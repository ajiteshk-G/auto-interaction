import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dealership import Dealership
from app.models.customer import Customer, ConversationSession, InteractionLog
from app.models.booking import TestDriveBooking, TestDriveSlot
from app.models.sales_ride import TestRideRecording, OutboundCallLog
from app.schemas.brand import BrandCatalog, VehicleItem
from app.database import AsyncSessionLocal

logger = logging.getLogger("seed_generator_service")

PROSPECT_NAMES = [
    ("Kunal Mathuria", "+9198196500", "kunal.mathuria@corp.in", "Mumbai"),
    ("Aditi Sharma", "+9198201500", "aditi.sharma@techventure.com", "Mumbai"),
    ("Rohan Mehta", "+9198202500", "rohan.mehta@finadvisors.in", "Mumbai"),
    ("Pooja Varma", "+9198203500", "pooja.varma@designstudio.org", "Pune"),
    ("Siddharth Rao", "+9198204500", "siddharth.rao@globalcloud.com", "Bangalore"),
    ("Ananya Deshmukh", "+9198205500", "ananya.d@lawchambers.in", "Mumbai"),
    ("Gaurav Joshi", "+9198206500", "gaurav.joshi@enterprises.com", "Delhi"),
    ("Deepika Sen", "+9198207500", "deepika.sen@consultancy.in", "Mumbai"),
    ("Varun Nair", "+9198208500", "varun.nair@aerotech.in", "Bangalore"),
    ("Neha Kapoor", "+9198209500", "neha.kapoor@luxuryliving.in", "Delhi")
]

class SeedGeneratorService:
    @classmethod
    async def seed_data_for_brand(cls, db: AsyncSession, brand: BrandCatalog) -> Dict[str, Any]:
        """
        Ensures dealerships and auto-generates rich seed data for all vehicles in a newly onboarded brand.
        """
        b_id = brand.id.lower()
        logger.info(f"Starting auto-seed for brand: {brand.name} ({b_id})")

        try:
            dealerships = await cls.ensure_dealerships_for_brand(db, brand)

            results = []
            for vehicle in brand.vehicles:
                res = await cls.seed_data_for_vehicle(db, brand, vehicle, default_dealerships=dealerships)
                results.append(res)

            await db.commit()
            logger.info(f"Auto-seed completed for brand {brand.name}: {len(results)} vehicles seeded.")
            return {
                "brand_id": b_id,
                "dealerships_count": len(dealerships),
                "vehicles_seeded": len(results),
                "details": results
            }
        except Exception as e:
            await db.rollback()
            logger.error(f"Auto-seed failed for brand {brand.name}: {e}", exc_info=True)
            raise e

    @classmethod
    async def seed_data_for_brand_background(cls, brand: BrandCatalog):
        """
        Runs auto-seeding in a dedicated background task and session without blocking the HTTP response.
        """
        try:
            async with AsyncSessionLocal() as db:
                await cls.seed_data_for_brand(db, brand)
        except Exception as e:
            logger.warning(f"Background auto-seed notice for brand '{brand.name}': {e}")

    @classmethod
    async def seed_data_for_vehicle(
        cls,
        db: AsyncSession,
        brand_or_id: Any,
        vehicle: VehicleItem,
        default_dealerships: Optional[List[Dealership]] = None
    ) -> Dict[str, Any]:
        """
        Automatically generates complete omnichannel seed data for a single vehicle:
        - Customer profiles (with budget, pre-approved financing, KYC, and advisor checklists)
        - 2 Test Drive Bookings (1 completed test ride + 1 confirmed upcoming lead)
        - Test Ride Recording with realistic in-vehicle transcript, sentiment & loved features
        - Outbound Call Log with post-ride follow-up conversation and stock lock
        - Pre-sales showroom conversation session and transcript turns
        """
        if isinstance(brand_or_id, str):
            b_id = brand_or_id.lower()
            b_name = b_id.title()
            agent_name = "AI Specialist"
        else:
            b_id = brand_or_id.id.lower()
            b_name = brand_or_id.name
            agent_name = getattr(brand_or_id, "avatar_name", None) or getattr(brand_or_id, "agent_name", None) or "AI Specialist"

        v_id = vehicle.id.lower()
        v_name = vehicle.name
        def _get_variant_name(v_obj, default_name: str) -> str:
            if not v_obj:
                return default_name
            if isinstance(v_obj, str):
                return v_obj
            return getattr(v_obj, "name", None) or default_name

        variant_1 = _get_variant_name(vehicle.variants[0] if vehicle.variants and len(vehicle.variants) > 0 else None, f"{v_name} Top Variant")
        variant_2 = _get_variant_name(vehicle.variants[-1] if vehicle.variants and len(vehicle.variants) > 1 else None, f"{v_name} Executive Edition")

        b_code = b_id.replace("_", "").upper()[:4]
        v_slug = hashlib.md5(v_id.encode()).hexdigest()[:4].upper()

        if not default_dealerships:
            default_dealerships = await cls.ensure_dealerships_for_brand(db, brand_or_id)

        dealer_1 = default_dealerships[0] if default_dealerships else None
        dealer_2 = default_dealerships[1] if len(default_dealerships) > 1 else dealer_1

        dealer_id_1 = dealer_1.id if dealer_1 else f"{b_id}_worli_center"
        dealer_name_1 = dealer_1.name if dealer_1 else f"{b_name} Experience Center - Worli"
        advisor_1 = dealer_1.available_advisors[0] if (dealer_1 and dealer_1.available_advisors) else f"Rajesh Varma ({b_name} Specialist)"

        dealer_id_2 = dealer_2.id if dealer_2 else dealer_id_1
        dealer_name_2 = dealer_2.name if dealer_2 else dealer_name_1
        advisor_2 = dealer_2.available_advisors[-1] if (dealer_2 and dealer_2.available_advisors) else f"Amit Saxena ({b_name} Consultant)"

        ref_completed = f"BK-{b_code}-{v_slug}-101"
        ref_upcoming = f"BK-{b_code}-{v_slug}-102"

        stmt_check = select(TestDriveBooking).where(TestDriveBooking.booking_reference == ref_completed)
        res_check = await db.execute(stmt_check)
        if res_check.scalars().first():
            logger.info(f"Seed data already exists for vehicle {v_id} ({ref_completed}). Skipping.")
            return {"vehicle_id": v_id, "status": "already_seeded", "booking_reference": ref_completed}

        hash_val = int(hashlib.md5(f"{b_id}_{v_id}".encode()).hexdigest(), 16)
        p1_idx = hash_val % len(PROSPECT_NAMES)
        p2_idx = (hash_val + 3) % len(PROSPECT_NAMES)

        p1_base = PROSPECT_NAMES[p1_idx]
        p2_base = PROSPECT_NAMES[p2_idx]

        phone_suffix_1 = f"{(hash_val % 90 + 10):02d}"
        phone_suffix_2 = f"{((hash_val + 17) % 90 + 10):02d}"
        phone_1 = f"{p1_base[1]}{phone_suffix_1}"
        phone_2 = f"{p2_base[1]}{phone_suffix_2}"

        # Customer 1 (Completed Test Ride Customer)
        cust_1_id_str = f"CUST-{b_code}-{v_slug}-01"
        stmt_c1 = select(Customer).where((Customer.customer_id == cust_1_id_str) | ((Customer.phone == phone_1) & (Customer.brand_id == b_id)))
        res_c1 = await db.execute(stmt_c1)
        cust_1 = res_c1.scalars().first()
        if not cust_1:
            cust_1 = Customer(
                customer_id=cust_1_id_str,
                brand_id=b_id,
                name=p1_base[0],
                phone=phone_1,
                email=f"{p1_base[0].lower().replace(' ', '.')}.{b_id}@example.com",
                city=p1_base[3],
                preferred_language="Hinglish",
                current_phase="POST_SALES",
                interested_vehicle_id=v_id,
                interested_variant=variant_1,
                budget_range=vehicle.price_range or "₹20 Lakh - ₹35 Lakh",
                loan_preapproval_amount=2200000,
                loan_interest_rate="8.15%",
                loan_status="PRE_APPROVED",
                owned_vin=f"{b_code}1{v_slug}2026MUM01",
                owned_vehicle_name=f"{b_name} {v_name} {variant_1}",
                registration_number=f"MH 01 {b_code} {phone_suffix_1}01",
                odometer_km=8450,
                insurance_policy_number=f"POL-{b_code}-2026-{phone_suffix_1}01",
                insurance_type="Zero Depreciation Comprehensive with Engine Protect",
                kyc_status="VERIFIED",
                advisor_checklist=[
                    f"Demonstrate {v_name} powertrain: {vehicle.engine_specs or 'High-torque smooth engine'}",
                    f"Showcase key USP: {vehicle.usp or 'Advanced ride quality and premium interior'}",
                    f"Test drive on open stretch to evaluate acceleration and cabin sound insulation",
                    f"Review priority delivery allocation and promotional finance rates"
                ]
            )
            db.add(cust_1)
            await db.flush()

        # Customer 2 (Active Sales Lead Customer for Tomorrow)
        cust_2_id_str = f"CUST-{b_code}-{v_slug}-02"
        stmt_c2 = select(Customer).where((Customer.customer_id == cust_2_id_str) | ((Customer.phone == phone_2) & (Customer.brand_id == b_id)))
        res_c2 = await db.execute(stmt_c2)
        cust_2 = res_c2.scalars().first()
        if not cust_2:
            cust_2 = Customer(
                customer_id=cust_2_id_str,
                brand_id=b_id,
                name=p2_base[0],
                phone=phone_2,
                email=f"{p2_base[0].lower().replace(' ', '.')}.{b_id}@example.com",
                city=p2_base[3],
                preferred_language="Hinglish",
                current_phase="PRE_SALES",
                interested_vehicle_id=v_id,
                interested_variant=variant_2,
                budget_range=vehicle.price_range or "₹18 Lakh - ₹30 Lakh",
                loan_preapproval_amount=1950000,
                loan_interest_rate="8.20%",
                loan_status="PRE_APPROVED",
                owned_vin=f"{b_code}1{v_slug}2026MUM02",
                owned_vehicle_name=f"{b_name} Previous Generation",
                registration_number=f"MH 02 {b_code} {phone_suffix_2}02",
                odometer_km=32100,
                insurance_policy_number=f"POL-{b_code}-2026-{phone_suffix_2}02",
                insurance_type="Comprehensive Return-to-Invoice",
                kyc_status="VERIFIED",
                advisor_checklist=[
                    f"Evaluate exchange valuation for existing vehicle against new {v_name}",
                    f"Demonstrate touchscreen infotainment, wireless Apple CarPlay/Android Auto",
                    f"Experience ride quality on uneven surfaces and rear seat comfort",
                    f"Provide on-road quotation for {variant_2} with accessories package"
                ]
            )
            db.add(cust_2)
            await db.flush()

        # 3. Create Pre-Sales Conversation Session & Interaction Turns for Customer 1
        sess_uid = f"SESS-{b_code}-{v_slug}-PRE01"
        sess_stmt = select(ConversationSession).where(ConversationSession.session_id == sess_uid)
        sess_res = await db.execute(sess_stmt)
        sess = sess_res.scalars().first()
        if not sess:
            sess = ConversationSession(
                session_id=sess_uid,
                brand_id=b_id,
                customer_id=cust_1.id,
                session_type="LIVE_CALL",
                vehicle_id=v_id,
                summary=f"Inquired about {b_name} {v_name} features, specifications, and test drive booking."
            )
            db.add(sess)
            await db.flush()

            turn_1 = InteractionLog(
                brand_id=b_id,
                session_id=sess.id,
                customer_id=cust_1.id,
                channel="VOICE_LIVE",
                speaker="customer",
                message=f"Namaste! Main {b_name} {v_name} ke bare mein janna chahta hoon. Iske key features kya hain?",
                extracted_intent="EXPLORE_VEHICLE",
                tool_triggered="switch_vehicle_showroom"
            )
            turn_2 = InteractionLog(
                brand_id=b_id,
                session_id=sess.id,
                customer_id=cust_1.id,
                channel="VOICE_LIVE",
                speaker="ai",
                message=f"Namaste {cust_1.name} ji! {b_name} {v_name} ek outstanding vehicle hai. Isme {vehicle.engine_specs or 'powerful refinement'} aur {vehicle.usp or 'advanced comfort & safety'} milta hai. Price range lagbhag {vehicle.price_range or 'competitive'} hai. Kya aap iska doorstep test drive experience karna chahenge?",
                extracted_intent="EXPLAIN_FEATURES",
                tool_triggered=None
            )
            turn_3 = InteractionLog(
                brand_id=b_id,
                session_id=sess.id,
                customer_id=cust_1.id,
                channel="VOICE_LIVE",
                speaker="customer",
                message=f"Haan bilkul, kal subah 11 baje test drive book kar dijiye.",
                extracted_intent="BOOK_TEST_DRIVE",
                tool_triggered="book_test_drive"
            )
            turn_4 = InteractionLog(
                brand_id=b_id,
                session_id=sess.id,
                customer_id=cust_1.id,
                channel="VOICE_LIVE",
                speaker="ai",
                message=f"Bohot badhiya! Aapka test drive book kar diya gaya hai. Reference: {ref_completed}. Hamare sales consultant {advisor_1} gaadi leke aapke doorstep par pahunchenge.",
                extracted_intent="CONFIRM_BOOKING",
                tool_triggered=None
            )
            db.add_all([turn_1, turn_2, turn_3, turn_4])

        # 4. Create Booking 1: TestRide_Completed
        booking_1 = TestDriveBooking(
            booking_reference=ref_completed,
            brand_id=b_id,
            customer_id=cust_1.id,
            vehicle_id=v_id,
            variant=variant_1,
            color="Metallic Titanium",
            dealership_id=dealer_id_1,
            dealership_name=dealer_name_1,
            sales_advisor_name=advisor_1,
            booking_type="HOME_DOORSTEP",
            delivery_address=f"Customer Residence, {cust_1.city}",
            scheduled_date="Yesterday",
            scheduled_time_slot="11:00 AM",
            status="TestRide_Completed",
            notes=f"Test drive completed for {b_name} {v_name} ({variant_1}). Highly impressed by performance and ride quality.",
            advisor_checklist=[
                f"Demonstrated {v_name} {variant_1} features and powertrain",
                f"Customer loved cabin quietness and responsive handling",
                f"Discussed 12-day priority allocation and special financing"
            ]
        )
        db.add(booking_1)
        await db.flush()

        # 5. Create Booking 2: CONFIRMED Upcoming Lead for Tomorrow
        booking_2 = TestDriveBooking(
            booking_reference=ref_upcoming,
            brand_id=b_id,
            customer_id=cust_2.id,
            vehicle_id=v_id,
            variant=variant_2,
            color="Deep Pearl White",
            dealership_id=dealer_id_2,
            dealership_name=dealer_name_2,
            sales_advisor_name=advisor_2,
            booking_type="HOME_DOORSTEP",
            delivery_address=f"Customer Residence, {cust_2.city}",
            scheduled_date="Tomorrow",
            scheduled_time_slot="03:00 PM",
            status="CONFIRMED",
            notes=f"Doorstep test drive booked for {b_name} {v_name} ({variant_2}). Customer evaluating trade-in and financing.",
            advisor_checklist=[
                f"Evaluate customer's current vehicle for exchange bonus",
                f"Highlight {v_name} {variant_2} safety and technology features",
                f"Provide on-road quote with zero-dep insurance package"
            ]
        )
        db.add(booking_2)
        await db.flush()

        # 6. Create TestRideRecording for Booking 1
        tr_sess_id = f"TR-2026-{b_code}-{v_slug}-01"
        highlights = vehicle.key_highlights if vehicle.key_highlights and len(vehicle.key_highlights) > 0 else [
            f"{v_name} Dynamic Handling & Suspension",
            f"Powertrain Acceleration ({vehicle.engine_specs or 'Refined Engine'})",
            f"Premium Cabin Ergonomics & Infotainment"
        ]
        loved_fts = highlights[:3]

        tr_rec = TestRideRecording(
            session_id=tr_sess_id,
            brand_id=b_id,
            customer_id=cust_1.id,
            booking_id=booking_1.id,
            booking_reference=ref_completed,
            vehicle_id=v_id,
            vehicle_name=f"{b_name} {v_name} {variant_1}",
            sales_advisor_name=advisor_1,
            duration_seconds=198,
            file_size_bytes=1524000,
            audio_format="audio/webm",
            gcs_bucket=f"{b_id}-sales-recordings",
            gcs_object_path=f"test_rides/tr_{b_id}_{v_slug}.webm",
            gcs_uri=f"gs://{b_id}-sales-recordings/test_rides/tr_{b_id}_{v_slug}.webm",
            transcript=f"""[00:05] {advisor_1.split(' ')[0]}: Welcome Mr. {cust_1.name.split(' ')[-1]}! Let's start the drive of the new {b_name} {v_name} {variant_1}.
[00:18] {cust_1.name}: Wow, the cabin insulation is impressive. The steering feel is very light and precise.
[00:42] {advisor_1.split(' ')[0]}: Notice how the suspension handles the rough patch here. The ride quality remains perfectly composed.
[01:12] {cust_1.name}: Absolutely. Acceleration is very linear. What is the current factory waiting period for this variant?
[01:35] {advisor_1.split(' ')[0]}: Usually factory dispatch takes 6 to 8 weeks, but we can verify our priority showroom allocation today.
[02:05] {cust_1.name}: That would be ideal. Please check if we can fast-track the delivery and share the financing offer.""",
            customer_sentiment_score=0.94,
            purchase_intent_score=0.95,
            loved_features=loved_fts,
            objections_raised=[f"Delivery waiting timeline for {v_name} (6-8 weeks)", "Evaluation of trade-in bonus"],
            advisor_pitch_score=9.1,
            advisor_coaching_feedback=f"Clear, confident explanation of {v_name} comfort, safety features, and road presence.",
            recommended_action=f"Follow up via outbound call offering fast-track 12-day allocation for {v_name} with pre-approved financing.",
            status="ANALYZED"
        )
        db.add(tr_rec)
        await db.flush()

        # 7. Create OutboundCallLog for Booking 1
        call_ref = f"CALL-{b_code}-{v_slug}-9901"
        call_log = OutboundCallLog(
            call_reference=call_ref,
            brand_id=b_id,
            customer_id=cust_1.id,
            test_ride_id=tr_rec.id,
            agent_name=f"{b_name} AI ({agent_name})",
            phone_number=phone_1,
            call_status="COMPLETED",
            call_duration_seconds=105,
            transcript=f"""[00:02] {agent_name}: "Namaste {cust_1.name} ji! Main {b_name} se {agent_name} baat kar rahi hoon. Aapka {v_name} ka test drive kaisa raha?"
[00:16] {cust_1.name}: "Namaste! Bohot accha experience raha. Gaadi ka suspension aur cabin comfort bohot pasand aaya."
[00:28] {agent_name}: "Bohot khoob sir! Hamare sales advisor ne note kiya tha ki aap delivery timeline ke baare mein pooch rahe the. We have locked a priority allocation for you in just 12 days!"
[00:46] {cust_1.name}: "That is great news. What about the financing terms?"
[00:56] {agent_name}: "Aapke liye pre-approved loan at 8.15% APR ready hai with zero foreclosure charges."
[01:08] {cust_1.name}: "Perfect! Please proceed with the booking and send over digital KYC."
[01:15] {agent_name}: "Allocation successfully locked! Digital financing link SMS kar di gayi hai. Thank you for choosing {b_name}!" """,
            objection_resolution_status=f"100% RESOLVED (12-Day Priority Allocation Locked for {v_name} + 8.15% APR financing approved)",
            customer_sentiment="VERY_POSITIVE",
            customer_decision="LOCKED_FAST_ALLOCATION",
            locked_vehicle_variant=f"{v_name} {variant_1}",
            locked_allocation_days=12,
            next_step="DIGITAL_FINANCING_KYC"
        )
        db.add(call_log)

        await db.commit()
        logger.info(f"Successfully auto-seeded complete dataset for vehicle: {v_name} ({v_id}) under brand {b_id}")
        return {
            "vehicle_id": v_id,
            "vehicle_name": v_name,
            "status": "seeded",
            "booking_completed": ref_completed,
            "booking_upcoming": ref_upcoming,
            "customer_completed": cust_1.name,
            "customer_upcoming": cust_2.name,
            "recording_session": tr_sess_id,
            "outbound_call": call_ref
        }

    @classmethod
    async def ensure_dealerships_for_brand(cls, db: AsyncSession, brand_or_id: Any) -> List[Dealership]:
        """
        Ensures at least 2 representative dealerships exist in the database for the given brand.
        """
        if isinstance(brand_or_id, str):
            b_id = brand_or_id.lower()
            b_name = b_id.title()
        else:
            b_id = brand_or_id.id.lower()
            b_name = brand_or_id.name

        stmt = select(Dealership).where(Dealership.brand_id == b_id)
        res = await db.execute(stmt)
        existing = res.scalars().all()
        if existing and len(existing) >= 2:
            return list(existing)

        created = list(existing)
        if not isinstance(brand_or_id, str) and getattr(brand_or_id, "dealerships", None):
            for d_item in brand_or_id.dealerships:
                d_id = getattr(d_item, "id", None) or f"{b_id}_{getattr(d_item, 'city', 'mumbai').lower()}"
                stmt_d = select(Dealership).where(Dealership.id == d_id)
                r = await db.execute(stmt_d)
                if not r.scalars().first():
                    d_row = Dealership(
                        id=d_id,
                        brand_id=b_id,
                        name=getattr(d_item, "name", f"{b_name} Experience Center"),
                        city=getattr(d_item, "city", "Mumbai"),
                        state="Maharashtra",
                        area="Flagship Auto Hub",
                        address=getattr(d_item, "address", "Signature Flagship Complex, Mumbai"),
                        pin_code="400018",
                        phone=getattr(d_item, "phone", "+91 22 6600 8800"),
                        email=f"contact@{b_id}-experience.in",
                        rating=getattr(d_item, "rating", 4.9),
                        available_advisors=getattr(d_item, "available_advisors", None) or [f"Rajesh Varma ({b_name} Specialist)", "Ananya Sen"],
                        is_active=True
                    )
                    db.add(d_row)
                    created.append(d_row)

        if len(created) < 2:
            d1_id = f"{b_id}_worli_flagship"
            stmt_1 = select(Dealership).where(Dealership.id == d1_id)
            r1 = await db.execute(stmt_1)
            if not r1.scalars().first():
                d1 = Dealership(
                    id=d1_id,
                    brand_id=b_id,
                    name=f"{b_name} Flagship Experience Center - Worli",
                    city="Mumbai",
                    state="Maharashtra",
                    area="Worli Sea Face",
                    address=f"Plot 18, Dr. Annie Besant Road, Worli, Mumbai",
                    pin_code="400018",
                    phone="+91 22 6158 8800",
                    email=f"worli@{b_id}-experience.in",
                    rating=4.9,
                    available_advisors=[f"Rohit Khanna ({b_name} Genius)", f"Ananya Sen (Luxury Consultant)"],
                    is_active=True
                )
                db.add(d1)
                created.append(d1)

            d2_id = f"{b_id}_andheri_prime"
            stmt_2 = select(Dealership).where(Dealership.id == d2_id)
            r2 = await db.execute(stmt_2)
            if not r2.scalars().first():
                d2 = Dealership(
                    id=d2_id,
                    brand_id=b_id,
                    name=f"{b_name} Prime Motors - Andheri West",
                    city="Mumbai",
                    state="Maharashtra",
                    area="Andheri West",
                    address=f"Prime Auto Boulevard, New Link Road, Andheri West, Mumbai",
                    pin_code="400053",
                    phone="+91 22 6677 8800",
                    email=f"andheri@{b_id}-motors.in",
                    rating=4.8,
                    available_advisors=[f"Karan Johar ({b_name} EV Specialist)", "Simran Bajaj"],
                    is_active=True
                )
                db.add(d2)
                created.append(d2)

        await db.flush()
        return created
