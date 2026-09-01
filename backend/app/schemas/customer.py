from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator
import re

NAME_REGEX = re.compile(r"^[a-zA-Z\s.]{2,50}$")
PHONE_REGEX = re.compile(r"^(\+91[\-\s]?)?[6-9]\d{9}$")

class InteractionLogSchema(BaseModel):
    id: Optional[int] = None
    session_id: Optional[int] = None
    channel: str = "VOICE_LIVE"
    speaker: str # "customer", "mia", "system"
    message: str
    extracted_intent: Optional[str] = None
    tool_triggered: Optional[str] = None
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class ConversationSessionSchema(BaseModel):
    id: int
    session_id: str
    customer_id: int
    session_type: str
    vehicle_id: str
    summary: Optional[str] = None
    created_at: datetime
    ended_at: Optional[datetime] = None
    transcripts: List[InteractionLogSchema] = []

    model_config = ConfigDict(from_attributes=True)

class CustomerIdentifyRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    phone: str = Field(..., min_length=10, max_length=16)
    session_type: str = "LIVE_CALL" # "LIVE_CALL" | "CHAT_BOT"
    vehicle_id: Optional[str] = "thar_roxx"

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        clean = v.strip()
        if not NAME_REGEX.match(clean):
            raise ValueError("Name must contain only alphabets and spaces (2 to 50 characters).")
        return clean

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        clean = re.sub(r"[\s\-]", "", v.strip())
        if not PHONE_REGEX.match(clean) and not re.match(r"^\+?[1-9]\d{9,14}$", clean):
            raise ValueError("Please enter a valid 10-digit mobile number (e.g. 9820155432 or +91 98201 55432).")
        return clean

class CustomerProfileBase(BaseModel):
    customer_id: str
    name: str
    phone: str
    email: Optional[str] = None
    city: str = "Mumbai"
    preferred_language: str = "Hinglish"
    current_phase: str = "PRE_SALES"
    interested_vehicle_id: Optional[str] = "thar_roxx"
    interested_variant: Optional[str] = "AX7L Diesel AT 4x4"
    budget_range: Optional[str] = "₹18 Lakh - ₹25 Lakh"
    
    pan_number: Optional[str] = None
    aadhaar_masked: Optional[str] = None
    kyc_status: str = "PENDING"
    kyc_extracted_data: Optional[Dict[str, Any]] = None
    
    loan_preapproval_amount: int = 1850000
    loan_interest_rate: str = "8.15%"
    voice_consent_hash: Optional[str] = None
    loan_status: str = "NOT_APPLIED"
    
    owned_vin: Optional[str] = "MAH1THARROXX2026MUM01"
    owned_vehicle_name: Optional[str] = "Mahindra Thar ROXX AX7L Diesel AT"
    registration_number: Optional[str] = "MH 02 FJ 9090"
    odometer_km: int = 9820
    insurance_policy_number: Optional[str] = "POL-ICICI-MH-2026-99201"
    insurance_type: Optional[str] = "Zero-Depreciation Comprehensive"

    model_config = ConfigDict(from_attributes=True)

class CustomerProfileCreate(CustomerProfileBase):
    pass

class CustomerProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    preferred_language: Optional[str] = None
    current_phase: Optional[str] = None
    interested_vehicle_id: Optional[str] = None
    interested_variant: Optional[str] = None
    budget_range: Optional[str] = None
    
    pan_number: Optional[str] = None
    aadhaar_masked: Optional[str] = None
    kyc_status: Optional[str] = None
    kyc_extracted_data: Optional[Dict[str, Any]] = None
    
    loan_preapproval_amount: Optional[int] = None
    loan_interest_rate: Optional[str] = None
    voice_consent_hash: Optional[str] = None
    loan_status: Optional[str] = None
    
    odometer_km: Optional[int] = None

class CustomerProfileResponse(CustomerProfileBase):
    id: int
    created_at: datetime
    updated_at: datetime
    interactions: List[InteractionLogSchema] = []
    sessions: List[ConversationSessionSchema] = []
    
    model_config = ConfigDict(from_attributes=True)

class CustomerIdentifyResponse(BaseModel):
    customer_id: str
    name: str
    phone: str
    is_returning: bool
    session_id: str
    greeting: str
    past_session_count: int
    interested_vehicle: str
    customer_profile: CustomerProfileBase

    model_config = ConfigDict(from_attributes=True)

class SaveTranscriptTurnRequest(BaseModel):
    session_id: str
    customer_id: str
    channel: str = "VOICE_LIVE"
    speaker: str # "customer", "mia", "system"
    message: str
    extracted_intent: Optional[str] = None
    tool_triggered: Optional[str] = None

class FullTranscriptMessageItem(BaseModel):
    speaker: str
    text: str
    timestamp: Optional[str] = None
    toolCall: Optional[str] = None
    language: Optional[str] = None

class SaveFullSessionTranscriptRequest(BaseModel):
    session_id: str
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    vehicle_id: Optional[str] = "thar_roxx"
    channel: Optional[str] = "VOICE_LIVE"
    messages: List[FullTranscriptMessageItem] = []
