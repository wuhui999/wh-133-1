from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models import User, Claim, ClaimStatus, UserRole
from app.schemas import ClaimCreate, ClaimOut, ClaimReview
from app.dependencies import get_current_user, require_role
from app.services.audit import write_audit_log

router = APIRouter(prefix="/api/claims", tags=["claims"])


def _gen_claim_no(db: Session):
    today = datetime.utcnow().strftime("%Y%m%d")
    count = db.query(Claim).filter(Claim.claim_no.like(f"CLM-{today}%")).count() + 1
    return f"CLM-{today}-{count:04d}"


@router.post("", response_model=ClaimOut)
def register_claim(body: ClaimCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    claim = Claim(
        waybill_id=body.waybill_id,
        claim_no=_gen_claim_no(db),
        status=ClaimStatus.registered.value,
        claimant_enterprise_id=body.claimant_enterprise_id or current_user.enterprise_id,
        respondent_enterprise_id=body.respondent_enterprise_id,
        segment_id=body.segment_id,
        alert_id=body.alert_id,
        amount=body.amount,
        reason=body.reason,
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    write_audit_log(db, user_id=current_user.id, action="register_claim", target_type="claim", target_id=claim.id,
                    detail=f"Claim {claim.claim_no} registered, amount={claim.amount}")
    return claim


@router.get("", response_model=list[ClaimOut])
def list_claims(status: str = None, waybill_id: int = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(Claim)
    if status:
        q = q.filter(Claim.status == status)
    if waybill_id:
        q = q.filter(Claim.waybill_id == waybill_id)
    return q.order_by(Claim.created_at.desc()).all()


@router.get("/{claim_id}", response_model=ClaimOut)
def get_claim(claim_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


@router.post("/{claim_id}/review", response_model=ClaimOut)
def review_claim(claim_id: int, body: ClaimReview, db: Session = Depends(get_db), current_user: User = Depends(require_role(UserRole.supervisor.value, UserRole.pharma.value))):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.status not in [ClaimStatus.registered.value, ClaimStatus.under_review.value]:
        raise HTTPException(status_code=400, detail=f"Cannot review claim in status {claim.status}")

    claim.status = body.status.value
    claim.reviewer_id = current_user.id
    claim.review_remark = body.remark
    claim.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(claim)

    write_audit_log(db, user_id=current_user.id, action="review_claim", target_type="claim", target_id=claim.id,
                    detail=f"Claim {claim.claim_no} reviewed: status={body.status.value}")
    return claim
