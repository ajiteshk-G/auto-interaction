from app.routers.health import router as health_router
from app.routers.catalog import router as catalog_router
from app.routers.customer import router as customer_router
from app.routers.bookings import router as bookings_router
from app.routers.diagnostics import router as diagnostics_router
from app.routers.sales_recording import router as sales_router
from app.routers.outbound_call import router as outbound_router
from app.routers.admin import router as admin_router
from app.routers.ws_live import router as ws_router
from app.routers.brand import router as brand_router

__all__ = [
    "health_router",
    "catalog_router",
    "customer_router",
    "bookings_router",
    "diagnostics_router",
    "sales_router",
    "outbound_router",
    "admin_router",
    "ws_router",
    "brand_router"
]
