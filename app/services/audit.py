from sqlalchemy.orm import Session
from app.models import AuditLog
from datetime import datetime


def write_audit_log(
    db: Session,
    user_id: int = None,
    action: str = "",
    target_type: str = "",
    target_id: int = None,
    detail: str = None,
):
    log = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
        created_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()
