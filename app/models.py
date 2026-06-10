from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
import enum


class UserRole(str, enum.Enum):
    pharma = "pharma"
    carrier = "carrier"
    supervisor = "supervisor"


class WaybillStatus(str, enum.Enum):
    draft = "draft"
    in_transit = "in_transit"
    delivered = "delivered"
    abnormal_closed = "abnormal_closed"


class AlertStatus(str, enum.Enum):
    generated = "generated"
    confirmed = "confirmed"
    handling = "handling"
    closed = "closed"


class AlertType(str, enum.Enum):
    temp_exceed = "temp_exceed"
    sampling_interrupt = "sampling_interrupt"


class ClaimStatus(str, enum.Enum):
    registered = "registered"
    under_review = "under_review"
    approved = "approved"
    rejected = "rejected"
    closed = "closed"


class ResponsibilitySegmentType(str, enum.Enum):
    loading = "loading"
    in_transit = "in_transit"
    unloading = "unloading"


class DrugType(str, enum.Enum):
    vaccine = "vaccine"
    biologic = "biologic"
    insulin = "insulin"
    blood_product = "blood_product"
    other = "other"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    role = Column(String(20), nullable=False)
    enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=True)
    enterprise = relationship("Enterprise", back_populates="users")
    created_at = Column(DateTime, default=datetime.utcnow)


class Enterprise(Base):
    __tablename__ = "enterprises"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, unique=True)
    ent_type = Column(String(20), nullable=False)
    users = relationship("User", back_populates="enterprise")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    plate_number = Column(String(32), unique=True, nullable=False)
    carrier_id = Column(Integer, ForeignKey("enterprises.id"), nullable=True)
    carrier = relationship("Enterprise")


class Probe(Base):
    __tablename__ = "probes"

    id = Column(Integer, primary_key=True, index=True)
    probe_code = Column(String(64), unique=True, nullable=False)
    waybill_id = Column(Integer, ForeignKey("waybills.id"), nullable=True)
    waybill = relationship("Waybill", back_populates="probes")


class Waybill(Base):
    __tablename__ = "waybills"

    id = Column(Integer, primary_key=True, index=True)
    waybill_no = Column(String(64), unique=True, nullable=False, index=True)
    status = Column(String(20), nullable=False, default=WaybillStatus.draft.value)
    drug_name = Column(String(128), nullable=False)
    drug_type = Column(String(20), nullable=False)
    quantity = Column(Float, default=0)
    pharma_enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=True)
    carrier_enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    temp_min = Column(Float, nullable=False, default=2.0)
    temp_max = Column(Float, nullable=False, default=8.0)
    consecutive_exceed_limit_min = Column(Integer, nullable=False, default=5)
    sampling_interval_sec = Column(Integer, nullable=False, default=60)
    departure_time = Column(DateTime, nullable=True)
    arrival_time = Column(DateTime, nullable=True)
    loading_start = Column(DateTime, nullable=True)
    loading_end = Column(DateTime, nullable=True)
    unloading_start = Column(DateTime, nullable=True)
    unloading_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    probes = relationship("Probe", back_populates="waybill")
    pharma_enterprise = relationship("Enterprise", foreign_keys=[pharma_enterprise_id])
    carrier_enterprise = relationship("Enterprise", foreign_keys=[carrier_enterprise_id])
    vehicle = relationship("Vehicle")


class TempSampling(Base):
    __tablename__ = "temp_samplings"

    id = Column(Integer, primary_key=True, index=True)
    waybill_id = Column(Integer, ForeignKey("waybills.id"), nullable=False, index=True)
    probe_id = Column(Integer, ForeignKey("probes.id"), nullable=False)
    temperature = Column(Float, nullable=False)
    sampled_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    waybill = relationship("Waybill")
    probe = relationship("Probe")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    waybill_id = Column(Integer, ForeignKey("waybills.id"), nullable=False, index=True)
    alert_type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default=AlertStatus.generated.value)
    temp_value = Column(Float, nullable=True)
    temp_min = Column(Float, nullable=True)
    temp_max = Column(Float, nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    consecutive_minutes = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    handler_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    handler = relationship("User")
    handle_remark = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    waybill = relationship("Waybill")


class ResponsibilitySegment(Base):
    __tablename__ = "responsibility_segments"

    id = Column(Integer, primary_key=True, index=True)
    waybill_id = Column(Integer, ForeignKey("waybills.id"), nullable=False, index=True)
    segment_type = Column(String(20), nullable=False)
    responsible_enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    alert_count = Column(Integer, default=0)
    max_exceed_temp = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    waybill = relationship("Waybill")
    responsible_enterprise = relationship("Enterprise")


class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    waybill_id = Column(Integer, ForeignKey("waybills.id"), nullable=False, index=True)
    claim_no = Column(String(64), unique=True, nullable=False)
    status = Column(String(20), nullable=False, default=ClaimStatus.registered.value)
    claimant_enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=True)
    respondent_enterprise_id = Column(Integer, ForeignKey("enterprises.id"), nullable=True)
    segment_id = Column(Integer, ForeignKey("responsibility_segments.id"), nullable=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=True)
    amount = Column(Float, default=0)
    reason = Column(Text, nullable=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_remark = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    waybill = relationship("Waybill")
    claimant = relationship("Enterprise", foreign_keys=[claimant_enterprise_id])
    respondent = relationship("Enterprise", foreign_keys=[respondent_enterprise_id])
    segment = relationship("ResponsibilitySegment")
    alert = relationship("Alert")
    reviewer = relationship("User")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    action = Column(String(64), nullable=False)
    target_type = Column(String(64), nullable=False)
    target_id = Column(Integer, nullable=True)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
