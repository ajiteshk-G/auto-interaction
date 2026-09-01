from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from app.schemas.catalog import VehicleItem, DealershipItem, VehicleComparisonRequest
from app.services.catalog_service import CatalogService
from app.services.cache_service import cache

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.database import get_db
from app.models.dealership import Dealership

router = APIRouter(prefix="/catalog", tags=["Vehicle Catalog"])

@router.get("", response_model=List[VehicleItem])
async def list_vehicles(category: Optional[str] = None):
    cache_key = f"vehicles_{category or 'all'}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    vehicles = CatalogService.get_all_vehicles()
    if category:
        result = [v for v in vehicles if v.category.lower() == category.lower()]
    else:
        result = vehicles

    cache.set(cache_key, result, ttl_seconds=600)
    return result

@router.get("/dealerships", response_model=List[DealershipItem])
async def list_dealerships(
    city: Optional[str] = None,
    brand_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    from app.services.brand_service import BrandService
    b_id = (brand_id or (BrandService.get_active_brand().id if BrandService.get_active_brand() else "mahindra")).lower()
    cache_key = f"dealerships_{b_id}_{city or 'all'}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    stmt = select(Dealership).where(Dealership.is_active == True, Dealership.brand_id == b_id)
    if city:
        stmt = stmt.where(func.lower(Dealership.city) == city.lower())
    res = await db.execute(stmt)
    dealers = res.scalars().all()
    if dealers:
        result = [
            DealershipItem(
                id=d.id,
                name=d.name,
                address=d.address,
                city=d.city,
                phone=d.phone,
                rating=d.rating or 4.8,
                available_advisors=d.available_advisors or ["Official Specialist"],
                has_test_drive_home_pickup=True
            )
            for d in dealers
        ]
        cache.set(cache_key, result, ttl_seconds=600)
        return result

    # Fallback from BrandService catalog if not yet seeded
    brand = BrandService.get_brand(b_id)
    if brand and brand.dealerships:
        result = [
            DealershipItem(
                id=d.id,
                name=d.name,
                address=d.address,
                city=d.city,
                phone=d.phone,
                rating=d.rating or 4.8,
                available_advisors=d.available_advisors or ["Official Specialist"],
                has_test_drive_home_pickup=True
            )
            for d in brand.dealerships
            if not city or d.city.lower() == city.lower()
        ]
        if result:
            cache.set(cache_key, result, ttl_seconds=600)
            return result

    fallback = CatalogService.get_dealerships()
    cache.set(cache_key, fallback, ttl_seconds=600)
    return fallback

@router.get("/{vehicle_id}", response_model=VehicleItem)
async def get_vehicle(vehicle_id: str):
    cache_key = f"vehicle_{vehicle_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    vehicle = CatalogService.get_vehicle_by_id(vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    cache.set(cache_key, vehicle, ttl_seconds=600)
    return vehicle

@router.post("/compare", response_model=List[VehicleItem])
async def compare_vehicles(req: VehicleComparisonRequest):
    return CatalogService.compare_vehicles(req.vehicle_ids)
