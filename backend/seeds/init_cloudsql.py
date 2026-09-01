import os
import sys
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("init_cloudsql")

# Add backend to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import engine, Base, AsyncSessionLocal
import app.models
from seeds.seed_dealerships import seed_dealerships
from app.services.customer_service import CustomerService
from app.models.dealership import Dealership
from sqlalchemy import select

async def main():
    db_url = str(engine.url)
    # Mask password for logging
    if ":" in db_url and "@" in db_url:
        masked_url = db_url.split(":")[0] + "://" + db_url.split(":")[1].split("@")[0].split("/")[-1] + ":***@" + db_url.split("@")[1]
    else:
        masked_url = db_url
    
    logger.info(f"Connecting to database: {masked_url}")
    
    # 1. Create tables
    async with engine.begin() as conn:
        logger.info("Creating all database tables if not present...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("✓ Tables created successfully.")

    # 2. Seed dealerships, holidays, slots
    logger.info("Seeding dealerships, holidays, and slots...")
    await seed_dealerships()

    # 3. Seed default customer
    async with AsyncSessionLocal() as db:
        cust = await CustomerService.get_or_create_default_customer(db)
        logger.info(f"✓ Default Customer ready: {cust.name} ({cust.customer_id})")

        d_res = await db.execute(select(Dealership))
        all_dealers = d_res.scalars().all()
        logger.info(f"✓ Total Dealerships in Database: {len(all_dealers)}")

    logger.info("🎉 Cloud SQL database initialization and seed complete!")

if __name__ == "__main__":
    asyncio.run(main())
