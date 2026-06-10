from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models import UserRole, WaybillStatus, AlertStatus, AlertType, ClaimStatus, ResponsibilitySegmentType, DrugType


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None
    enterprise_id: Optional[int] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole
    enterprise_id: Optional[int] = None


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    enterprise_id: Optional[int] = None

    class Config:
        from_attributes = True


class EnterpriseCreate(BaseModel):
    name: str
    ent_type: str


class EnterpriseOut(BaseModel):
    id: int
    name: str
    ent_type: str

    class Config:
        from_attributes = True


class VehicleCreate(BaseModel):
    plate_number: str
    carrier_id: Optional[int] = None


class VehicleOut(BaseModel):
    id: int
    plate_number: str
    carrier_id: Optional[int] = None

    class Config:
        from_attributes = True


class ProbeCreate(BaseModel):
    probe_code: str


class ProbeOut(BaseModel):
    id: int
    probe_code: str
    waybill_id: Optional[int] = None

    class Config:
        from_attributes = True


class ProbeBind(BaseModel):
    probe_id: int


class WaybillCreate(BaseModel):
    waybill_no: str
    drug_name: str
    drug_type: DrugType
    quantity: float = 0
    pharma_enterprise_id: Optional[int] = None
    carrier_enterprise_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    temp_min: Optional[float] = None
    temp_max: Optional[float] = None
    consecutive_exceed_limit_min: Optional[int] = None
    sampling_interval_sec: int = 60


class WaybillStatusUpdate(BaseModel):
    status: WaybillStatus
    loading_start: Optional[datetime] = None
    loading_end: Optional[datetime] = None
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    unloading_start: Optional[datetime] = None
    unloading_end: Optional[datetime] = None


class WaybillOut(BaseModel):
    id: int
    waybill_no: str
    status: str
    drug_name: str
    drug_type: str
    quantity: float
    pharma_enterprise_id: Optional[int] = None
    carrier_enterprise_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    temp_min: float
    temp_max: float
    consecutive_exceed_limit_min: int
    sampling_interval_sec: int
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    loading_start: Optional[datetime] = None
    loading_end: Optional[datetime] = None
    unloading_start: Optional[datetime] = None
    unloading_end: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TempSamplingCreate(BaseModel):
    waybill_id: int
    probe_id: int
    temperature: float
    sampled_at: datetime


class TempSamplingBatch(BaseModel):
    samples: List[TempSamplingCreate]


class TempSamplingOut(BaseModel):
    id: int
    waybill_id: int
    probe_id: int
    temperature: float
    sampled_at: datetime

    class Config:
        from_attributes = True


class BreakPointOut(BaseModel):
    probe_id: int
    break_start: datetime
    break_end: Optional[datetime] = None
    gap_seconds: float


class AlertOut(BaseModel):
    id: int
    waybill_id: int
    alert_type: str
    status: str
    temp_value: Optional[float] = None
    temp_min: Optional[float] = None
    temp_max: Optional[float] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    consecutive_minutes: Optional[float] = None
    description: Optional[str] = None
    handler_id: Optional[int] = None
    handle_remark: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AlertConfirm(BaseModel):
    remark: Optional[str] = None


class AlertHandle(BaseModel):
    remark: str


class AlertClose(BaseModel):
    remark: Optional[str] = None


class ResponsibilitySegmentOut(BaseModel):
    id: int
    waybill_id: int
    segment_type: str
    responsible_enterprise_id: Optional[int] = None
    start_time: datetime
    end_time: datetime
    alert_count: int
    max_exceed_temp: Optional[float] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class ResponsibilityReportOut(BaseModel):
    waybill_id: int
    segments: List[ResponsibilitySegmentOut]


class ClaimCreate(BaseModel):
    waybill_id: int
    claimant_enterprise_id: Optional[int] = None
    respondent_enterprise_id: Optional[int] = None
    segment_id: Optional[int] = None
    alert_id: Optional[int] = None
    amount: float = 0
    reason: Optional[str] = None


class ClaimClose(BaseModel):
    remark: Optional[str] = None


class ClaimReview(BaseModel):
    status: ClaimStatus
    remark: Optional[str] = None


class ClaimOut(BaseModel):
    id: int
    waybill_id: int
    claim_no: str
    status: str
    claimant_enterprise_id: Optional[int] = None
    respondent_enterprise_id: Optional[int] = None
    segment_id: Optional[int] = None
    alert_id: Optional[int] = None
    amount: float
    reason: Optional[str] = None
    reviewer_id: Optional[int] = None
    review_remark: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    action: str
    target_type: str
    target_id: Optional[int] = None
    detail: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
