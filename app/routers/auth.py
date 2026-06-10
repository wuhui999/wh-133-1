from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Enterprise, UserRole
from app.schemas import (
    LoginRequest, Token, UserCreate, UserOut, EnterpriseCreate, EnterpriseOut,
)
from app.dependencies import (
    verify_password, get_password_hash, create_access_token, get_current_user, require_role,
)
from app.services.audit import write_audit_log

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/enterprises", response_model=EnterpriseOut)
def create_enterprise(body: EnterpriseCreate, db: Session = Depends(get_db)):
    ent = Enterprise(name=body.name, ent_type=body.ent_type)
    db.add(ent)
    db.commit()
    db.refresh(ent)
    return ent


@router.get("/enterprises", response_model=list[EnterpriseOut])
def list_enterprises(db: Session = Depends(get_db)):
    return db.query(Enterprise).all()


@router.post("/register", response_model=UserOut)
def register_user(body: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == body.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    user = User(
        username=body.username,
        hashed_password=get_password_hash(body.password),
        role=body.role.value,
        enterprise_id=body.enterprise_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(data={"user_id": user.id, "role": user.role, "enterprise_id": user.enterprise_id})
    write_audit_log(db, user_id=user.id, action="login", target_type="user", target_id=user.id)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(require_role(UserRole.supervisor.value))):
    return db.query(User).all()
