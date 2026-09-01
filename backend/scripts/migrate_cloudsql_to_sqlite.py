import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from app.database import Base
from app.models import (
    Customer, ConversationSession, InteractionLog,
    TestDriveBooking, TestDriveSlot, PublicHoliday, SlotConfig,
    Dealership, TestRideRecording, OutboundCallLog, InsuranceClaim
)

CLOUD_SQL_URL = "postgresql+asyncpg://postgres:MahindraDev2026!Secure@34.42.54.228:5432/mahindra_auto"
LOCAL_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "auto.db")
LOCAL_SQLITE_URL = f"sqlite+aiosqlite:///{LOCAL_DB_PATH}"

TABLE_MODEL_MAP = [
    ("dealerships", Dealership),
    ("public_holidays", PublicHoliday),
    ("slot_configs", SlotConfig),
    ("customers", Customer),
    ("test_drive_slots", TestDriveSlot),
    ("test_drive_bookings", TestDriveBooking),
    ("conversation_sessions", ConversationSession),
    ("interaction_logs", InteractionLog),
    ("test_ride_recordings", TestRideRecording),
    ("outbound_call_logs", OutboundCallLog),
    ("insurance_claims", InsuranceClaim)
]

async def migrate():
    print(f"Migrating Cloud SQL -> Local SQLite ({LOCAL_DB_PATH})...")
    os.makedirs(os.path.dirname(LOCAL_DB_PATH), exist_ok=True)
    
    # Remove existing SQLite db if present to ensure clean migration
    if os.path.exists(LOCAL_DB_PATH):
        os.remove(LOCAL_DB_PATH)

    cloud_engine = create_async_engine(CLOUD_SQL_URL)
    local_engine = create_async_engine(LOCAL_SQLITE_URL, connect_args={"check_same_thread": False})
    LocalSession = async_sessionmaker(bind=local_engine, class_=AsyncSession, expire_on_commit=False)

    # 1. Create tables in SQLite
    async with local_engine.begin() as local_conn:
        await local_conn.run_sync(Base.metadata.create_all)
    print("✓ Created SQLite schemas for all tables.")

    # 2. Copy data table by table using SQLAlchemy ORM for seamless type conversion
    async with cloud_engine.connect() as cloud_conn:
        for table_name, model_cls in TABLE_MODEL_MAP:
            res = await cloud_conn.execute(text(f"SELECT * FROM {table_name}"))
            cols = list(res.keys())
            rows = res.fetchall()
            
            if not rows:
                print(f"Table '{table_name}': 0 rows (skipped)")
                continue

            print(f"Migrating '{table_name}': {len(rows)} rows...")
            
            async with LocalSession() as local_session:
                async with local_session.begin():
                    for r in rows:
                        row_dict = {col: val for col, val in zip(cols, r)}
                        obj = model_cls(**row_dict)
                        local_session.add(obj)

            print(f"✓ Table '{table_name}': successfully migrated {len(rows)} rows.")

    print("\n--- Verifying Row Counts in Local SQLite DB ---")
    async with local_engine.connect() as local_conn:
        for table_name, _ in TABLE_MODEL_MAP:
            cnt = (await local_conn.execute(text(f'SELECT count(*) FROM "{table_name}"'))).scalar()
            print(f"  {table_name}: {cnt} rows")

    await cloud_engine.dispose()
    await local_engine.dispose()
    print("\n✓ Migration completed successfully!")

if __name__ == "__main__":
    asyncio.run(migrate())
