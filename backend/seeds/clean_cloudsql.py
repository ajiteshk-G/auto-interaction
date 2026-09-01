import os
import sys
import asyncio
import logging
import argparse

# Add backend directory to sys.path dynamically
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("clean_cloudsql")

async def clean_database(preserve_name: str = "Ajitesh"):
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    logger.info("Connecting to Cloud SQL...")
    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        if preserve_name:
            res = await conn.execute(text(f"SELECT id, customer_id, name, phone FROM customers WHERE name ILIKE '%{preserve_name}%';"))
            preserved_rows = res.fetchall()
            if preserved_rows:
                pres_ids = [str(r[0]) for r in preserved_rows]
                id_filter = ", ".join(pres_ids)
                logger.info(f"Preserving records for {preserve_name} (IDs: {id_filter})")

                # Reset slots for non-preserved
                await conn.execute(text(f"""
                    UPDATE test_drive_slots 
                    SET status = 'AVAILABLE', customer_id = NULL, customer_name = NULL, customer_phone = NULL,
                        booking_reference = NULL, booking_type = NULL, delivery_address = NULL, pin_code = NULL, notes = NULL, reserved_at = NULL
                    WHERE (customer_id IS NOT NULL AND customer_id NOT IN ({id_filter}))
                       OR (customer_name IS NOT NULL AND customer_name NOT ILIKE '%{preserve_name}%');
                """))
                
                await conn.execute(text(f"DELETE FROM test_ride_recordings WHERE customer_id NOT IN ({id_filter});"))
                await conn.execute(text(f"DELETE FROM outbound_call_logs WHERE customer_id NOT IN ({id_filter});"))
                await conn.execute(text(f"DELETE FROM test_drive_bookings WHERE customer_id NOT IN ({id_filter});"))
                await conn.execute(text(f"DELETE FROM insurance_claims WHERE customer_id NOT IN ({id_filter});"))
                await conn.execute(text(f"""
                    DELETE FROM interaction_logs 
                    WHERE customer_id NOT IN ({id_filter}) 
                       OR session_id IN (SELECT id FROM conversation_sessions WHERE customer_id NOT IN ({id_filter}));
                """))
                await conn.execute(text(f"DELETE FROM conversation_sessions WHERE customer_id NOT IN ({id_filter});"))
                await conn.execute(text(f"DELETE FROM customers WHERE id NOT IN ({id_filter});"))
                logger.info(f"✓ Successfully purged records for everyone except {preserve_name}.")
            else:
                logger.warning(f"No customers found matching '{preserve_name}'. No rows deleted.")
        else:
            tables_to_clean = [
                "outbound_call_logs",
                "test_ride_recordings",
                "test_drive_bookings",
                "interaction_logs",
                "conversation_sessions",
                "insurance_claims",
                "customers"
            ]
            stmt = f"TRUNCATE TABLE {', '.join(tables_to_clean)} CASCADE;"
            logger.info(f"Executing: {stmt}")
            await conn.execute(text(stmt))
            logger.info("✓ Successfully truncated customer records.")

    await engine.dispose()
    logger.info("🎉 Cloud SQL clean-up finished.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean Cloud SQL customer data")
    parser.add_argument("--preserve", default="Ajitesh", help="Customer name to preserve (default: Ajitesh)")
    args = parser.parse_args()
    asyncio.run(clean_database(preserve_name=args.preserve))
