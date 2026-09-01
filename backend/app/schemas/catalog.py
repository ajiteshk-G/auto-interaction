from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class VehicleVariant(BaseModel):
    name: str
    price_ex_showroom: str
    engine_or_battery: str
    transmission: str
    key_features: List[str]

class VehicleItem(BaseModel):
    id: str
    name: str
    tagline: str
    category: str # "Authentic SUV", "Tech SUV", "Born Electric SUV", "Commercial"
    price_range: str
    hero_image: str
    engine_specs: str
    seating_capacity: str
    fuel_or_battery: str
    range_or_mileage: str
    key_highlights: List[str]
    usp: str
    variants: List[VehicleVariant]
    is_custom_source_of_truth: bool = False
    uploaded_image_url: Optional[str] = None

class VehicleComparisonRequest(BaseModel):
    vehicle_ids: List[str]

class DealershipItem(BaseModel):
    id: str
    name: str
    address: str
    city: str
    phone: str
    rating: float
    available_advisors: List[str]
    has_test_drive_home_pickup: bool
