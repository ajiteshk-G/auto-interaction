import os
import uuid
import time
import shutil
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Body
from pydantic import BaseModel

from app.schemas.brand import (
    BrandCatalog,
    BrandSummary,
    BrandOnboardRequest,
    VehicleUpdateRequest,
    BrandUpdate
)
from app.schemas.catalog import VehicleItem
from app.services.brand_service import BrandService
from app.services.brand_crawler_service import BrandCrawlerService

logger = logging.getLogger("brand_router")
router = APIRouter(prefix="/brands", tags=["Brand Management & Studio"])

STATIC_UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "static",
    "uploads"
)
os.makedirs(STATIC_UPLOAD_DIR, exist_ok=True)

class SwitchBrandRequest(BaseModel):
    brand_id: str

@router.get("", response_model=List[BrandSummary])
async def list_brands():
    """List all available automotive brand profiles."""
    return BrandService.list_brands()

@router.get("/active", response_model=BrandCatalog)
async def get_active_brand():
    """Returns the currently active brand and its complete vehicle catalog."""
    return BrandService.get_active_brand()

@router.post("/active", response_model=BrandCatalog)
async def set_active_brand(req: SwitchBrandRequest):
    """Switches the active brand for the entire omnichannel application."""
    brand = BrandService.set_active_brand(req.brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail=f"Brand '{req.brand_id}' not found")
    return brand

@router.get("/{brand_id}", response_model=BrandCatalog)
async def get_brand(brand_id: str):
    brand = BrandService.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail=f"Brand '{brand_id}' not found")
    return brand

@router.post("/onboard", response_model=BrandCatalog)
async def onboard_brand(req: BrandOnboardRequest):
    """
    Onboard a brand by providing the brand name and one or more URLs.
    Crawls pages, extracts logos/vehicles/specs/images with Gemini, and registers brand.
    """
    if not req.brand_name.strip():
        raise HTTPException(status_code=400, detail="Brand name cannot be empty")
    if not req.urls:
        raise HTTPException(status_code=400, detail="At least one URL must be provided")

    try:
        catalog = await BrandCrawlerService.crawl_and_extract_catalog(
            brand_name=req.brand_name,
            urls=req.urls
        )
        saved = BrandService.onboard_or_save_brand(catalog, set_active=True)
        return saved
    except Exception as e:
        logger.error(f"Failed to onboard brand {req.brand_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to onboard brand: {str(e)}")

@router.post("/{brand_id}/upload-vehicle-image", response_model=VehicleItem)
async def upload_vehicle_image(
    brand_id: str,
    vehicle_id: str = Form(...),
    image: UploadFile = File(...)
):
    """
    Upload a replacement vehicle image directly. Marks the image as
    is_custom_source_of_truth = True, taking priority over any scraped image.
    """
    brand = BrandService.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail=f"Brand '{brand_id}' not found")

    ext = os.path.splitext(image.filename or "")[1].lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        ext = ".png"

    dest_dir = os.path.join(STATIC_UPLOAD_DIR, brand_id.lower(), "vehicles")
    os.makedirs(dest_dir, exist_ok=True)
    
    unique_name = f"{vehicle_id.lower()}_{int(time.time())}{ext}"
    dest_path = os.path.join(dest_dir, unique_name)

    try:
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(image.file, f)
    except Exception as e:
        logger.error(f"Failed saving uploaded vehicle image: {e}")
        raise HTTPException(status_code=500, detail="Failed to save image file")

    public_url = f"/uploads/{brand_id.lower()}/vehicles/{unique_name}"
    updated_v = BrandService.update_vehicle_image(brand_id, vehicle_id, public_url)
    if not updated_v:
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_id}' not found in brand '{brand_id}'")

    return updated_v

@router.post("/{brand_id}/upload-logo", response_model=BrandCatalog)
async def upload_brand_logo(
    brand_id: str,
    logo: UploadFile = File(...)
):
    """Upload custom brand logo, overriding scraped logo."""
    brand = BrandService.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail=f"Brand '{brand_id}' not found")

    ext = os.path.splitext(logo.filename or "")[1].lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp", ".svg"]:
        ext = ".png"

    dest_dir = os.path.join(STATIC_UPLOAD_DIR, brand_id.lower(), "logos")
    os.makedirs(dest_dir, exist_ok=True)

    unique_name = f"logo_{int(time.time())}{ext}"
    dest_path = os.path.join(dest_dir, unique_name)

    try:
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(logo.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to save logo file")

    public_url = f"/uploads/{brand_id.lower()}/logos/{unique_name}"
    updated = BrandService.update_brand_logo(brand_id, public_url)
    return updated

@router.put("/{brand_id}/vehicles/{vehicle_id}", response_model=VehicleItem)
async def update_vehicle(brand_id: str, vehicle_id: str, req: VehicleUpdateRequest):
    """Edit vehicle specs, tagline, name, or pricing in the catalog."""
    updated = BrandService.update_vehicle(brand_id, vehicle_id, req)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_id}' not found in brand '{brand_id}'")
    return updated

@router.post("/{brand_id}/vehicles", response_model=VehicleItem)
async def add_vehicle(brand_id: str, vehicle: VehicleItem):
    """Manually add a vehicle to the brand catalog."""
    vehicle.is_custom_source_of_truth = True
    added = BrandService.add_vehicle(brand_id, vehicle)
    if not added:
        raise HTTPException(status_code=404, detail=f"Brand '{brand_id}' not found")
    return added

@router.delete("/{brand_id}/vehicles/{vehicle_id}")
async def delete_vehicle(brand_id: str, vehicle_id: str):
    """Delete an incorrectly scraped vehicle from the catalog."""
    success = BrandService.delete_vehicle(brand_id, vehicle_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_id}' not found")
    return {"status": "deleted", "vehicle_id": vehicle_id}
