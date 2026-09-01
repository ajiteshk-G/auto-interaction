from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class TestRideRecording(Base):
    __tablename__ = "test_ride_recordings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(64), unique=True, index=True, nullable=False) # e.g. "TR-2026-AARAV-881"
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    booking_id = Column(Integer, ForeignKey("test_drive_bookings.id"), nullable=True)
    booking_reference = Column(String(64), index=True, nullable=True)
    
    # Vehicle and Advisor
    vehicle_id = Column(String(64), nullable=False, default="thar_roxx")
    vehicle_name = Column(String(128), default="Mahindra Thar ROXX AX7L Diesel 4x4 AT")
    sales_advisor_name = Column(String(128), default="Rajesh Varma (Bayview Mahindra)")
    
    # Storage in GCS / File System
    gcs_bucket = Column(String(128), default="mahindra-sales-recordings")
    gcs_object_path = Column(String(256), nullable=False) # e.g. "test_rides/tr_aarav_sharma_2026.webm"
    gcs_uri = Column(String(256), nullable=False) # e.g. "gs://mahindra-sales-recordings/test_rides/tr_aarav_sharma_2026.webm"
    duration_seconds = Column(Integer, default=184)
    file_size_bytes = Column(Integer, default=1485200)
    audio_format = Column(String(32), default="audio/webm")
    
    # AI Extracted Multi-Dimensional Insights
    transcript = Column(Text, nullable=True)
    customer_sentiment_score = Column(Float, default=0.88) # 0.0 to 1.0
    purchase_intent_score = Column(Float, default=0.92) # 0.0 to 1.0
    loved_features = Column(JSON, nullable=True) # e.g. ["FSD Suspension", "Panoramic Skyroof", "mStallion Diesel Power"]
    objections_raised = Column(JSON, nullable=True) # e.g. ["Rear seat legroom comfort", "Delivery wait period (10-12 weeks)"]
    advisor_pitch_score = Column(Float, default=8.5) # out of 10
    advisor_coaching_feedback = Column(Text, nullable=True)
    recommended_action = Column(Text, nullable=True)
    
    status = Column(String(32), default="ANALYZED") # RECORDING, UPLOADED, ANALYZED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="test_ride_recordings")
    outbound_calls = relationship("OutboundCallLog", back_populates="test_ride", cascade="all, delete-orphan")


class OutboundCallLog(Base):
    __tablename__ = "outbound_call_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    call_reference = Column(String(64), unique=True, index=True, nullable=False) # e.g. "CALL-MIA-2026-9901"
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    test_ride_id = Column(Integer, ForeignKey("test_ride_recordings.id"), nullable=True)
    
    agent_name = Column(String(64), default="MIA (Mahindra Intelligent Assistant)")
    phone_number = Column(String(32), default="+91 98201 23456")
    call_status = Column(String(32), default="COMPLETED") # INITIATED, RINGING, CONNECTED, COMPLETED
    call_duration_seconds = Column(Integer, default=95)
    
    # Conversational script and audio transcript
    transcript = Column(Text, nullable=True)
    
    # Post-Call Insights & Handoff
    objection_resolution_status = Column(String(64), default="RESOLVED_RECLINE_AND_12_DAY_ALLOCATION")
    customer_sentiment = Column(String(32), default="VERY_POSITIVE")
    customer_decision = Column(String(64), default="LOCKED_FAST_ALLOCATION_PROCEED_TO_FINANCING")
    locked_vehicle_variant = Column(String(128), default="Thar ROXX AX7L Diesel AT (Stealth Black)")
    locked_allocation_days = Column(Integer, default=12)
    next_step = Column(String(64), default="DIGITAL_FINANCING_KYC")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="outbound_calls")
    test_ride = relationship("TestRideRecording", back_populates="outbound_calls")
