from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, AuditLog
from app.schemas import AuditLogOut
from app.dependencies import get_current_user, require_role
from app.models import UserRole

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
def list_audit_logs(
    target_type: str = None,
    target_id: int = None,
    action: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.supervisor.value)),
):
    q = db.query(AuditLog)
    if target_type:
        q = q.filter(AuditLog.target_type == target_type)
    if target_id:
        q = q.filter(AuditLog.target_id == target_id)
    if action:
        q = q.filter(AuditLog.action == action)
    return q.order_by(AuditLog.created_at.desc()).limit(200).all()
