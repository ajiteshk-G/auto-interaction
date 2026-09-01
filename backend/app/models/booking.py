from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class TestDriveBooking(Base):
    __tablename__ = "test_drive_bookings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    booking_reference = Column(String(64), unique=True, index=True, nullable=False) # e.g. "BK-MAH-2026-8821"
    brand_id = Column(String(64), index=True, default="mahindra", nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    vehicle_id = Column(String(64), nullable=False) # "thar_roxx", "be_6e", "xuv700"
    variant = Column(String(128), nullable=False) # "AX7L Diesel AT 4x4"
    color = Column(String(64), default="Stealth Black")
    
    dealership_id = Column(String(64), default="bayview_bandra")
    dealership_name = Column(String(128), default="Bayview Mahindra, Bandra West")
    sales_advisor_name = Column(String(128), default="Rajesh Varma")
    
    booking_type = Column(String(32), default="HOME_DOORSTEP") # HOME_DOORSTEP, SHOWROOM_VISIT
    delivery_address = Column(Text, nullable=True)
    scheduled_date = Column(String(32), nullable=False) # "Tomorrow" or YYYY-MM-DD
    scheduled_time_slot = Column(String(32), nullable=False) # "5:00 PM"
    
    status = Column(String(32), default="CONFIRMED") # CONFIRMED, COMPLETED, CANCELLED
    notes = Column(Text, nullable=True)
    advisor_checklist = Column(JSON, nullable=True) # Dynamic checklist items from pre-sales
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="bookings")


class TestDriveSlot(Base):
    __tablename__ = "test_drive_slots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    brand_id = Column(String(64), index=True, default="mahindra", nullable=False)
    slot_date = Column(String(32), index=True, nullable=False) # e.g. "2026-08-26"
    slot_time = Column(String(32), nullable=False) # e.g. "11:00 AM"
    dealership_id = Column(String(64), default="bayview_bandra")
    vehicle_id = Column(String(64), nullable=True) # "thar_roxx" or None for all
    status = Column(String(32), default="AVAILABLE", nullable=False) # "AVAILABLE", "RESERVED", "BLOCKED"
    
    # Customer Details when reserved
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    customer_name = Column(String(128), nullable=True)
    customer_phone = Column(String(32), nullable=True)
    booking_reference = Column(String(64), nullable=True)
    booking_type = Column(String(32), default="HOME_DOORSTEP") # HOME_DOORSTEP or SHOWROOM_VISIT
    delivery_address = Column(Text, nullable=True)
    pin_code = Column(String(16), nullable=True)
    notes = Column(Text, nullable=True)
    
    reserved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PublicHoliday(Base):
    __tablename__ = "public_holidays"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    holiday_date = Column(String(16), unique=True, index=True, nullable=False) # "YYYY-MM-DD"
    holiday_name = Column(String(128), nullable=False)
    state = Column(String(64), nullable=True) # "ALL", "Maharashtra", etc.
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class SlotConfig(Base):
    __tablename__ = "slot_configs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    slot_time = Column(String(32), unique=True, index=True, nullable=False) # "09:00 AM", "10:00 AM", etc.
    display_order = Column(Integer, default=0)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

