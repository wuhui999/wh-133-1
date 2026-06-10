from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models import User, Waybill, TempSampling, Probe
from app.schemas import TempSamplingCreate, TempSamplingBatch, TempSamplingOut, BreakPointOut
from app.dependencies import get_current_user
from app.services.temp_monitor import check_temperature_rules, detect_sampling_breaks

router = APIRouter(prefix="/api/temperature", tags=["temperature"])


@router.post("/samples", response_model=list[TempSamplingOut])
def batch_write_samples(body: TempSamplingBatch, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    waybill = db.query(Waybill).filter(Waybill.id == body.samples[0].waybill_id).first() if body.samples else None
    if not waybill:
        raise HTTPException(status_code=404, detail="Waybill not found")

    results = []
    for s in body.samples:
        probe = db.query(Probe).filter(Probe.id == s.probe_id).first()
        if not probe:
            raise HTTPException(status_code=404, detail=f"Probe {s.probe_id} not found")
        sample = TempSampling(
            waybill_id=s.waybill_id,
            probe_id=s.probe_id,
            temperature=s.temperature,
            sampled_at=s.sampled_at,
        )
        db.add(sample)
        db.flush()
        results.append(sample)

    db.commit()
    for sample in results:
        db.refresh(sample)
        check_temperature_rules(db, waybill, sample)

    return results


@router.get("/curve/{waybill_id}", response_model=list[TempSamplingOut])
def query_temperature_curve(
    waybill_id: int,
    probe_id: int = None,
    start_time: datetime = None,
    end_time: datetime = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(TempSampling).filter(TempSampling.waybill_id == waybill_id)
    if probe_id:
        q = q.filter(TempSampling.probe_id == probe_id)
    if start_time:
        q = q.filter(TempSampling.sampled_at >= start_time)
    if end_time:
        q = q.filter(TempSampling.sampled_at <= end_time)
    return q.order_by(TempSampling.sampled_at).all()


@router.get("/breakpoints/{waybill_id}/{probe_id}", response_model=list[BreakPointOut])
def detect_breakpoints(
    waybill_id: int,
    probe_id: int,
    threshold_multiplier: float = Query(2.0, description="Gap threshold as multiplier of sampling interval"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    breaks = detect_sampling_breaks(db, waybill_id, probe_id, threshold_multiplier)
    return breaks
