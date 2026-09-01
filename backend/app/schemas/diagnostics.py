from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class DamageAssessmentRequest(BaseModel):
    customer_id: str
    vehicle_vin: Optional[str] = None
    image_base64: Optional[str] = None
    video_feed_enabled: bool = False
    mock_damage_type: Optional[str] = "bumper_foglamp" # "bumper_foglamp", "windshield_chip", "door_scratch"

class DamageAssessmentResponse(BaseModel):
    damage_detected: bool
    severity: str # "MINOR", "MODERATE", "CRITICAL"
    detected_parts: List[str]
    structural_damage: bool
    recommended_oem_part: str
    oem_part_number: str
    estimated_part_cost: float
    estimated_labor_cost: float
    estimated_out_of_pocket: float
    recommended_workshop: str
    parts_dispatch_eta: str
    gemini_vision_summary: str

class WarningLightScanRequest(BaseModel):
    image_base64: Optional[str] = None
    light_symbol: Optional[str] = "engine_oil_pressure"

class WarningLightScanResponse(BaseModel):
    symbol_name: str
    severity: str
    explanation: str
    recommended_action: str
    safe_to_drive: bool

class ClaimSubmissionRequest(BaseModel):
    customer_id: str
    vin: str
    vehicle_model: str
    incident_description: str
    detected_damages: List[str]
    oem_part_number: str
    workshop_name: str = "Bayview Mahindra Workshop"

class ClaimSubmissionResponse(BaseModel):
    id: int
    claim_id: str
    customer_id: int
    vin: str
    vehicle_model: str
    oem_part_number: str
    insurer_name: str
    policy_number: str
    claim_status: str
    workshop_name: str
    parts_delivery_estimate: str
    customer_out_of_pocket: float
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
