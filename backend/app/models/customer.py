from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("phone", "brand_id", name="uq_customers_phone_brand"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_id = Column(String(64), unique=True, index=True, nullable=False) # e.g. "CUST-9820155432"
    brand_id = Column(String(64), index=True, default="mahindra", nullable=False)
    name = Column(String(128), nullable=False)
    phone = Column(String(32), index=True, nullable=False) # Unique Phone per brand
    email = Column(String(128), nullable=True)
    city = Column(String(64), default="Mumbai")
    preferred_language = Column(String(32), default="Hinglish")
    
    # Persistent State across lifecycle
    current_phase = Column(String(32), default="PRE_SALES") # PRE_SALES, FINANCING, PURCHASED, POST_SALES
    interested_vehicle_id = Column(String(64), default="thar_roxx")
    interested_variant = Column(String(64), default="AX7L Diesel AT 4x4")
    budget_range = Column(String(64), nullable=True)
    advisor_checklist = Column(JSON, nullable=True) # Pre-sales inquiry demo items
    
    # Showroom & KYC persistence
    pan_number = Column(String(32), nullable=True)
    aadhaar_masked = Column(String(32), nullable=True)
    kyc_status = Column(String(32), default="PENDING")
    kyc_extracted_data = Column(JSON, nullable=True)
    
    # Financing details
    loan_preapproval_amount = Column(Integer, default=1850000)
    loan_interest_rate = Column(String(16), default="8.15%")
    voice_consent_hash = Column(String(128), nullable=True)
    loan_status = Column(String(32), default="NOT_APPLIED")
    
    # Vehicle Ownership details (for Post-Sales)
    owned_vin = Column(String(64), default="MAH1THARROXX2026MUM01")
    owned_vehicle_name = Column(String(128), default="Mahindra Thar ROXX AX7L Diesel AT")
    registration_number = Column(String(32), default="MH 02 FJ 9090")
    odometer_km = Column(Integer, default=9820)
    insurance_policy_number = Column(String(64), default="POL-ICICI-MH-2026-99201")
    insurance_type = Column(String(64), default="Zero-Depreciation Comprehensive")
    
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # 1:Many Relationships
    sessions = relationship("ConversationSession", back_populates="customer", cascade="all, delete-orphan", order_by="desc(ConversationSession.created_at)")
    interactions = relationship("InteractionLog", back_populates="customer", cascade="all, delete-orphan", order_by="desc(InteractionLog.created_at)")
    bookings = relationship("TestDriveBooking", back_populates="customer", cascade="all, delete-orphan")
    claims = relationship("InsuranceClaim", back_populates="customer", cascade="all, delete-orphan")
    test_ride_recordings = relationship("TestRideRecording", back_populates="customer", cascade="all, delete-orphan")
    outbound_calls = relationship("OutboundCallLog", back_populates="customer", cascade="all, delete-orphan")

class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(64), unique=True, index=True, nullable=False) # e.g. "SESS-20260825-ABCD"
    brand_id = Column(String(64), index=True, default="mahindra", nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    session_type = Column(String(32), default="LIVE_CALL") # "LIVE_CALL" | "CHAT_BOT"
    vehicle_id = Column(String(64), default="thar_roxx")
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    customer = relationship("Customer", back_populates="sessions")
    transcripts = relationship("InteractionLog", back_populates="session", cascade="all, delete-orphan", order_by="InteractionLog.created_at")

class InteractionLog(Base):
    __tablename__ = "interaction_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    brand_id = Column(String(64), index=True, default="mahindra", nullable=False)
    session_id = Column(Integer, ForeignKey("conversation_sessions.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    channel = Column(String(32), default="VOICE_LIVE") # VOICE_LIVE, WHATSAPP, WEB_CHAT, DEALER_TABLET
    speaker = Column(String(32), nullable=False) # "customer", "mia", "system"
    message = Column(Text, nullable=False)
    extracted_intent = Column(String(128), nullable=True)
    tool_triggered = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    customer = relationship("Customer", back_populates="interactions")
    session = relationship("ConversationSession", back_populates="transcripts")
