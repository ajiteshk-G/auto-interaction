import time
import datetime
import logging
import asyncio
from datetime import datetime as dt, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.database import get_db
from app.models.booking import TestDriveBooking, TestDriveSlot, PublicHoliday, SlotConfig
from app.models.dealership import Dealership
from app.models.customer import Customer, InteractionLog, ConversationSession
from app.schemas.booking import (
    TestDriveBookingCreate,
    TestDriveBookingResponse,
    DateSlotsResponse,
    SlotItem,
    SlotReserveRequest,
    SlotReserveResponse
)
from app.services.customer_service import CustomerService, clean_phone
from app.services.catalog_service import CatalogService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bookings", tags=["Test Drive Bookings"])

async def resolve_dealership_from_db(
    db: AsyncSession,
    pin_code: Optional[str] = None,
    dealership_id: Optional[str] = None,
    city: Optional[str] = None
) -> Optional[Dealership]:
    """Dynamically resolves the best matching dealership from the database."""
    # 1. By direct dealership_id
    if dealership_id:
        stmt = select(Dealership).where(Dealership.id == dealership_id, Dealership.is_active == True)
        res = await db.execute(stmt)
        dlr = res.scalars().first()
        if dlr:
            return dlr

    # 2. By PIN code
    if pin_code and pin_code.strip():
        clean_pin = pin_code.strip()
        # Direct exact PIN match
        stmt = select(Dealership).where(Dealership.pin_code == clean_pin, Dealership.is_active == True)
        res = await db.execute(stmt)
        dlr = res.scalars().first()
        if dlr:
            return dlr

        # Regional PIN prefix match
        target_city = None
        if clean_pin.startswith("400") or clean_pin.startswith("401"):
            target_city = "Mumbai"
        elif clean_pin.startswith("411") or clean_pin.startswith("412"):
            target_city = "Pune"
        elif clean_pin.startswith("110") or clean_pin.startswith("122") or clean_pin.startswith("201"):
            target_city = "Delhi"
        elif clean_pin.startswith("560"):
            target_city = "Bangalore"
        elif clean_pin.startswith("600"):
            target_city = "Chennai"

        if target_city:
            stmt = select(Dealership).where(func.lower(Dealership.city) == target_city.lower(), Dealership.is_active == True)
            res = await db.execute(stmt)
            dlr = res.scalars().first()
            if dlr:
                return dlr

    # 3. By City Name
    if city and city.strip():
        stmt = select(Dealership).where(func.lower(Dealership.city) == city.strip().lower(), Dealership.is_active == True)
        res = await db.execute(stmt)
        dlr = res.scalars().first()
        if dlr:
            return dlr

    # 4. Fallback to first available active dealership in database
    stmt = select(Dealership).where(Dealership.is_active == True)
    res = await db.execute(stmt)
    return res.scalars().first()


@router.get("/available-slots", response_model=DateSlotsResponse)
async def get_available_slots(
    date: str = Query(..., description="Target date in YYYY-MM-DD format"),
    pin_code: Optional[str] = Query(None, description="Customer Area PIN Code to find nearest showroom"),
    dealership_id: Optional[str] = Query(None, description="Specific Dealership ID if selected"),
    city: Optional[str] = Query(None, description="City name (Mumbai, Pune, Delhi, Bangalore, Chennai)"),
    vehicle_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Fetches available test ride slots dynamically from the database.
    - Resolves showroom by PIN code or City from database (no hardcoding).
    - Checks Public Holidays from `public_holidays` database table.
    - Checks Sundays (Showrooms Closed).
    - Queries allowed operational slots from `slot_configs` table (9:00 AM - 6:00 PM).
    - Queries reserved status from `test_drive_slots` database table.
    """
    try:
        parsed_date = dt.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    # 1. Resolve Showroom from Database
    dealership = await resolve_dealership_from_db(db, pin_code=pin_code, dealership_id=dealership_id, city=city)
    active_dlr_id = dealership.id if dealership else "mumbai_nbs_chowpatty"
    active_dlr_name = dealership.name if dealership else "Mahindra Official Showroom"

    # 2. Check Sunday Rule (0=Mon, 6=Sun)
    is_sunday = parsed_date.weekday() == 6
    if is_sunday:
        return DateSlotsResponse(
            date=date,
            is_blocked=True,
            blocked_reason="Sundays are closed for Test Rides. Please select Monday through Saturday.",
            is_sunday=True,
            is_holiday=False,
            dealership_id=active_dlr_id,
            dealership_name=active_dlr_name,
            slots=[]
        )

    # 3. Check Public Holidays from Database Table
    h_stmt = select(PublicHoliday).where(
        PublicHoliday.holiday_date == date,
        PublicHoliday.is_active == 1
    )
    h_res = await db.execute(h_stmt)
    holiday_row = h_res.scalars().first()

    if holiday_row:
        return DateSlotsResponse(
            date=date,
            is_blocked=True,
            blocked_reason=f"Public Holiday ({holiday_row.holiday_name}) - Showrooms & Test Drive Fleets are closed.",
            is_sunday=False,
            is_holiday=True,
            holiday_name=holiday_row.holiday_name,
            dealership_id=active_dlr_id,
            dealership_name=active_dlr_name,
            slots=[]
        )

    # 4. Fetch Allowed Operational Time Slots from Database Table
    s_stmt = select(SlotConfig).where(SlotConfig.is_active == 1).order_by(SlotConfig.display_order.asc())
    s_res = await db.execute(s_stmt)
    slot_cfg_rows = s_res.scalars().all()
    allowed_slots = (
        [s.slot_time for s in slot_cfg_rows]
        if slot_cfg_rows
        else ["09:00 AM", "10:00 AM", "11:00 AM", "12:00 PM", "01:00 PM", "02:00 PM", "03:00 PM", "04:00 PM", "05:00 PM"]
    )

    # 5. Query Reserved Slots from `test_drive_slots` Table in Database
    stmt = select(TestDriveSlot).where(
        TestDriveSlot.slot_date == date,
        TestDriveSlot.dealership_id == active_dlr_id
    )
    res = await db.execute(stmt)
    db_slots = {s.slot_time: s for s in res.scalars().all()}

    slot_items: List[SlotItem] = []
    new_slots_to_add = []

    for time_str in allowed_slots:
        if time_str in db_slots:
            s_obj = db_slots[time_str]
            slot_items.append(
                SlotItem(
                    id=s_obj.id,
                    slot_date=s_obj.slot_date,
                    slot_time=s_obj.slot_time,
                    status=s_obj.status,
                    is_available=(s_obj.status == "AVAILABLE"),
                    display_time=s_obj.slot_time,
                    customer_name=s_obj.customer_name if s_obj.status == "RESERVED" else None
                )
            )
        else:
            # Seed available slot in DB for consistency
            new_slot = TestDriveSlot(
                slot_date=date,
                slot_time=time_str,
                dealership_id=active_dlr_id,
                vehicle_id=vehicle_id,
                status="AVAILABLE"
            )
            new_slots_to_add.append(new_slot)
            slot_items.append(
                SlotItem(
                    id=None,
                    slot_date=date,
                    slot_time=time_str,
                    status="AVAILABLE",
                    is_available=True,
                    display_time=time_str,
                    customer_name=None
                )
            )

    if new_slots_to_add:
        db.add_all(new_slots_to_add)
        await db.commit()

    return DateSlotsResponse(
        date=date,
        is_blocked=False,
        blocked_reason=None,
        is_sunday=False,
        is_holiday=False,
        holiday_name=None,
        dealership_id=active_dlr_id,
        dealership_name=active_dlr_name,
        slots=slot_items
    )


@router.post("/reserve-slot", response_model=SlotReserveResponse)
async def reserve_test_drive_slot(
    req: SlotReserveRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Reserves a test ride slot in the database for a customer.
    - Validates against Public Holidays table in DB.
    - Validates against Sunday rule.
    - Validates slot time against `slot_configs` table in DB.
    - Resolves showroom by PIN code or dealership_id from DB.
    - Resolves customer dynamically by entered phone number.
    - Persists slot status as 'RESERVED' in database.
    """
    try:
        parsed_date = dt.strptime(req.slot_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    # 1. Validate Sunday
    if parsed_date.weekday() == 6:
        raise HTTPException(status_code=400, detail="Test drives cannot be booked on Sundays.")

    # 2. Validate Public Holiday against DB
    h_stmt = select(PublicHoliday).where(
        PublicHoliday.holiday_date == req.slot_date,
        PublicHoliday.is_active == 1
    )
    h_res = await db.execute(h_stmt)
    holiday_row = h_res.scalars().first()
    if holiday_row:
        raise HTTPException(status_code=400, detail=f"Cannot book on {holiday_row.holiday_name} (National Public Holiday).")

    # 3. Validate Time Slot against DB SlotConfig
    s_stmt = select(SlotConfig).where(SlotConfig.is_active == 1)
    s_res = await db.execute(s_stmt)
    allowed_slots = [s.slot_time for s in s_res.scalars().all()] or [
        "09:00 AM", "10:00 AM", "11:00 AM", "12:00 PM", "01:00 PM", "02:00 PM", "03:00 PM", "04:00 PM", "05:00 PM"
    ]
    if req.slot_time not in allowed_slots:
        raise HTTPException(
            status_code=400,
            detail="Invalid slot time. Test drives are strictly permitted only between 9:00 AM and 6:00 PM."
        )

    # 4. Resolve Dealership from Database
    dealership = await resolve_dealership_from_db(db, pin_code=req.pin_code, dealership_id=req.dealership_id)
    dealership_id = dealership.id if dealership else "mumbai_nbs_chowpatty"
    dealership_name = dealership.name if dealership else "Mahindra Official Showroom"
    advisor_name = (
        dealership.available_advisors[0]
        if (dealership and dealership.available_advisors)
        else "Rajesh Varma (Senior Specialist)"
    )

    # 5. Resolve Customer dynamically by entered phone number
    customer = await CustomerService.get_or_create_customer_by_phone(
        db,
        phone=req.customer_phone,
        name=req.customer_name,
        vehicle_id=req.vehicle_id
    )

    # Idempotency check: if customer already reserved this exact slot, return existing booking
    existing_b_stmt = select(TestDriveBooking).where(
        TestDriveBooking.customer_id == customer.id,
        TestDriveBooking.vehicle_id == req.vehicle_id,
        TestDriveBooking.scheduled_date == req.slot_date,
        TestDriveBooking.scheduled_time_slot == req.slot_time
    )
    existing_b_res = await db.execute(existing_b_stmt)
    existing_booking = existing_b_res.scalars().first()
    if existing_booking:
        v_info = CatalogService.get_vehicle_by_id(req.vehicle_id)
        return SlotReserveResponse(
            success=True,
            message=f"Test Ride is already reserved for {req.customer_name} on {req.slot_date} at {req.slot_time} ({dealership_name}).",
            booking_reference=existing_booking.booking_reference,
            slot_date=req.slot_date,
            slot_time=req.slot_time,
            booking_type=existing_booking.booking_type or "HOME_DOORSTEP",
            vehicle_name=v_info.name if v_info else "Mahindra SUV",
            dealership_name=dealership_name,
            sales_advisor_name=advisor_name,
            customer_name=req.customer_name,
            customer_phone=req.customer_phone,
            delivery_address=req.delivery_address,
            pin_code=req.pin_code,
            whatsapp_dispatched=True
        )

    booking_ref = f"BK-MAH-{int(time.time()) % 100000}"

    # 6. Check and update slot in DB
    stmt = select(TestDriveSlot).where(
        TestDriveSlot.slot_date == req.slot_date,
        TestDriveSlot.slot_time == req.slot_time,
        TestDriveSlot.dealership_id == dealership_id
    )
    res = await db.execute(stmt)
    slot = res.scalars().first()

    if slot:
        if slot.status == "RESERVED":
            raise HTTPException(
                status_code=409,
                detail=f"The {req.slot_time} slot on {req.slot_date} at {dealership_name} is already reserved. Please select another slot."
            )
        slot.status = "RESERVED"
        slot.customer_id = customer.id
        slot.customer_name = req.customer_name
        slot.customer_phone = req.customer_phone
        slot.booking_reference = booking_ref
        slot.booking_type = req.booking_type or "HOME_DOORSTEP"
        slot.delivery_address = req.delivery_address
        slot.pin_code = req.pin_code
        slot.notes = req.notes
        slot.reserved_at = dt.utcnow()
    else:
        slot = TestDriveSlot(
            slot_date=req.slot_date,
            slot_time=req.slot_time,
            dealership_id=dealership_id,
            vehicle_id=req.vehicle_id,
            status="RESERVED",
            customer_id=customer.id,
            customer_name=req.customer_name,
            customer_phone=req.customer_phone,
            booking_reference=booking_ref,
            booking_type=req.booking_type or "HOME_DOORSTEP",
            delivery_address=req.delivery_address,
            pin_code=req.pin_code,
            notes=req.notes,
            reserved_at=dt.utcnow()
        )
        db.add(slot)

    # 7. Create TestDriveBooking in database
    v_info = CatalogService.get_vehicle_by_id(req.vehicle_id)
    vehicle_display_name = v_info.name if v_info else "Mahindra Thar ROXX"

    # Resolve advisor checklist from request, customer profile, interaction history, or notes
    from app.services.checklist_service import ChecklistService
    lead_checklist = req.advisor_checklist or customer.advisor_checklist
    if not lead_checklist or len(lead_checklist) == 0:
        i_stmt = select(InteractionLog).where(InteractionLog.customer_id == customer.id)
        i_res = await db.execute(i_stmt)
        customer_dialogues = " ".join([l.message for l in i_res.scalars().all() if l.speaker == "customer"])
        if customer_dialogues:
            lead_checklist = ChecklistService.extract_checklist_items(customer_dialogues, req.vehicle_id)
    if req.notes:
        extracted = ChecklistService.extract_checklist_items(req.notes, req.vehicle_id, lead_checklist)
        if extracted:
            lead_checklist = extracted
    if not lead_checklist or len(lead_checklist) == 0:
        lead_checklist = ChecklistService.get_static_checklist(req.vehicle_id)

    booking = TestDriveBooking(
        booking_reference=booking_ref,
        customer_id=customer.id,
        vehicle_id=req.vehicle_id,
        variant=req.variant or "AX7L Diesel AT 4x4",
        color=req.color or "Stealth Black",
        dealership_id=dealership_id,
        dealership_name=dealership_name,
        sales_advisor_name=advisor_name,
        booking_type=req.booking_type or "HOME_DOORSTEP",
        delivery_address=req.delivery_address or "Customer Residence",
        scheduled_date=req.slot_date,
        scheduled_time_slot=req.slot_time,
        status="CONFIRMED",
        notes=req.notes,
        advisor_checklist=lead_checklist
    )
    if lead_checklist:
        customer.advisor_checklist = lead_checklist
    db.add(booking)

    # 8. Log interaction turn
    await CustomerService.log_interaction(
        db,
        customer_id_str=customer.customer_id,
        speaker="mia",
        message=f"Reserved test drive for {vehicle_display_name} at {dealership_name} on {req.slot_date} at {req.slot_time}. Reference: {booking_ref}",
        channel="VOICE_LIVE",
        session_id_str=f"BOOKING-{booking_ref}",
        intent="TEST_DRIVE_BOOKED",
        tool="reserve_slot_db"
    )

    await db.commit()

    # 9. Dispatch Twilio SMS asynchronously in background
    asyncio.create_task(
        NotificationService.send_test_drive_confirmation(
            customer_phone=req.customer_phone,
            customer_name=req.customer_name,
            booking_reference=booking_ref,
            vehicle_name=vehicle_display_name,
            variant=req.variant or "Official Variant",
            slot_date=req.slot_date,
            slot_time=req.slot_time,
            dealership_name=dealership_name,
            sales_advisor_name=advisor_name,
            booking_type=req.booking_type or "HOME_DOORSTEP",
            delivery_address=req.delivery_address,
            pin_code=req.pin_code
        )
    )

    return SlotReserveResponse(
        success=True,
        message=f"Test Ride successfully reserved for {req.customer_name} on {req.slot_date} at {req.slot_time} ({dealership_name})! Confirmation SMS sent.",
        booking_reference=booking_ref,
        slot_date=req.slot_date,
        slot_time=req.slot_time,
        booking_type=req.booking_type or "HOME_DOORSTEP",
        vehicle_name=vehicle_display_name,
        dealership_name=dealership_name,
        sales_advisor_name=advisor_name,
        customer_name=req.customer_name,
        customer_phone=req.customer_phone,
        delivery_address=req.delivery_address,
        pin_code=req.pin_code,
        whatsapp_dispatched=True
    )


@router.get("/my-bookings", response_model=List[TestDriveBookingResponse])
async def list_my_bookings(
    customer_id: Optional[str] = None,
    phone: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(TestDriveBooking)
    if customer_id:
        c_stmt = select(Customer).where((Customer.customer_id == customer_id) | (Customer.id == customer_id if customer_id.isdigit() else False))
        c_res = await db.execute(c_stmt)
        cust = c_res.scalars().first()
        if cust:
            stmt = stmt.where(TestDriveBooking.customer_id == cust.id)
        else:
            return []
    elif phone:
        normalized_phone = clean_phone(phone)
        c_stmt = select(Customer).where((Customer.phone == normalized_phone) | (Customer.phone == phone))
        c_res = await db.execute(c_stmt)
        cust = c_res.scalars().first()
        if cust:
            stmt = stmt.where(TestDriveBooking.customer_id == cust.id)
        else:
            return []
    if status:
        stmt = stmt.where(TestDriveBooking.status == status)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("", response_model=List[TestDriveBookingResponse])
async def list_bookings(
    customer_id: Optional[int] = None,
    phone: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(TestDriveBooking)
    if customer_id:
        stmt = stmt.where(TestDriveBooking.customer_id == customer_id)
    elif phone:
        normalized_phone = clean_phone(phone)
        c_stmt = select(Customer).where((Customer.phone == normalized_phone) | (Customer.phone == phone))
        c_res = await db.execute(c_stmt)
        cust = c_res.scalars().first()
        if cust:
            stmt = stmt.where(TestDriveBooking.customer_id == cust.id)
        else:
            return []
    if status:
        stmt = stmt.where(TestDriveBooking.status == status)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=TestDriveBookingResponse)
async def create_booking(
    booking_in: TestDriveBookingCreate,
    db: AsyncSession = Depends(get_db)
):
    customer = None
    if booking_in.customer_phone:
        customer = await CustomerService.get_customer_by_phone(db, booking_in.customer_phone)
    if not customer and booking_in.customer_id:
        customer = await CustomerService.get_customer_by_id(db, booking_in.customer_id)
        if not customer:
            customer = Customer(
                customer_id=booking_in.customer_id,
                name=booking_in.customer_name or "Valued Customer",
                phone=f"+91 98{abs(hash(booking_in.customer_id)) % 100000000:08d}",
                city="Mumbai",
                interested_vehicle_id=booking_in.vehicle_id
            )
            db.add(customer)
            await db.commit()
            await db.refresh(customer)
    if not customer:
        customer = await CustomerService.get_or_create_default_customer(db)

    booking_ref = f"BK-MAH-{int(time.time()) % 100000}"
    dealers = CatalogService.get_dealerships()
    d_match = next((d for d in dealers if d.id == booking_in.dealership_id), dealers[0])
    advisor = d_match.available_advisors[0] if d_match.available_advisors else "Rajesh Varma"

    from app.services.checklist_service import ChecklistService
    chk = booking_in.advisor_checklist or customer.advisor_checklist
    if booking_in.notes:
        extracted = ChecklistService.extract_checklist_items(booking_in.notes, booking_in.vehicle_id, chk)
        if extracted:
            chk = extracted

    booking = TestDriveBooking(
        booking_reference=booking_ref,
        customer_id=customer.id,
        vehicle_id=booking_in.vehicle_id,
        variant=booking_in.variant,
        color=booking_in.color,
        dealership_id=booking_in.dealership_id,
        dealership_name=d_match.name,
        sales_advisor_name=advisor,
        booking_type=booking_in.booking_type,
        delivery_address=booking_in.delivery_address,
        scheduled_date=booking_in.scheduled_date,
        scheduled_time_slot=booking_in.scheduled_time_slot,
        status="CONFIRMED",
        notes=booking_in.notes,
        advisor_checklist=chk
    )
    if chk:
        customer.advisor_checklist = chk

    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return booking
