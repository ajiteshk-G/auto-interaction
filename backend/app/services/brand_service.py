import os
import json
import logging
from typing import List, Optional, Dict
from app.schemas.brand import BrandCatalog, BrandSummary, VehicleUpdateRequest
from app.schemas.catalog import VehicleItem, VehicleVariant, DealershipItem
from app.services.cache_service import cache

logger = logging.getLogger("brand_service")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "brands")

class BrandService:
    _brands: Dict[str, BrandCatalog] = {}
    _active_brand_id: str = "mahindra"
    _initialized: bool = False

    @classmethod
    def initialize(cls):
        if cls._initialized:
            return
        os.makedirs(DATA_DIR, exist_ok=True)
        for fname in os.listdir(DATA_DIR):
            if fname.endswith(".json"):
                fpath = os.path.join(DATA_DIR, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        brand = BrandCatalog(**data)
                        cls._brands[brand.id] = brand
                        if brand.is_active:
                            cls._active_brand_id = brand.id
                except Exception as e:
                    logger.error(f"Error loading brand preset {fname}: {e}")
        
        if cls._active_brand_id not in cls._brands and cls._brands:
            cls._active_brand_id = next(iter(cls._brands.keys()))
            cls._brands[cls._active_brand_id].is_active = True
        cls._initialized = True
        logger.info(f"BrandService initialized with {len(cls._brands)} brands. Active brand: {cls._active_brand_id}")

    @classmethod
    def list_brands(cls) -> List[BrandSummary]:
        cls.initialize()
        summaries = []
        for b in cls._brands.values():
            summaries.append(BrandSummary(
                id=b.id,
                name=b.name,
                tagline=b.tagline,
                logo_url=b.logo_url,
                primary_color=b.primary_color,
                vehicle_count=len(b.vehicles),
                is_active=(b.id == cls._active_brand_id)
            ))
        return summaries

    @classmethod
    def get_brand(cls, brand_id: str) -> Optional[BrandCatalog]:
        cls.initialize()
        return cls._brands.get(brand_id.lower())

    @classmethod
    def get_active_brand(cls) -> BrandCatalog:
        cls.initialize()
        brand = cls._brands.get(cls._active_brand_id)
        if not brand:
            # Fallback to first brand
            cls._active_brand_id = next(iter(cls._brands.keys()))
            brand = cls._brands[cls._active_brand_id]
        return brand

    @classmethod
    def set_active_brand(cls, brand_id: str) -> Optional[BrandCatalog]:
        cls.initialize()
        brand_id = brand_id.lower()
        if brand_id not in cls._brands:
            return None
        for b in cls._brands.values():
            b.is_active = (b.id == brand_id)
            cls._save_to_disk(b)
        cls._active_brand_id = brand_id
        cache.invalidate()
        return cls._brands[brand_id]

    @classmethod
    def onboard_or_save_brand(cls, brand: BrandCatalog, set_active: bool = True) -> BrandCatalog:
        cls.initialize()
        brand.id = brand.id.lower()
        cls._brands[brand.id] = brand
        cls._save_to_disk(brand)
        if set_active:
            cls.set_active_brand(brand.id)
        return brand

    @classmethod
    def update_vehicle_image(cls, brand_id: str, vehicle_id: str, image_url: str) -> Optional[VehicleItem]:
        cls.initialize()
        brand = cls._brands.get(brand_id.lower())
        if not brand:
            return None
        for v in brand.vehicles:
            if v.id.lower() == vehicle_id.lower():
                v.hero_image = image_url
                v.uploaded_image_url = image_url
                v.is_custom_source_of_truth = True
                cls._save_to_disk(brand)
                return v
        return None

    @classmethod
    def update_brand_logo(cls, brand_id: str, logo_url: str) -> Optional[BrandCatalog]:
        cls.initialize()
        brand = cls._brands.get(brand_id.lower())
        if not brand:
            return None
        brand.logo_url = logo_url
        cls._save_to_disk(brand)
        return brand

    @classmethod
    def update_vehicle(cls, brand_id: str, vehicle_id: str, req: VehicleUpdateRequest) -> Optional[VehicleItem]:
        cls.initialize()
        brand = cls._brands.get(brand_id.lower())
        if not brand:
            return None
        for v in brand.vehicles:
            if v.id.lower() == vehicle_id.lower():
                if req.name is not None: v.name = req.name
                if req.tagline is not None: v.tagline = req.tagline
                if req.category is not None: v.category = req.category
                if req.price_range is not None: v.price_range = req.price_range
                if req.hero_image is not None:
                    v.hero_image = req.hero_image
                    v.is_custom_source_of_truth = True
                if req.engine_specs is not None: v.engine_specs = req.engine_specs
                if req.seating_capacity is not None: v.seating_capacity = req.seating_capacity
                if req.fuel_or_battery is not None: v.fuel_or_battery = req.fuel_or_battery
                if req.range_or_mileage is not None: v.range_or_mileage = req.range_or_mileage
                if req.key_highlights is not None: v.key_highlights = req.key_highlights
                if req.usp is not None: v.usp = req.usp
                if req.variants is not None: v.variants = req.variants
                v.is_custom_source_of_truth = True
                cls._save_to_disk(brand)
                return v
        return None

    @classmethod
    def add_vehicle(cls, brand_id: str, vehicle: VehicleItem) -> Optional[VehicleItem]:
        cls.initialize()
        brand = cls._brands.get(brand_id.lower())
        if not brand:
            return None
        # Remove existing if same ID
        brand.vehicles = [v for v in brand.vehicles if v.id.lower() != vehicle.id.lower()]
        brand.vehicles.append(vehicle)
        cls._save_to_disk(brand)
        return vehicle

    @classmethod
    def delete_vehicle(cls, brand_id: str, vehicle_id: str) -> bool:
        cls.initialize()
        brand = cls._brands.get(brand_id.lower())
        if not brand:
            return False
        initial_len = len(brand.vehicles)
        brand.vehicles = [v for v in brand.vehicles if v.id.lower() != vehicle_id.lower()]
        if len(brand.vehicles) < initial_len:
            cls._save_to_disk(brand)
            return True
        return False

    @classmethod
    def _save_to_disk(cls, brand: BrandCatalog):
        os.makedirs(DATA_DIR, exist_ok=True)
        fpath = os.path.join(DATA_DIR, f"{brand.id}.json")
        try:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(brand.model_dump(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist brand {brand.id}: {e}")
