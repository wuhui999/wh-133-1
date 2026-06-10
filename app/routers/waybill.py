from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Waybill, Probe, Vehicle, WaybillStatus, UserRole
from app.schemas import (
    WaybillCreate, WaybillOut, WaybillStatusUpdate, ProbeCreate, ProbeOut,
    ProbeBind, VehicleCreate, VehicleOut,
)
from app.dependencies import get_current_user, require_role
from app.services.audit import write_audit_log

router = APIRouter(prefix="/api/waybills", tags=["waybills"])


@router.post("/vehicles", response_model=VehicleOut)
def create_vehicle(body: VehicleCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    v = Vehicle(plate_number=body.plate_number, carrier_id=body.carrier_id)
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


@router.get("/vehicles", response_model=list[VehicleOut])
def list_vehicles(db: Session = Depends(get_db)):
    return db.query(Vehicle).all()


@router.post("/probes", response_model=ProbeOut)
def create_probe(body: ProbeCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    p = Probe(probe_code=body.probe_code)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.get("/probes", response_model=list[ProbeOut])
def list_probes(db: Session = Depends(get_db)):
    return db.query(Probe).all()


@router.post("", response_model=WaybillOut)
def create_waybill(body: WaybillCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role(UserRole.pharma.value))):
    wb = Waybill(
        waybill_no=body.waybill_no,
        status=WaybillStatus.draft.value,
        drug_name=body.drug_name,
        drug_type=body.drug_type.value,
        quantity=body.quantity,
        pharma_enterprise_id=body.pharma_enterprise_id or current_user.enterprise_id,
        carrier_enterprise_id=body.carrier_enterprise_id,
        vehicle_id=body.vehicle_id,
        temp_min=body.temp_min,
        temp_max=body.temp_max,
        consecutive_exceed_limit_min=body.consecutive_exceed_limit_min,
        sampling_interval_sec=body.sampling_interval_sec,
    )
    db.add(wb)
    db.commit()
    db.refresh(wb)
    write_audit_log(db, user_id=current_user.id, action="create_waybill", target_type="waybill", target_id=wb.id,
                    detail=f"Created waybill {wb.waybill_no}")
    return wb


@router.get("", response_model=list[WaybillOut])
def list_waybills(status: str = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(Waybill)
    if status:
        q = q.filter(Waybill.status == status)
    return q.all()


@router.get("/{waybill_id}", response_model=WaybillOut)
def get_waybill(waybill_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    wb = db.query(Waybill).filter(Waybill.id == waybill_id).first()
    if not wb:
        raise HTTPException(status_code=404, detail="Waybill not found")
    return wb


@router.post("/{waybill_id}/bind-probe", response_model=WaybillOut)
def bind_probe(waybill_id: int, body: ProbeBind, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    wb = db.query(Waybill).filter(Waybill.id == waybill_id).first()
    if not wb:
        raise HTTPException(status_code=404, detail="Waybill not found")
    probe = db.query(Probe).filter(Probe.id == body.probe_id).first()
    if not probe:
        raise HTTPException(status_code=404, detail="Probe not found")
    probe.waybill_id = waybill_id
    db.commit()
    db.refresh(wb)
    write_audit_log(db, user_id=current_user.id, action="bind_probe", target_type="waybill", target_id=wb.id,
                    detail=f"Bound probe {probe.probe_code} to waybill {wb.waybill_no}")
    return wb


@router.patch("/{waybill_id}/status", response_model=WaybillOut)
def update_waybill_status(waybill_id: int, body: WaybillStatusUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    wb = db.query(Waybill).filter(Waybill.id == waybill_id).first()
    if not wb:
        raise HTTPException(status_code=404, detail="Waybill not found")
    wb.status = body.status.value
    if body.loading_start:
        wb.loading_start = body.loading_start
    if body.loading_end:
        wb.loading_end = body.loading_end
    if body.departure_time:
        wb.departure_time = body.departure_time
    if body.arrival_time:
        wb.arrival_time = body.arrival_time
    if body.unloading_start:
        wb.unloading_start = body.unloading_start
    if body.unloading_end:
        wb.unloading_end = body.unloading_end
    db.commit()
    db.refresh(wb)
    write_audit_log(db, user_id=current_user.id, action="update_waybill_status", target_type="waybill", target_id=wb.id,
                    detail=f"Status updated to {body.status.value}")
    return wb
