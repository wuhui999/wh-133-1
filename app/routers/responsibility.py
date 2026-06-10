from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    User, Waybill, Alert, TempSampling, ResponsibilitySegment, ResponsibilitySegmentType,
    AlertStatus, AlertType,
)
from app.schemas import ResponsibilitySegmentOut, ResponsibilityReportOut
from app.dependencies import get_current_user, require_role
from app.services.audit import write_audit_log
from app.models import UserRole

router = APIRouter(prefix="/api/responsibility", tags=["responsibility"])


@router.post("/generate/{waybill_id}", response_model=ResponsibilityReportOut)
def generate_responsibility_report(waybill_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    wb = db.query(Waybill).filter(Waybill.id == waybill_id).first()
    if not wb:
        raise HTTPException(status_code=404, detail="Waybill not found")

    db.query(ResponsibilitySegment).filter(ResponsibilitySegment.waybill_id == waybill_id).delete()

    segments = []
    if wb.loading_start and wb.loading_end:
        seg = _build_segment(
            db, wb, ResponsibilitySegmentType.loading,
            wb.loading_start, wb.loading_end,
            wb.pharma_enterprise_id,
        )
        segments.append(seg)

    in_transit_start = wb.loading_end or wb.departure_time
    in_transit_end = wb.arrival_time or wb.unloading_start
    if in_transit_start and in_transit_end:
        seg = _build_segment(
            db, wb, ResponsibilitySegmentType.in_transit,
            in_transit_start, in_transit_end,
            wb.carrier_enterprise_id,
        )
        segments.append(seg)

    if wb.unloading_start and wb.unloading_end:
        seg = _build_segment(
            db, wb, ResponsibilitySegmentType.unloading,
            wb.unloading_start, wb.unloading_end,
            wb.carrier_enterprise_id,
        )
        segments.append(seg)

    db.commit()

    write_audit_log(db, user_id=current_user.id, action="generate_responsibility", target_type="waybill",
                    target_id=waybill_id, detail=f"Generated {len(segments)} segments")

    return {"waybill_id": waybill_id, "segments": segments}


def _build_segment(db, wb, seg_type, start, end, enterprise_id):
    alerts = (
        db.query(Alert)
        .filter(
            Alert.waybill_id == wb.id,
            Alert.started_at >= start,
            Alert.started_at <= end,
        )
        .all()
    )
    alert_count = len(alerts)

    max_exceed = None
    for a in alerts:
        if a.alert_type == AlertType.temp_exceed.value and a.temp_value is not None:
            exceed_amount = max(
                abs(a.temp_value - wb.temp_min),
                abs(a.temp_value - wb.temp_max),
            )
            if max_exceed is None or exceed_amount > max_exceed:
                max_exceed = exceed_amount

    seg = ResponsibilitySegment(
        waybill_id=wb.id,
        segment_type=seg_type.value,
        responsible_enterprise_id=enterprise_id,
        start_time=start,
        end_time=end,
        alert_count=alert_count,
        max_exceed_temp=max_exceed,
        description=f"{seg_type.value} phase: {start.isoformat()} ~ {end.isoformat()}, alerts={alert_count}",
    )
    db.add(seg)
    db.flush()
    db.refresh(seg)
    return seg


@router.get("/{waybill_id}", response_model=ResponsibilityReportOut)
def get_responsibility_report(waybill_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    segments = db.query(ResponsibilitySegment).filter(ResponsibilitySegment.waybill_id == waybill_id).all()
    return {"waybill_id": waybill_id, "segments": segments}
