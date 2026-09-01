import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.database import engine, Base, AsyncSessionLocal
from app.services.customer_service import CustomerService
from app.services.brand_service import BrandService
from app.routers import (
    health_router,
    catalog_router,
    customer_router,
    bookings_router,
    diagnostics_router,
    sales_router,
    outbound_router,
    admin_router,
    ws_router,
    brand_router
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schemas on startup and load brands
    try:
        BrandService.initialize()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        # Seed default customer and dealerships & pre-warm cache
        async with AsyncSessionLocal() as db:
            await CustomerService.get_or_create_default_customer(db)
            try:
                from seeds.seed_dealerships import seed_dealerships
                await seed_dealerships()
            except Exception as se:
                print(f"Dealership seed info: {se}")
            
            # Prewarm cache for instantaneous response
            from sqlalchemy.future import select
            from app.models.dealership import Dealership
            from app.schemas.catalog import DealershipItem
            from app.services.cache_service import cache
            
            d_res = await db.execute(select(Dealership).where(Dealership.is_active == True))
            all_dealers = d_res.scalars().all()
            if all_dealers:
                items = [
                    DealershipItem(
                        id=d.id,
                        name=d.name,
                        address=d.address,
                        city=d.city,
                        phone=d.phone,
                        rating=d.rating or 4.8,
                        available_advisors=d.available_advisors or ["Rajesh Varma"],
                        has_test_drive_home_pickup=True
                    )
                    for d in all_dealers
                ]
                cache.set("dealerships_all", items, ttl_seconds=3600)
    except Exception as e:
        print(f"Startup notice: {e}")
        
    yield
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.1.0",
    description="Mahindra Omnichannel AI Platform (MIA) with Pre-Sales Live Avatar, Mobile Sales Test-Ride Recording, Outbound Voice Call Insights & Instant Digital Financing",
    lifespan=lifespan
)

# CORS Configuration for local Next.js frontend & Cloud Run
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static File Serving for Uploaded Images (Source of Truth)
STATIC_UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "static",
    "uploads"
)
os.makedirs(STATIC_UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=STATIC_UPLOAD_DIR), name="uploads")

# Mount REST Routers
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(brand_router, prefix=settings.API_V1_STR)
app.include_router(catalog_router, prefix=settings.API_V1_STR)
app.include_router(customer_router, prefix=settings.API_V1_STR)
app.include_router(bookings_router, prefix=settings.API_V1_STR)
app.include_router(diagnostics_router, prefix=settings.API_V1_STR)
app.include_router(sales_router, prefix=settings.API_V1_STR)
app.include_router(outbound_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix=settings.API_V1_STR)
app.include_router(ws_router)

@app.get("/")
async def root():
    active_b = BrandService.get_active_brand()
    return {
        "app": "Generic Automotive AI Platform (MIA Omnichannel)",
        "active_brand": {
            "id": active_b.id,
            "name": active_b.name,
            "tagline": active_b.tagline,
            "vehicle_count": len(active_b.vehicles)
        },
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health",
        "brands_api": f"{settings.API_V1_STR}/brands",
        "live_websocket": "/ws/live-audio"
    }
