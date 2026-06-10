from sqlalchemy.orm import Session
from app.models import Waybill, TempSampling, Alert, AlertType, AlertStatus
from datetime import datetime, timedelta
from app.services.audit import write_audit_log


def check_temperature_rules(db: Session, waybill: Waybill, sample: TempSampling):
    exceed = sample.temperature < waybill.temp_min or sample.temperature > waybill.temp_max
    if not exceed:
        return None

    limit_minutes = waybill.consecutive_exceed_limit_min
    cutoff = sample.sampled_at - timedelta(minutes=limit_minutes)

    recent_samples = (
        db.query(TempSampling)
        .filter(
            TempSampling.waybill_id == waybill.id,
            TempSampling.probe_id == sample.probe_id,
            TempSampling.sampled_at >= cutoff,
            TempSampling.sampled_at <= sample.sampled_at,
        )
        .order_by(TempSampling.sampled_at)
        .all()
    )

    consecutive_start = sample.sampled_at
    for s in reversed(recent_samples):
        if s.temperature < waybill.temp_min or s.temperature > waybill.temp_max:
            consecutive_start = s.sampled_at
        else:
            break

    consecutive_duration = (sample.sampled_at - consecutive_start).total_seconds() / 60.0

    if consecutive_duration >= limit_minutes:
        existing = (
            db.query(Alert)
            .filter(
                Alert.waybill_id == waybill.id,
                Alert.alert_type == AlertType.temp_exceed.value,
                Alert.status.in_([AlertStatus.generated.value, AlertStatus.confirmed.value, AlertStatus.handling.value]),
                Alert.started_at <= sample.sampled_at,
            )
            .first()
        )
        if existing:
            existing.ended_at = sample.sampled_at
            existing.consecutive_minutes = consecutive_duration
            existing.temp_value = sample.temperature
            db.commit()
            return existing

        alert = Alert(
            waybill_id=waybill.id,
            alert_type=AlertType.temp_exceed.value,
            status=AlertStatus.generated.value,
            temp_value=sample.temperature,
            temp_min=waybill.temp_min,
            temp_max=waybill.temp_max,
            started_at=consecutive_start,
            ended_at=sample.sampled_at,
            consecutive_minutes=consecutive_duration,
            description=f"Temperature {sample.temperature}°C exceeded range [{waybill.temp_min}, {waybill.temp_max}] for {consecutive_duration:.1f} minutes",
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        write_audit_log(
            db,
            action="alert_generated",
            target_type="alert",
            target_id=alert.id,
            detail=f"Auto-generated temp_exceed alert for waybill {waybill.waybill_no}",
        )
        return alert

    return None


def detect_sampling_breaks(db: Session, waybill_id: int, probe_id: int, threshold_multiplier: float = 2.0):
    waybill = db.query(Waybill).filter(Waybill.id == waybill_id).first()
    if not waybill:
        return []

    expected_interval = waybill.sampling_interval_sec
    break_threshold = expected_interval * threshold_multiplier

    samples = (
        db.query(TempSampling)
        .filter(TempSampling.waybill_id == waybill_id, TempSampling.probe_id == probe_id)
        .order_by(TempSampling.sampled_at)
        .all()
    )

    breaks = []
    for i in range(1, len(samples)):
        gap = (samples[i].sampled_at - samples[i - 1].sampled_at).total_seconds()
        if gap > break_threshold:
            breaks.append({
                "probe_id": probe_id,
                "break_start": samples[i - 1].sampled_at,
                "break_end": samples[i].sampled_at,
                "gap_seconds": gap,
            })

            existing = (
                db.query(Alert)
                .filter(
                    Alert.waybill_id == waybill_id,
                    Alert.alert_type == AlertType.sampling_interrupt.value,
                    Alert.status.in_([AlertStatus.generated.value, AlertStatus.confirmed.value]),
                )
                .first()
            )
            if not existing:
                alert = Alert(
                    waybill_id=waybill_id,
                    alert_type=AlertType.sampling_interrupt.value,
                    status=AlertStatus.generated.value,
                    started_at=samples[i - 1].sampled_at,
                    ended_at=samples[i].sampled_at,
                    description=f"Sampling gap {gap:.0f}s detected on probe {probe_id} (threshold: {break_threshold:.0f}s)",
                )
                db.add(alert)
                db.commit()
                db.refresh(alert)

                write_audit_log(
                    db,
                    action="alert_generated",
                    target_type="alert",
                    target_id=alert.id,
                    detail=f"Auto-generated sampling_interrupt alert for waybill_id={waybill_id}",
                )

    return breaks
