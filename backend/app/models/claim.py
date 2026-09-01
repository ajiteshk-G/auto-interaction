from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class InsuranceClaim(Base):
    __tablename__ = "insurance_claims"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    claim_id = Column(String(64), unique=True, index=True, nullable=False) # e.g. "MH-INS-99201"
    brand_id = Column(String(64), index=True, default="mahindra", nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    vin = Column(String(64), nullable=False)
    vehicle_model = Column(String(128), nullable=False)
    
    incident_description = Column(Text, nullable=False)
    damage_severity = Column(String(32), default="MINOR") # MINOR, MODERATE, SEVERE
    detected_damages = Column(JSON, nullable=False) # e.g. ["lower bumper cover scratches", "cracked right fog lamp housing"]
    
    oem_part_number = Column(String(64), default="#TH-88301")
    oem_part_description = Column(String(128), default="Fog Lamp Assembly Right")
    estimated_part_cost = Column(Float, default=3200.0)
    estimated_labor_cost = Column(Float, default=800.0)
    customer_out_of_pocket = Column(Float, default=0.0)
    
    insurer_name = Column(String(128), default="ICICI Lombard General Insurance")
    policy_number = Column(String(64), default="POL-ICICI-MH-2026-99201")
    claim_status = Column(String(32), default="DIGITALLY_APPROVED") # SUBMITTED, DIGITALLY_APPROVED, PARTS_DISPATCHED, SETTLED
    
    workshop_name = Column(String(128), default="Bayview Mahindra Workshop")
    parts_delivery_estimate = Column(String(64), default="Tomorrow Morning 9:00 AM")
    
    image_evidence_url = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="claims")
