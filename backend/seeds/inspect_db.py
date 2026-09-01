import os
import sys
import asyncio

# Add backend directory to sys.path dynamically
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.customer import Customer, ConversationSession, InteractionLog
from app.models.booking import TestDriveBooking

DATABASE_URL = "postgresql+asyncpg://postgres:MahindraDev2026!Secure@34.42.54.228:5432/mahindra_auto"

async def check():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as db:
        res = await db.execute(select(Customer))
        customers = res.scalars().all()
        print(f"Total customers in Cloud SQL: {len(customers)}", flush=True)
        for c in customers:
            print(f"Customer: ID={c.id}, Name='{c.name}', Phone='{c.phone}', Vehicle='{c.interested_vehicle_id}', Checklist={c.advisor_checklist}", flush=True)
            
        res_b = await db.execute(select(TestDriveBooking))
        bookings = res_b.scalars().all()
        print(f"\nTotal bookings in Cloud SQL: {len(bookings)}", flush=True)
        for b in bookings:
            print(f"Booking: Ref={b.booking_reference}, CustID={b.customer_id}, Vehicle={b.vehicle_id}, Status={b.status}, Dealership={b.dealership_name}, Checklist={b.advisor_checklist}", flush=True)

        res_i = await db.execute(select(InteractionLog))
        logs = res_i.scalars().all()
        print(f"\nTotal interaction logs in Cloud SQL: {len(logs)}", flush=True)
        for l in logs:
            print(f"Log: SessID={l.session_id}, CustID={l.customer_id}, Speaker={l.speaker}, Msg='{l.message}'", flush=True)
            
    await engine.dispose()

asyncio.run(check())
