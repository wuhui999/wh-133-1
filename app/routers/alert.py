from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Alert, AlertStatus, AlertType
from app.schemas import AlertOut, AlertConfirm, AlertHandle, AlertClose
from app.dependencies import get_current_user, require_role
from app.services.audit import write_audit_log
from app.models import UserRole

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(
    waybill_id: int = None,
    status: str = None,
    alert_type: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Alert)
    if waybill_id:
        q = q.filter(Alert.waybill_id == waybill_id)
    if status:
        q = q.filter(Alert.status == status)
    if alert_type:
        q = q.filter(Alert.alert_type == alert_type)
    return q.order_by(Alert.created_at.desc()).all()


@router.get("/{alert_id}", response_model=AlertOut)
def get_alert(alert_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("/{alert_id}/confirm", response_model=AlertOut)
def confirm_alert(alert_id: int, body: AlertConfirm, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.status != AlertStatus.generated.value:
        raise HTTPException(status_code=400, detail=f"Cannot confirm alert in status {alert.status}")
    alert.status = AlertStatus.confirmed.value
    if body.remark:
        alert.handle_remark = body.remark
    db.commit()
    db.refresh(alert)
    write_audit_log(db, user_id=current_user.id, action="confirm_alert", target_type="alert", target_id=alert.id,
                    detail=body.remark)
    return alert


@router.post("/{alert_id}/handle", response_model=AlertOut)
def handle_alert(alert_id: int, body: AlertHandle, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.status not in [AlertStatus.confirmed.value]:
        raise HTTPException(status_code=400, detail=f"Cannot handle alert in status {alert.status}")
    alert.status = AlertStatus.handling.value
    alert.handler_id = current_user.id
    alert.handle_remark = body.remark
    db.commit()
    db.refresh(alert)
    write_audit_log(db, user_id=current_user.id, action="handle_alert", target_type="alert", target_id=alert.id,
                    detail=body.remark)
    return alert


@router.post("/{alert_id}/close", response_model=AlertOut)
def close_alert(alert_id: int, body: AlertClose, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.status not in [AlertStatus.handling.value, AlertStatus.confirmed.value]:
        raise HTTPException(status_code=400, detail=f"Cannot close alert in status {alert.status}")
    alert.status = AlertStatus.closed.value
    if body.remark:
        alert.handle_remark = (alert.handle_remark or "") + " | CLOSE: " + body.remark
    db.commit()
    db.refresh(alert)
    write_audit_log(db, user_id=current_user.id, action="close_alert", target_type="alert", target_id=alert.id,
                    detail=body.remark)
    return alert
