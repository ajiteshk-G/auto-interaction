import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.future import select
from app.database import AsyncSessionLocal
from app.models.dealership import Dealership
from app.models.customer import Customer
from app.models.booking import TestDriveBooking
from app.models.sales_ride import TestRideRecording, OutboundCallLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_multitenant_brands")

MULTI_BRAND_DEALERSHIPS = [
    # BMW DEALERSHIPS
    {
        "id": "bmw_infinity_worli",
        "brand_id": "bmw",
        "name": "BMW Infinity Cars - Worli",
        "city": "Mumbai",
        "state": "Maharashtra",
        "area": "Worli Sea Face",
        "address": "Plot 10, Dr. Annie Besant Rd, Worli Sea Face, Mumbai",
        "pin_code": "400018",
        "phone": "+91 22 6158 6000",
        "email": "worli@bmw-infinitycars.in",
        "map_url": "https://maps.google.com/?q=BMW+Infinity+Cars+Worli+Mumbai",
        "rating": 4.9,
        "available_advisors": ["Rohit Khanna (BMW M Genius)", "Ananya Sen (Luxury Specialist)"]
    },
    {
        "id": "bmw_navnit_andheri",
        "brand_id": "bmw",
        "name": "BMW Navnit Motors - Andheri",
        "city": "Mumbai",
        "state": "Maharashtra",
        "area": "Andheri West",
        "address": "Navnit House, New Link Road, Andheri West, Mumbai",
        "pin_code": "400053",
        "phone": "+91 22 6677 7777",
        "email": "andheri@bmw-navnitmotors.in",
        "map_url": "https://maps.google.com/?q=BMW+Navnit+Motors+Andheri+Mumbai",
        "rating": 4.8,
        "available_advisors": ["Karan Johar (EV Specialist)", "Simran Bajaj"]
    },
    {
        "id": "bmw_deutsche_delhi",
        "brand_id": "bmw",
        "name": "BMW Deutsche Motoren - Connaught Place",
        "city": "Delhi",
        "state": "Delhi",
        "area": "Connaught Place",
        "address": "Barakhamba Road, Connaught Place, New Delhi",
        "pin_code": "110001",
        "phone": "+91 11 4330 0000",
        "email": "delhi@deutschemotoren.in",
        "map_url": "https://maps.google.com/?q=BMW+Deutsche+Motoren+Delhi",
        "rating": 4.9,
        "available_advisors": ["Aditya Roy", "Meera Rajput"]
    },

    # HYUNDAI DEALERSHIPS
    {
        "id": "hyundai_modi_goregaon",
        "brand_id": "hyundai",
        "name": "Modi Hyundai - Goregaon West",
        "city": "Mumbai",
        "state": "Maharashtra",
        "area": "Goregaon West",
        "address": "Near Inorbit Mall, Link Road, Goregaon West, Mumbai",
        "pin_code": "400104",
        "phone": "+91 22 6789 1234",
        "email": "goregaon@modihyundai.com",
        "map_url": "https://maps.google.com/?q=Modi+Hyundai+Goregaon+Mumbai",
        "rating": 4.8,
        "available_advisors": ["Amit Saxena (EV Specialist)", "Roshni Patel"]
    },
    {
        "id": "hyundai_sai_malad",
        "brand_id": "hyundai",
        "name": "Sai Auto Hyundai - Malad West",
        "city": "Mumbai",
        "state": "Maharashtra",
        "area": "Malad West",
        "address": "Chincholi Bunder Road, Off SV Road, Malad West, Mumbai",
        "pin_code": "400064",
        "phone": "+91 22 2888 5555",
        "email": "malad@saihyundai.com",
        "map_url": "https://maps.google.com/?q=Sai+Auto+Hyundai+Malad+Mumbai",
        "rating": 4.7,
        "available_advisors": ["Sunil Nair", "Deepika Rao"]
    },

    # MARUTI SUZUKI DEALERSHIPS
    {
        "id": "maruti_nexa_andheri",
        "brand_id": "maruti_suzuki",
        "name": "Nexa Andheri West (Shivaji Nagar)",
        "city": "Mumbai",
        "state": "Maharashtra",
        "area": "Andheri West",
        "address": "Plot 42, JP Road, Near Metro Station, Andheri West, Mumbai",
        "pin_code": "400058",
        "phone": "+91 22 2620 4444",
        "email": "andheri@nexadealer.com",
        "map_url": "https://maps.google.com/?q=Nexa+Andheri+West+Mumbai",
        "rating": 4.8,
        "available_advisors": ["Varun Kapoor (Senior RM)", "Swati Deshmukh"]
    },
    {
        "id": "maruti_arena_bandra",
        "brand_id": "maruti_suzuki",
        "name": "Maruti Suzuki Arena - Bandra East",
        "city": "Mumbai",
        "state": "Maharashtra",
        "area": "Bandra East",
        "address": "BKC Connector Rd, Kalanagar, Bandra East, Mumbai",
        "pin_code": "400051",
        "phone": "+91 22 2659 8888",
        "email": "bandra@arenadealer.com",
        "map_url": "https://maps.google.com/?q=Maruti+Arena+Bandra+Mumbai",
        "rating": 4.7,
        "available_advisors": ["Prakash Jadhav", "Anjali Mehta"]
    }
]

DEFAULT_CUSTOMERS = [
    # BMW DEFAULT CUSTOMER
    {
        "customer_id": "CUST-BMW-98201",
        "brand_id": "bmw",
        "name": "Vikram Malhotra",
        "phone": "+919820199001",
        "email": "vikram.malhotra@luxurycorp.com",
        "city": "Mumbai",
        "preferred_language": "English",
        "current_phase": "PRE_SALES",
        "interested_vehicle_id": "bmw_x5",
        "interested_variant": "xDrive40i M Sport",
        "budget_range": "₹95 Lakh - ₹1.10 Crore",
        "loan_preapproval_amount": 7500000,
        "loan_interest_rate": "7.90%",
        "loan_status": "PRE_APPROVED",
        "owned_vin": "WBA31AY0098201BMW",
        "owned_vehicle_name": "BMW 3 Series 330Li M Sport",
        "registration_number": "MH 01 DX 3300",
        "odometer_km": 14200,
        "insurance_policy_number": "POL-BAJAJ-BMW-2026-9901",
        "insurance_type": "BMW Secure Advanced Comprehensive",
        "pan_number": "BAPVM9901L",
        "aadhaar_masked": "XXXX-XXXX-9901",
        "kyc_status": "VERIFIED",
        "advisor_checklist": [
            "Demonstrate BMW Curved Display & iDrive 8.5 with QuickSelect",
            "Showcase Adaptive 2-Axle Air Suspension ride comfort",
            "Test drive on Sea Link for TwinPower Turbo acceleration",
            "Explain BMW Financial Services 7.9% APR & 3-year Service Inclusive"
        ]
    },
    # HYUNDAI DEFAULT CUSTOMER
    {
        "customer_id": "CUST-HYU-98201",
        "brand_id": "hyundai",
        "name": "Arjun Reddy",
        "phone": "+919820199002",
        "email": "arjun.reddy@techsol.in",
        "city": "Mumbai",
        "preferred_language": "Hinglish",
        "current_phase": "PRE_SALES",
        "interested_vehicle_id": "creta",
        "interested_variant": "SX (O) 1.5 Turbo Petrol DCT",
        "budget_range": "₹18 Lakh - ₹22 Lakh",
        "loan_preapproval_amount": 1650000,
        "loan_interest_rate": "8.25%",
        "loan_status": "PRE_APPROVED",
        "owned_vin": "MAL1HYU2026CRETA01",
        "owned_vehicle_name": "Hyundai Venue SX 1.0 Turbo",
        "registration_number": "MH 02 ER 8820",
        "odometer_km": 21000,
        "insurance_policy_number": "POL-HDFC-HYU-2026-5501",
        "insurance_type": "Zero Depreciation Return-to-Invoice",
        "pan_number": "ARJPR4401P",
        "aadhaar_masked": "XXXX-XXXX-4401",
        "kyc_status": "VERIFIED",
        "advisor_checklist": [
            "Demonstrate Hyundai SmartSense Level 2 ADAS (Forward Collision & Lane Keep)",
            "Experience Voice-Enabled Panoramic Sunroof in Hinglish",
            "Explain Hyundai Bluelink 70+ Connected Car features",
            "Discuss Hyundai Shield of Trust 5-Year Maintenance Packages"
        ]
    },
    # MARUTI SUZUKI DEFAULT CUSTOMER
    {
        "customer_id": "CUST-MAR-98201",
        "brand_id": "maruti_suzuki",
        "name": "Manish Patel",
        "phone": "+919820199003",
        "email": "manish.patel@patelauto.com",
        "city": "Mumbai",
        "preferred_language": "Hinglish",
        "current_phase": "PRE_SALES",
        "interested_vehicle_id": "grand_vitara",
        "interested_variant": "Alpha+ Intelligent Electric Hybrid e-CVT",
        "budget_range": "₹16 Lakh - ₹21 Lakh",
        "loan_preapproval_amount": 1700000,
        "loan_interest_rate": "8.10%",
        "loan_status": "PRE_APPROVED",
        "owned_vin": "MAR1MSIL2026GV001",
        "owned_vehicle_name": "Maruti Suzuki Baleno Alpha",
        "registration_number": "MH 03 BT 5511",
        "odometer_km": 34000,
        "insurance_policy_number": "POL-MARUTI-INS-2026-3301",
        "insurance_type": "Maruti Suzuki Genuine Insurance Zero-Dep",
        "pan_number": "MPTMP1101M",
        "aadhaar_masked": "XXXX-XXXX-1101",
        "kyc_status": "VERIFIED",
        "advisor_checklist": [
            "Demonstrate EV mode pure electric city silent driving",
            "Showcase 27.97 km/l class-leading fuel economy",
            "Demonstrate Head-Up Display (HUD) and 360 View Camera",
            "Review Maruti Suzuki Smart Finance instant 100% on-road funding"
        ]
    }
]

MULTI_BRAND_BOOKINGS = [
    # BMW LEADS / BOOKINGS
    {
        "booking_reference": "BK-BMW-2026-101",
        "brand_id": "bmw",
        "cust_name": "Rhea Kapoor",
        "cust_phone": "+919819650001",
        "vehicle_id": "bmw_3series",
        "variant": "330Li M Sport Gran Limousine",
        "dealership_id": "bmw_infinity_worli",
        "dealership_name": "BMW Infinity Cars - Worli",
        "advisor": "Rohit Khanna (BMW M Genius)",
        "date": "Tomorrow",
        "slot": "11:00 AM",
        "notes": "Interested in BMW Curved Display, rear seat comfort limousine legroom, and M Sport dynamic dampers."
    },
    {
        "booking_reference": "BK-BMW-2026-102",
        "brand_id": "bmw",
        "cust_name": "Siddharth Singhania",
        "cust_phone": "+919820250002",
        "vehicle_id": "bmw_ix",
        "variant": "xDrive40 All-Electric SUV",
        "dealership_id": "bmw_navnit_andheri",
        "dealership_name": "BMW Navnit Motors - Andheri",
        "advisor": "Karan Johar (EV Specialist)",
        "date": "Tomorrow",
        "slot": "03:00 PM",
        "notes": "Interested in BMW Wallbox home charging installation, Shy Tech interior, and 425km WLTP range."
    },
    {
        "booking_reference": "BK-BMW-2026-103",
        "brand_id": "bmw",
        "cust_name": "Ananya Roy",
        "cust_phone": "+919820350003",
        "vehicle_id": "bmw_x1",
        "variant": "sDrive18d M Sport",
        "dealership_id": "bmw_infinity_worli",
        "dealership_name": "BMW Infinity Cars - Worli",
        "advisor": "Ananya Sen (Luxury Specialist)",
        "date": "Day After Tomorrow",
        "slot": "05:00 PM",
        "notes": "First luxury SUV purchase. Wants to evaluate boot space and Harman Kardon HiFi audio system."
    },

    # HYUNDAI LEADS / BOOKINGS
    {
        "booking_reference": "BK-HYU-2026-201",
        "brand_id": "hyundai",
        "cust_name": "Neha Sen",
        "cust_phone": "+919819650004",
        "vehicle_id": "ioniq5",
        "variant": "Long Range RWD 72.6 kWh",
        "dealership_id": "hyundai_modi_goregaon",
        "dealership_name": "Modi Hyundai - Goregaon West",
        "advisor": "Amit Saxena (EV Specialist)",
        "date": "Tomorrow",
        "slot": "10:00 AM",
        "notes": "Evaluating 800V ultra-fast charging (10% to 80% in 18 mins) and Vehicle-to-Load (V2L) capability."
    },
    {
        "booking_reference": "BK-HYU-2026-202",
        "brand_id": "hyundai",
        "cust_name": "Rahul Varma",
        "cust_phone": "+919820250005",
        "vehicle_id": "tucson",
        "variant": "Signature 2.0 CRDi Diesel AWD",
        "dealership_id": "hyundai_sai_malad",
        "dealership_name": "Sai Auto Hyundai - Malad West",
        "advisor": "Sunil Nair",
        "date": "Tomorrow",
        "slot": "04:00 PM",
        "notes": "Wants high-speed highway ride quality and HTRAC All-Wheel Drive demonstration."
    },
    {
        "booking_reference": "BK-HYU-2026-203",
        "brand_id": "hyundai",
        "cust_name": "Sneha Joshi",
        "cust_phone": "+919820350006",
        "vehicle_id": "creta",
        "variant": "SX (O) Knight Edition 1.5 Turbo DCT",
        "dealership_id": "hyundai_modi_goregaon",
        "dealership_name": "Modi Hyundai - Goregaon West",
        "advisor": "Roshni Patel",
        "date": "Day After Tomorrow",
        "slot": "12:00 PM",
        "notes": "Prefers Black styling, ventilated front seats, and Bose premium 8-speaker sound system."
    },

    # MARUTI SUZUKI LEADS / BOOKINGS
    {
        "booking_reference": "BK-MAR-2026-301",
        "brand_id": "maruti_suzuki",
        "cust_name": "Ritu Sharma",
        "cust_phone": "+919819650007",
        "vehicle_id": "brezza",
        "variant": "ZXi+ 1.5 DualJet 6AT",
        "dealership_id": "maruti_arena_bandra",
        "dealership_name": "Maruti Suzuki Arena - Bandra East",
        "advisor": "Prakash Jadhav",
        "date": "Tomorrow",
        "slot": "11:30 AM",
        "notes": "Testing city maneuverability, electric sunroof, 360 view camera, and paddle shifters."
    },
    {
        "booking_reference": "BK-MAR-2026-302",
        "brand_id": "maruti_suzuki",
        "cust_name": "Kunal Gupta",
        "cust_phone": "+919820250008",
        "vehicle_id": "fronx",
        "variant": "Alpha 1.0L Boosterjet Turbo 6AT",
        "dealership_id": "maruti_nexa_andheri",
        "dealership_name": "Nexa Andheri West (Shivaji Nagar)",
        "advisor": "Varun Kapoor (Senior RM)",
        "date": "Tomorrow",
        "slot": "02:00 PM",
        "notes": "Interested in turbocharged acceleration, Wireless SmartPlay Pro+, and sporty coupe silhouette."
    },
    {
        "booking_reference": "BK-MAR-2026-303",
        "brand_id": "maruti_suzuki",
        "cust_name": "Pooja Joshi",
        "cust_phone": "+919820350009",
        "vehicle_id": "grand_vitara",
        "variant": "Alpha+ Intelligent Electric Hybrid",
        "dealership_id": "maruti_nexa_andheri",
        "dealership_name": "Nexa Andheri West (Shivaji Nagar)",
        "advisor": "Swati Deshmukh",
        "date": "Day After Tomorrow",
        "slot": "04:30 PM",
        "notes": "Family test drive focusing on 27.97 km/l fuel savings and Panoramic Sliding Skyroof."
    }
]

async def seed_multitenant_brands():
    logger.info("Seeding multi-tenant brand data for BMW, Hyundai, and Maruti Suzuki...")
    async with AsyncSessionLocal() as db:
        # 1. Seed Dealerships
        d_res = await db.execute(select(Dealership))
        existing_dealers = {d.id: d for d in d_res.scalars().all()}

        for d_item in MULTI_BRAND_DEALERSHIPS:
            if d_item["id"] not in existing_dealers:
                d = Dealership(
                    id=d_item["id"],
                    brand_id=d_item["brand_id"],
                    name=d_item["name"],
                    city=d_item["city"],
                    state=d_item["state"],
                    area=d_item["area"],
                    address=d_item["address"],
                    pin_code=d_item["pin_code"],
                    phone=d_item["phone"],
                    email=d_item["email"],
                    map_url=d_item["map_url"],
                    rating=d_item["rating"],
                    available_advisors=d_item["available_advisors"],
                    is_active=True
                )
                db.add(d)
                logger.info(f"Added dealership: {d.name} ({d.brand_id})")
            else:
                existing = existing_dealers[d_item["id"]]
                existing.brand_id = d_item["brand_id"]
                existing.name = d_item["name"]
                existing.city = d_item["city"]
                existing.state = d_item["state"]
                existing.area = d_item["area"]
                existing.address = d_item["address"]
                existing.pin_code = d_item["pin_code"]
                existing.phone = d_item["phone"]
                existing.email = d_item["email"]
                existing.rating = d_item["rating"]
                existing.available_advisors = d_item["available_advisors"]

        await db.commit()

        # 2. Seed Default Brand Customers
        c_res = await db.execute(select(Customer))
        existing_customers = {f"{c.phone}_{c.brand_id}": c for c in c_res.scalars().all()}

        created_customers = {}
        for c_data in DEFAULT_CUSTOMERS:
            key = f"{c_data['phone']}_{c_data['brand_id']}"
            if key not in existing_customers:
                cust = Customer(
                    customer_id=c_data["customer_id"],
                    brand_id=c_data["brand_id"],
                    name=c_data["name"],
                    phone=c_data["phone"],
                    email=c_data["email"],
                    city=c_data["city"],
                    preferred_language=c_data["preferred_language"],
                    current_phase=c_data["current_phase"],
                    interested_vehicle_id=c_data["interested_vehicle_id"],
                    interested_variant=c_data["interested_variant"],
                    budget_range=c_data["budget_range"],
                    loan_preapproval_amount=c_data["loan_preapproval_amount"],
                    loan_interest_rate=c_data["loan_interest_rate"],
                    loan_status=c_data["loan_status"],
                    owned_vin=c_data["owned_vin"],
                    owned_vehicle_name=c_data["owned_vehicle_name"],
                    registration_number=c_data["registration_number"],
                    odometer_km=c_data["odometer_km"],
                    insurance_policy_number=c_data["insurance_policy_number"],
                    insurance_type=c_data["insurance_type"],
                    pan_number=c_data["pan_number"],
                    aadhaar_masked=c_data["aadhaar_masked"],
                    kyc_status=c_data["kyc_status"],
                    advisor_checklist=c_data["advisor_checklist"]
                )
                db.add(cust)
                await db.flush()
                created_customers[key] = cust
                logger.info(f"Added default customer: {cust.name} ({cust.brand_id})")
            else:
                created_customers[key] = existing_customers[key]

        await db.commit()

        # 3. Seed Sample Leads and Test Drive Bookings
        b_res = await db.execute(select(TestDriveBooking))
        existing_bookings = {b.booking_reference: b for b in b_res.scalars().all()}

        for b_data in MULTI_BRAND_BOOKINGS:
            if b_data["booking_reference"] not in existing_bookings:
                # Find or create lead customer
                lead_phone = b_data["cust_phone"]
                lead_key = f"{lead_phone}_{b_data['brand_id']}"
                cust = existing_customers.get(lead_key) or created_customers.get(lead_key)
                if not cust:
                    cust = Customer(
                        customer_id=f"CUST-{lead_phone[-10:]}",
                        brand_id=b_data["brand_id"],
                        name=b_data["cust_name"],
                        phone=lead_phone,
                        email=f"{b_data['cust_name'].lower().replace(' ', '.')}@example.com",
                        city="Mumbai",
                        current_phase="SALES_TEST_RIDE",
                        interested_vehicle_id=b_data["vehicle_id"],
                        interested_variant=b_data["variant"]
                    )
                    db.add(cust)
                    await db.flush()
                    created_customers[lead_key] = cust

                booking = TestDriveBooking(
                    booking_reference=b_data["booking_reference"],
                    brand_id=b_data["brand_id"],
                    customer_id=cust.id,
                    vehicle_id=b_data["vehicle_id"],
                    variant=b_data["variant"],
                    color="Official Edition",
                    dealership_id=b_data["dealership_id"],
                    dealership_name=b_data["dealership_name"],
                    sales_advisor_name=b_data["advisor"],
                    booking_type="HOME_DOORSTEP",
                    delivery_address="Customer Residence, Mumbai",
                    scheduled_date=b_data["date"],
                    scheduled_time_slot=b_data["slot"],
                    status="CONFIRMED",
                    notes=b_data["notes"],
                    advisor_checklist=[b_data["notes"]]
                )
                db.add(booking)
                logger.info(f"Added booking: {booking.booking_reference} for {b_data['cust_name']} ({b_data['brand_id']})")

        await db.commit()

        # 4. Seed Test Ride Recordings and Outbound Calls for BMW
        tr_res = await db.execute(select(TestRideRecording).where(TestRideRecording.session_id == "TR-2026-BMW-X5-01"))
        if not tr_res.scalars().first():
            bmw_cust = created_customers.get("+919820199001_bmw")
            if bmw_cust:
                rec = TestRideRecording(
                    session_id="TR-2026-BMW-X5-01",
                    brand_id="bmw",
                    customer_id=bmw_cust.id,
                    booking_reference="BK-BMW-2026-101",
                    vehicle_id="bmw_x5",
                    vehicle_name="BMW X5 xDrive40i M Sport",
                    sales_advisor_name="Rohit Khanna (BMW Infinity Cars)",
                    duration_seconds=210,
                    file_size_bytes=1654000,
                    audio_format="audio/webm",
                    gcs_bucket="bmw-sales-recordings",
                    gcs_object_path="test_rides/tr_bmw_vikram_2026.webm",
                    gcs_uri="gs://bmw-sales-recordings/test_rides/tr_bmw_vikram_2026.webm",
                    transcript="""[00:05] Rohit Khanna: Welcome to the new BMW X5 xDrive40i M Sport, Mr. Malhotra. Let's start the 3.0-litre inline six engine.
[00:18] Vikram Malhotra: Wow, the engine note is silky smooth. And this curved display looks incredible.
[00:45] Rohit Khanna: Notice the adaptive 2-axle air suspension as we hit the uneven tarmac near Worli Sea Face. It glides over bumps.
[01:15] Vikram Malhotra: The cabin insulation is remarkable. How long is the delivery waiting period for Tanzanite Blue?
[01:35] Rohit Khanna: For Tanzanite Blue, typical factory allocation takes 6 to 8 weeks, but we can check priority dealer pipeline today.
[02:10] Vikram Malhotra: That sounds great. Let's proceed with the loan pre-approval and lock the allocation.""",
                    customer_sentiment_score=0.95,
                    purchase_intent_score=0.96,
                    loved_features=["Inline-6 TwinPower Turbo Smoothness", "Adaptive 2-Axle Air Suspension", "BMW Curved Display with iDrive 8.5"],
                    objections_raised=["Waiting period for Tanzanite Blue metallic (6-8 weeks)"],
                    advisor_pitch_score=9.2,
                    advisor_coaching_feedback="Excellent explanation of BMW xDrive power distribution and air suspension comfort.",
                    recommended_action="Follow up via outbound call offering fast-track 10-day priority dispatch with BMW Financial Services 7.9% APR.",
                    status="ANALYZED"
                )
                db.add(rec)
                await db.flush()

                # Outbound Call Log for BMW
                call = OutboundCallLog(
                    call_reference="CALL-BMW-2026-9901",
                    brand_id="bmw",
                    customer_id=bmw_cust.id,
                    test_ride_id=rec.id,
                    agent_name="Kabir AI (BMW Client Experience Executive)",
                    phone_number="+91 98201 99001",
                    call_status="COMPLETED",
                    call_duration_seconds=115,
                    transcript="""[00:02] Kabir AI: "Good afternoon Mr. Vikram Malhotra! I am Kabir from BMW Client Experience. How was your test drive of the BMW X5 xDrive40i this morning with Rohit?"
[00:16] Vikram Malhotra: "Hello Kabir! The drive was magnificent. Loved the air suspension and smooth power."
[00:28] Kabir AI: "Splendid! Rohit noted you were interested in the Tanzanite Blue metallic. Great news—we have secured an executive priority allocation arriving in just 10 days instead of 8 weeks!"
[00:45] Vikram Malhotra: "That is fantastic news. What about the financing terms?"
[00:55] Kabir AI: "BMW Financial Services has pre-approved your application for ₹75 Lakhs at our special promotional rate of 7.9% APR."
[01:10] Vikram Malhotra: "Let's lock that immediately. Please send over the digital KYC link."
[01:15] Kabir AI: "Allocation locked and digital documents sent. Welcome to the BMW family, Mr. Malhotra!" """,
                    objection_resolution_status="100% RESOLVED (Factory Allocation expedited to 10 days + 7.9% APR locked)",
                    customer_sentiment="VERY_POSITIVE",
                    customer_decision="LOCKED_FAST_ALLOCATION_PROCEED_TO_FINANCING",
                    locked_vehicle_variant="BMW X5 xDrive40i M Sport (Tanzanite Blue)",
                    locked_allocation_days=10,
                    next_step="DIGITAL_FINANCING_KYC"
                )
                db.add(call)
                logger.info("Added BMW Test Ride Recording and Outbound Call Log.")

        await db.commit()
    logger.info("Multi-tenant brand seed completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed_multitenant_brands())
