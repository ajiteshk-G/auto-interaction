from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict

class TestRideStartRequest(BaseModel):
    customer_id: str = Field(..., description="Customer ID, e.g. CUST-AARAV-001")
    vehicle_id: str = Field(default="thar_roxx", description="Vehicle model ID")
    variant: str = Field(default="AX7L Diesel AT 4x4", description="Vehicle variant")
    sales_advisor_name: str = Field(default="Rajesh Varma (Bayview Mahindra)", description="Advisor Name")
    dealership_name: str = Field(default="Bayview Mahindra, Bandra West", description="Dealership name")

class TestRideRecordingUploadRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="Test Ride session ID")
    customer_id: str = Field(..., description="Customer ID")
    booking_reference: Optional[str] = Field(None, description="Booking reference, e.g. BK-MAH-16859")
    customer_name: Optional[str] = Field(None, description="Customer Name")
    brand_id: Optional[str] = Field(None, description="Brand identifier, e.g. bmw, hyundai, maruti_suzuki, mahindra")
    vehicle_id: str = Field(default="thar_roxx")
    variant: str = Field(default="AX7L Diesel AT 4x4")
    sales_advisor_name: str = Field(default="Rajesh Varma (Bayview Mahindra)")
    audio_base64: Optional[str] = Field(None, description="Base64 encoded audio recording from mobile device")
    audio_format: str = Field(default="audio/wav")
    duration_seconds: int = Field(default=184)
    simulated_scenario: Optional[str] = Field(default="bandra_sea_link_test_ride")
    advisor_checklist: Optional[List[str]] = Field(None, description="Demonstrated checklist items")

class TestRideInsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    brand_id: Optional[str] = "mahindra"
    booking_reference: Optional[str] = None
    customer_id: Union[str, int]
    vehicle_id: str
    vehicle_name: str
    sales_advisor_name: str
    gcs_uri: str
    gcs_bucket: str
    gcs_object_path: Optional[str] = None
    duration_seconds: int
    transcript: str
    customer_sentiment_score: float
    purchase_intent_score: float
    loved_features: List[str]
    objections_raised: List[str]
    advisor_pitch_score: float
    advisor_coaching_feedback: str
    recommended_action: str
    status: str
    created_at: datetime

class TestRideLeadItem(BaseModel):
    customer_id: str
    brand_id: Optional[str] = "mahindra"
    name: str
    phone: str
    email: Optional[str] = None
    city: str
    preferred_vehicle: str
    vehicle_name: Optional[str] = None
    vehicle_id: Optional[str] = "thar_roxx"
    variant: Optional[str] = "AX7L Diesel AT 4x4"
    booking_reference: Optional[str] = None
    dealership_id: Optional[str] = None
    dealership_name: Optional[str] = None
    booking_type: Optional[str] = "HOME_DOORSTEP"
    delivery_address: Optional[str] = None
    booking_status: str
    scheduled_slot: Optional[str] = None
    presales_notes: Optional[str] = None
    advisor_checklist: Optional[List[str]] = None
    is_custom_checklist: Optional[bool] = False
