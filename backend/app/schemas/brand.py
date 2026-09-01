from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.catalog import VehicleItem, VehicleVariant, DealershipItem

class BrandBase(BaseModel):
    id: str
    name: str
    tagline: str
    logo_url: str
    primary_color: str = "#d71920"
    secondary_color: str = "#1e293b"
    accent_color: str = "#0ea5e9"
    avatar_name: str = "Assistant"
    avatar_voice: str = "Puck"
    source_urls: List[str] = Field(default_factory=list)
    is_active: bool = False

class BrandCreate(BrandBase):
    pass

class BrandUpdate(BaseModel):
    name: Optional[str] = None
    tagline: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    avatar_name: Optional[str] = None
    avatar_voice: Optional[str] = None

class BrandCatalog(BrandBase):
    vehicles: List[VehicleItem] = Field(default_factory=list)
    dealerships: List[DealershipItem] = Field(default_factory=list)

class BrandSummary(BaseModel):
    id: str
    name: str
    tagline: str
    logo_url: str
    primary_color: str
    vehicle_count: int
    is_active: bool

class BrandOnboardRequest(BaseModel):
    brand_name: str
    urls: Optional[List[str]] = Field(default_factory=list)

class VehicleUpdateRequest(BaseModel):
    name: Optional[str] = None
    tagline: Optional[str] = None
    category: Optional[str] = None
    price_range: Optional[str] = None
    hero_image: Optional[str] = None
    engine_specs: Optional[str] = None
    seating_capacity: Optional[str] = None
    fuel_or_battery: Optional[str] = None
    range_or_mileage: Optional[str] = None
    key_highlights: Optional[List[str]] = None
    usp: Optional[str] = None
    variants: Optional[List[VehicleVariant]] = None
