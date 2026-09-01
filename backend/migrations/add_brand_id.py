import asyncio
import logging
from sqlalchemy import text
from app.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")

TABLES = [
    "customers",
    "conversation_sessions",
    "interaction_logs",
    "test_drive_bookings",
    "test_drive_slots",
    "dealerships",
    "test_ride_recordings",
    "outbound_call_logs",
    "insurance_claims"
]

async def apply_migration():
    logger.info("Starting multi-tenant database migration...")
    async with engine.connect() as conn:
        for t in TABLES:
            logger.info(f"Checking table {t} for brand_id...")
            has_col = await conn.execute(text(f"""
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = '{t}' AND column_name = 'brand_id'
            """))
            if not has_col.scalar():
                logger.info(f"Adding brand_id column to {t}...")
                await conn.execute(text(f"""
                    ALTER TABLE {t} ADD COLUMN brand_id VARCHAR(64) NOT NULL DEFAULT 'mahindra';
                """))
                await conn.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS ix_{t}_brand_id ON {t}(brand_id);
                """))
                await conn.commit()
                logger.info(f"Added brand_id to {t}.")
            else:
                logger.info(f"Table {t} already has brand_id.")

        # Update unique constraint on customers (phone + brand_id)
        logger.info("Updating customer phone uniqueness constraint...")
        try:
            await conn.execute(text("ALTER TABLE customers DROP CONSTRAINT IF EXISTS customers_phone_key;"))
            await conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_customers_phone_brand') THEN
                        ALTER TABLE customers ADD CONSTRAINT uq_customers_phone_brand UNIQUE (phone, brand_id);
                    END IF;
                END $$;
            """))
            await conn.commit()
            logger.info("Customer phone uniqueness constraint updated successfully.")
        except Exception as e:
            logger.warning(f"Constraint notice: {e}")

    logger.info("Migration complete!")

if __name__ == "__main__":
    asyncio.run(apply_migration())
