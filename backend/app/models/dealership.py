from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, Boolean
from app.database import Base

class Dealership(Base):
    __tablename__ = "dealerships"

    id = Column(String(64), primary_key=True, index=True) # e.g. "mumbai_nbs_chowpatty"
    name = Column(String(128), nullable=False) # "Mahindra NBS International Ltd - Chowpatty"
    city = Column(String(64), index=True, nullable=False) # "Mumbai", "Pune", "Delhi", "Bangalore", "Chennai"
    state = Column(String(64), nullable=False) # "Maharashtra", "Delhi", "Karnataka", "Tamil Nadu"
    area = Column(String(128), nullable=True) # "Chowpatty Sea Face", "Bandra West"
    address = Column(Text, nullable=False)
    pin_code = Column(String(16), nullable=False)
    phone = Column(String(32), nullable=False)
    email = Column(String(128), nullable=True)
    map_url = Column(String(256), nullable=True)
    rating = Column(Float, default=4.8)
    available_advisors = Column(JSON, nullable=True) # ["Rajesh Varma", "Pooja Hegde"]
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
