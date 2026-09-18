import uuid
import re
import json
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from app.models.customer import Customer, ConversationSession, InteractionLog
from app.services.cache_service import cache

def clean_phone(phone_str: str) -> str:
    """Normalizes phone numbers to standard E.164 / +91 format for consistent identification."""
    raw = re.sub(r"[\s\-\(\)\.]", "", str(phone_str or "").strip())
    if raw.startswith("+91") and len(raw) == 13:
        return raw
    if raw.startswith("91") and len(raw) == 12:
        return "+" + raw
    if raw.startswith("0") and len(raw) == 11:
        return "+91" + raw[1:]
    if len(raw) == 10:
        return "+91" + raw
    if not raw.startswith("+") and len(raw) > 0:
        return "+" + raw
    return raw

def clean_name(name_str: Optional[str]) -> str:
    """Normalizes customer name to clean Title Case for deterministic Name + Phone identification."""
    if not name_str:
        return ""
    cleaned = " ".join(str(name_str).strip().split())
    if cleaned.lower() in ("valued customer", "valued guest", "guest", "there", "customer"):
        return ""
    return cleaned.title()

def make_customer_id(name: str, phone: str, brand_id: str) -> str:
    """Generates a deterministic customer_id combining Brand + Normalized Name + Phone."""
    b_prefix = (brand_id or "mah").upper()[:3]
    norm_n = clean_name(name)
    name_slug = re.sub(r"[^A-Z0-9]", "", norm_n.upper())[:12] or "USER"
    digits = re.sub(r"\D", "", str(phone or ""))
    phone_slug = digits[-10:] if len(digits) >= 10 else (digits or uuid.uuid4().hex[:6].upper())
    return f"CUST-{b_prefix}-{name_slug}-{phone_slug}"

from app.services.brand_service import BrandService

def resolve_brand(brand_id: Optional[str] = None) -> str:
    if brand_id and brand_id.strip():
        return brand_id.strip().lower()
    try:
        active = BrandService.get_active_brand()
        if active and active.id:
            return active.id.lower()
    except Exception:
        pass
    return "mahindra"

VEHICLE_PRICE_MAP = {
    "thar_roxx": ("Mahindra Thar ROXX", "₹12.99 Lakh – ₹22.49 Lakh"),
    "xuv700": ("Mahindra XUV700", "₹13.99 Lakh – ₹26.99 Lakh"),
    "scorpio_n": ("Mahindra Scorpio-N", "₹13.85 Lakh – ₹24.54 Lakh"),
    "xuv_3xo": ("Mahindra XUV 3XO", "₹7.79 Lakh – ₹15.49 Lakh"),
    "be_6": ("Mahindra BE 6", "₹18.90 Lakh – ₹26.90 Lakh"),
    "xev_9e": ("Mahindra XEV 9e", "₹21.90 Lakh – ₹30.50 Lakh"),
    "bolero_neo": ("Mahindra Bolero Neo", "₹9.95 Lakh – ₹12.15 Lakh"),
    "xuv400": ("Mahindra XUV400 EV", "₹15.49 Lakh – ₹19.39 Lakh"),
    "bmw_x5": ("BMW X5", "₹96.00 Lakh – ₹1.09 Crore"),
    "creta": ("Hyundai Creta", "₹11.00 Lakh – ₹20.15 Lakh"),
    "grand_vitara": ("Maruti Suzuki Grand Vitara", "₹10.99 Lakh – ₹20.09 Lakh"),
}

FEATURE_PATTERNS = [
    (r"\b(panoramic|skyroof|sunroof|moonroof)\b", "Panoramic Skyroof / Sunroof"),
    (r"\b(adas|autonomous|lane\s*keep|adaptive\s*cruise|smart\s*pilot|collision)\b", "Level 2 ADAS Suite"),
    (r"\b(4x4|4wd|off[\s-]*road|m_ld|crawl\s*smart|intelliturn|terrain|4xplor)\b", "4x4 Off-Road & Terrain Modes"),
    (r"\b(harman|kardon|dolby|atmos|speaker|music\s*system|sound|audio)\b", "Harman Kardon / Premium 3D Audio"),
    (r"\b(360|camera|blind\s*view|parking\s*sensor|surround\s*view)\b", "360° Surround View Camera"),
    (r"\b(ventilated|cooled\s*seat|leatherette|ergonomic|power\s*seat|rear\s*seat|legroom|comfort|space|boot)\b", "Ventilated Seats & Cabin Comfort"),
    (r"\b(safety|ncap|5[\s-]*star|airbag|esp|disc\s*brake)\b", "5-Star Safety & 6 Airbags"),
    (r"\b(diesel|petrol|mstallion|mhawk|torque|bhp|power|automatic|manual|gearbox|transmission)\b", "Engine Performance & AT/MT Powertrain"),
    (r"\b(mileage|fuel|average|kmpl|range|battery|charging|ev)\b", "Mileage / Driving Range"),
    (r"\b(screen|display|adrenox|cockpit|carplay|android\s*auto|infotainment|digital\s*cluster)\b", "Twin HD Digital Cockpit & AdrenoX"),
    (r"\b(suspension|fsd|ride\s*quality|watts\s*link|handling|damping)\b", "Frequency Selective Damping (FSD) Suspension"),
    (r"\b(emi|loan|finance|down\s*payment|interest\s*rate|on[\s-]*road|price|cost|discount)\b", "On-Road Pricing & EMI Finance"),
]

def extract_conversation_intelligence(
    messages: List[Dict[str, Any]],
    default_vehicle_id: str = "thar_roxx",
    existing_budget: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyzes conversation messages (both Customer and AI) to extract:
    - interested_cars: list of vehicle names discussed
    - primary_vehicle_id: resolved vehicle_id
    - interested_features: list of specific features customer showed interest in
    - budget: extracted budget or price range discussed
    - key_points_summary: human-readable summary of the conversation
    """
    full_text = " ".join([str(m.get("text") or m.get("message") or "") for m in messages if m.get("speaker") != "system"])
    customer_text = " ".join([str(m.get("text") or m.get("message") or "") for m in messages if m.get("speaker") == "customer"])
    combined_lower = full_text.lower()
    cust_lower = customer_text.lower()

    # 1. Detect interested car(s)
    car_patterns = [
        ("thar_roxx", "Mahindra Thar ROXX", r"\b(thar\s*roxx|roxx|thar\s*5[\s-]*door|thar)\b"),
        ("xuv700", "Mahindra XUV700", r"\b(xuv\s*700|xuv700|700)\b"),
        ("scorpio_n", "Mahindra Scorpio-N", r"\b(scorpio[\s-]*n|scorpio)\b"),
        ("xuv_3xo", "Mahindra XUV 3XO", r"\b(xuv\s*3xo|3xo)\b"),
        ("be_6", "Mahindra BE 6", r"\b(be\s*6e?|be6)\b"),
        ("xev_9e", "Mahindra XEV 9e", r"\b(xev\s*9e|xev9e|9e)\b"),
        ("bolero_neo", "Mahindra Bolero Neo", r"\b(bolero\s*neo|bolero)\b"),
        ("xuv400", "Mahindra XUV400 EV", r"\b(xuv\s*400|xuv400)\b"),
        ("bmw_x5", "BMW X5", r"\b(bmw\s*x5|x5)\b"),
        ("creta", "Hyundai Creta", r"\b(creta)\b"),
        ("grand_vitara", "Maruti Suzuki Grand Vitara", r"\b(grand\s*vitara|vitara)\b"),
    ]
    detected_cars: List[Tuple[str, str]] = []
    for vid, vname, pat in car_patterns:
        if re.search(pat, cust_lower, re.IGNORECASE):
            detected_cars.append((vid, vname))
    for vid, vname, pat in car_patterns:
        if re.search(pat, combined_lower, re.IGNORECASE) and all(x[0] != vid for x in detected_cars):
            detected_cars.append((vid, vname))

    if not detected_cars:
        fallback_vid = default_vehicle_id or "thar_roxx"
        fallback_name = VEHICLE_PRICE_MAP.get(fallback_vid, (fallback_vid.replace("_", " ").title(), "₹15 Lakh – ₹25 Lakh"))[0]
        detected_cars.append((fallback_vid, fallback_name))

    primary_vid, primary_vname = detected_cars[0]
    interested_cars = [c[1] for c in detected_cars]

    # 2. Detect interested features
    features: List[str] = []
    for pat, label in FEATURE_PATTERNS:
        if re.search(pat, cust_lower, re.IGNORECASE):
            if label not in features:
                features.append(label)
    for pat, label in FEATURE_PATTERNS:
        if re.search(pat, combined_lower, re.IGNORECASE):
            if label not in features and len(features) < 5:
                features.append(label)
    if not features:
        features = ["SUV Styling & Road Presence", "Cabin Comfort & Infotainment"]

    # 3. Extract budget from dialogue
    budget_str = None
    m_range = re.search(r"(?:₹|rs\.?\s*)?(\d{1,2}(?:\.\d+)?)\s*(?:to|\-|and)\s*(\d{1,2}(?:\.\d+)?)\s*(?:lakh|lakhs|lac|l\b)", cust_lower, re.IGNORECASE)
    if not m_range:
        m_range = re.search(r"(?:₹|rs\.?\s*)?(\d{1,2}(?:\.\d+)?)\s*(?:to|\-|and)\s*(\d{1,2}(?:\.\d+)?)\s*(?:lakh|lakhs|lac|l\b)", combined_lower, re.IGNORECASE)
    if m_range:
        budget_str = f"₹{m_range.group(1)} Lakh – ₹{m_range.group(2)} Lakh"
    else:
        m_single = re.search(r"(?:budget|under|around|upto|up\s*to|within|below|approx|₹|rs\.?)\s*(?:is\s*|of\s*)?(?:₹|rs\.?\s*)?(\d{1,2}(?:\.\d+)?)\s*(?:lakh|lakhs|lac|l\b)", cust_lower, re.IGNORECASE)
        if not m_single:
            m_single = re.search(r"\b(\d{1,2}(?:\.\d+)?)\s*(?:lakh|lakhs|lac)\b", cust_lower, re.IGNORECASE)
        if m_single:
            val = float(m_single.group(1))
            low = max(8, int(val - 2))
            high = int(val + 2)
            budget_str = f"~₹{m_single.group(1)} Lakh (₹{low}L – ₹{high}L range)"

    if not budget_str:
        if existing_budget and existing_budget not in ("Standard Range", ""):
            budget_str = existing_budget
        else:
            budget_str = VEHICLE_PRICE_MAP.get(primary_vid, ("", "₹15.00 Lakh – ₹24.50 Lakh"))[1]

    feat_short = ", ".join(features[:3])
    cars_short = ", ".join(interested_cars[:2])
    summary_text = f"Interested in {cars_short} | Focus: {feat_short} | Budget: {budget_str}"

    return {
        "primary_vehicle_id": primary_vid,
        "primary_vehicle_name": primary_vname,
        "interested_cars": interested_cars,
        "interested_features": features,
        "budget": budget_str,
        "key_points_summary": summary_text,
    }

class CustomerService:
    @staticmethod
    async def get_or_create_customer_by_phone(
        db: AsyncSession,
        phone: str,
        name: Optional[str] = None,
        vehicle_id: str = "thar_roxx",
        brand_id: Optional[str] = None
    ) -> Customer:
        """
        Retrieves or creates a unique customer identified by (Name + Phone Number) scoped to brand_id.
        If name is provided, matches (lower(name) == norm_name.lower() AND phone == normalized_phone).
        """
        b_id = resolve_brand(brand_id)
        normalized_phone = clean_phone(phone)
        norm_name = clean_name(name)
        cust_slug = make_customer_id(norm_name or "Valued Customer", normalized_phone, b_id)

        customer = None
        if norm_name:
            stmt = (
                select(Customer)
                .where(
                    (Customer.brand_id == b_id) &
                    (func.lower(Customer.name) == norm_name.lower()) &
                    ((Customer.phone == normalized_phone) | (Customer.phone == phone))
                )
                .options(
                    selectinload(Customer.sessions).selectinload(ConversationSession.transcripts),
                    selectinload(Customer.interactions),
                    selectinload(Customer.bookings),
                    selectinload(Customer.claims),
                )
            )
            res = await db.execute(stmt)
            customer = res.scalars().first()

            if not customer:
                stmt_placeholder = (
                    select(Customer)
                    .where(
                        (Customer.brand_id == b_id) &
                        ((Customer.phone == normalized_phone) | (Customer.phone == phone)) &
                        (func.lower(Customer.name).in_(["valued customer", "valued guest", "guest", "there"]))
                    )
                    .options(
                        selectinload(Customer.sessions).selectinload(ConversationSession.transcripts),
                        selectinload(Customer.interactions),
                        selectinload(Customer.bookings),
                        selectinload(Customer.claims),
                    )
                )
                res_ph = await db.execute(stmt_placeholder)
                placeholder_cust = res_ph.scalars().first()
                if placeholder_cust:
                    placeholder_cust.name = norm_name
                    placeholder_cust.customer_id = cust_slug
                    await db.commit()
                    customer = placeholder_cust
        else:
            stmt = (
                select(Customer)
                .where(
                    (Customer.brand_id == b_id) &
                    ((Customer.phone == normalized_phone) | (Customer.phone == phone) | (Customer.customer_id == cust_slug))
                )
                .order_by(Customer.updated_at.desc())
                .options(
                    selectinload(Customer.sessions).selectinload(ConversationSession.transcripts),
                    selectinload(Customer.interactions),
                    selectinload(Customer.bookings),
                    selectinload(Customer.claims),
                )
            )
            res = await db.execute(stmt)
            customer = res.scalars().first()

        if customer:
            return customer

        v_id = vehicle_id or ("bmw_x5" if b_id == "bmw" else "creta" if b_id == "hyundai" else "grand_vitara" if b_id == "maruti_suzuki" else "thar_roxx")
        default_budget = VEHICLE_PRICE_MAP.get(v_id, ("", "₹15.00 Lakh – ₹22.50 Lakh"))[1]

        customer = Customer(
            customer_id=cust_slug,
            brand_id=b_id,
            name=norm_name if norm_name else "Valued Customer",
            phone=normalized_phone,
            email=f"{cust_slug.lower()}@customer.{b_id}.com",
            city="Mumbai",
            preferred_language="Hinglish" if b_id != "bmw" else "English",
            current_phase="PRE_SALES",
            interested_vehicle_id=v_id,
            interested_variant="AX7L Diesel AT 4x4" if v_id == "thar_roxx" else "Official Edition",
            budget_range=default_budget,
            kyc_status="PENDING"
        )
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
        return customer

    @staticmethod
    async def get_or_create_default_customer(
        db: AsyncSession,
        phone: Optional[str] = None,
        name: Optional[str] = None,
        brand_id: Optional[str] = None
    ) -> Customer:
        """Retrieves default customer for the specified brand or entered phone."""
        b_id = resolve_brand(brand_id)
        if phone:
            return await CustomerService.get_or_create_customer_by_phone(db, phone=phone, name=name, brand_id=b_id)

        # Lookup brand-specific default customer
        stmt = (
            select(Customer)
            .where(Customer.brand_id == b_id)
            .order_by(Customer.id.asc())
            .options(
                selectinload(Customer.sessions).selectinload(ConversationSession.transcripts),
                selectinload(Customer.interactions),
                selectinload(Customer.bookings),
                selectinload(Customer.claims),
            )
        )
        result = await db.execute(stmt)
        customer = result.scalars().first()
        
        if not customer:
            # Fallback creation for that brand
            if b_id == "bmw":
                customer = Customer(
                    customer_id="CUST-BMW-98201",
                    brand_id="bmw",
                    name="Vikram Malhotra",
                    phone="+919820199001",
                    email="vikram.malhotra@luxurycorp.com",
                    city="Mumbai",
                    preferred_language="English",
                    current_phase="PRE_SALES",
                    interested_vehicle_id="bmw_x5",
                    interested_variant="xDrive40i M Sport",
                    budget_range="₹95 Lakh - ₹1.10 Crore",
                    loan_preapproval_amount=7500000,
                    loan_interest_rate="7.90%",
                    loan_status="PRE_APPROVED",
                    owned_vin="WBA31AY0098201BMW",
                    owned_vehicle_name="BMW 3 Series 330Li M Sport",
                    registration_number="MH 01 DX 3300",
                    odometer_km=14200,
                    insurance_policy_number="POL-BAJAJ-BMW-2026-9901",
                    insurance_type="BMW Secure Advanced Comprehensive",
                    pan_number="BAPVM9901L",
                    aadhaar_masked="XXXX-XXXX-9901",
                    kyc_status="VERIFIED"
                )
            elif b_id == "hyundai":
                customer = Customer(
                    customer_id="CUST-HYU-98201",
                    brand_id="hyundai",
                    name="Arjun Reddy",
                    phone="+919820199002",
                    email="arjun.reddy@techsol.in",
                    city="Mumbai",
                    preferred_language="Hinglish",
                    current_phase="PRE_SALES",
                    interested_vehicle_id="creta",
                    interested_variant="SX (O) 1.5 Turbo Petrol DCT",
                    budget_range="₹18 Lakh - ₹22 Lakh",
                    loan_preapproval_amount=1650000,
                    loan_interest_rate="8.25%",
                    loan_status="PRE_APPROVED",
                    owned_vin="MAL1HYU2026CRETA01",
                    owned_vehicle_name="Hyundai Venue SX 1.0 Turbo",
                    registration_number="MH 02 ER 8820",
                    odometer_km=21000,
                    insurance_policy_number="POL-HDFC-HYU-2026-5501",
                    insurance_type="Zero Depreciation Return-to-Invoice",
                    pan_number="ARJPR4401P",
                    aadhaar_masked="XXXX-XXXX-4401",
                    kyc_status="VERIFIED"
                )
            elif b_id == "maruti_suzuki":
                customer = Customer(
                    customer_id="CUST-MAR-98201",
                    brand_id="maruti_suzuki",
                    name="Manish Patel",
                    phone="+919820199003",
                    email="manish.patel@patelauto.com",
                    city="Mumbai",
                    preferred_language="Hinglish",
                    current_phase="PRE_SALES",
                    interested_vehicle_id="grand_vitara",
                    interested_variant="Alpha+ Intelligent Electric Hybrid e-CVT",
                    budget_range="₹16 Lakh - ₹21 Lakh",
                    loan_preapproval_amount=1700000,
                    loan_interest_rate="8.10%",
                    loan_status="PRE_APPROVED",
                    owned_vin="MAR1MSIL2026GV001",
                    owned_vehicle_name="Maruti Suzuki Baleno Alpha",
                    registration_number="MH 03 BT 5511",
                    odometer_km=34000,
                    insurance_policy_number="POL-MARUTI-INS-2026-3301",
                    insurance_type="Maruti Suzuki Genuine Insurance Zero-Dep",
                    pan_number="MPTMP1101M",
                    aadhaar_masked="XXXX-XXXX-1101",
                    kyc_status="VERIFIED"
                )
            else:
                customer = Customer(
                    customer_id="CUST-9820155432",
                    brand_id="mahindra",
                    name="Aarav Sharma",
                    phone="+919820155432",
                    email="aarav.sharma@example.com",
                    city="Mumbai",
                    preferred_language="Hinglish",
                    current_phase="PRE_SALES",
                    interested_vehicle_id="thar_roxx",
                    interested_variant="AX7L Diesel AT 4x4",
                    budget_range="₹18 Lakh - ₹25 Lakh",
                    pan_number="ABCPS1234K",
                    aadhaar_masked="XXXX-XXXX-8921",
                    kyc_status="VERIFIED",
                    loan_preapproval_amount=1850000,
                    loan_interest_rate="8.15%",
                    loan_status="PROVISIONALLY_APPROVED",
                    owned_vin="MAH1THARROXX2026MUM01",
                    owned_vehicle_name="Mahindra Thar ROXX AX7L Diesel AT 4x4",
                    registration_number="MH 02 FJ 9090",
                    odometer_km=9820,
                    insurance_policy_number="POL-ICICI-MH-2026-99201",
                    insurance_type="Zero-Depreciation Comprehensive"
                )
            db.add(customer)
            await db.commit()
            await db.refresh(customer)
        
        if not customer:
            customer = Customer(
                customer_id="CUST-9820155432",
                name="Aarav Sharma",
                phone="+919820155432",
                email="aarav.sharma@example.com",
                city="Mumbai",
                preferred_language="Hinglish",
                current_phase="PRE_SALES",
                interested_vehicle_id="thar_roxx",
                interested_variant="AX7L Diesel AT 4x4",
                budget_range="₹18 Lakh - ₹25 Lakh",
                pan_number="ABCPS1234K",
                aadhaar_masked="XXXX-XXXX-8921",
                kyc_status="VERIFIED",
                kyc_extracted_data={
                    "full_name": "Aarav Sharma",
                    "dob": "1990-05-14",
                    "pan": "ABCPS1234K",
                    "aadhaar_last4": "8921",
                    "city": "Mumbai",
                    "verified_at": "2026-08-24T18:30:00Z"
                },
                loan_preapproval_amount=1850000,
                loan_interest_rate="8.15%",
                voice_consent_hash="VBC-SHA256-AARAV-98201-LOAN1850K",
                loan_status="PROVISIONALLY_APPROVED",
                owned_vin="MAH1THARROXX2026MUM01",
                owned_vehicle_name="Mahindra Thar ROXX AX7L Diesel AT 4x4",
                registration_number="MH 02 FJ 9090",
                odometer_km=9820,
                insurance_policy_number="POL-ICICI-MH-2026-99201",
                insurance_type="Zero-Depreciation Comprehensive"
            )
            db.add(customer)
            await db.commit()
            await db.refresh(customer)
            
# Clean default customer without synthetic dummy sessions
            
            # Refresh with all eager loads
            stmt_reload = (
                select(Customer)
                .where(Customer.id == customer.id)
                .options(
                    selectinload(Customer.sessions).selectinload(ConversationSession.transcripts),
                    selectinload(Customer.interactions)
                )
            )
            res = await db.execute(stmt_reload)
            customer = res.scalars().first()
            
        return customer

    @staticmethod
    async def identify_or_register_customer(
        db: AsyncSession,
        name: str,
        phone: str,
        session_type: str = "LIVE_CALL",
        vehicle_id: str = "thar_roxx",
        brand_id: Optional[str] = None
    ) -> Tuple[Customer, ConversationSession, bool, int]:
        """
        Uniquely identifies a customer by Normalized (Name + Phone Number) and brand_id:
        - If returning customer (same Name + Phone): reuses single Customer entry, creates a NEW ConversationSession row.
        - If new customer (distinct Name + Phone): creates new Customer entry, creates a NEW ConversationSession row.
        Returns (Customer, ConversationSession, is_returning, total_session_count).
        """
        b_id = resolve_brand(brand_id)
        normalized_phone = clean_phone(phone)
        norm_name = clean_name(name) or "Valued Customer"
        cust_id_slug = make_customer_id(norm_name, normalized_phone, b_id)

        stmt = (
            select(Customer)
            .where(
                (Customer.brand_id == b_id) &
                (func.lower(Customer.name) == norm_name.lower()) &
                (Customer.phone == normalized_phone)
            )
            .options(
                selectinload(Customer.sessions),
                selectinload(Customer.interactions)
            )
        )
        result = await db.execute(stmt)
        customer = result.scalars().first()

        is_returning = False
        if customer:
            is_returning = True
            if vehicle_id:
                customer.interested_vehicle_id = vehicle_id
            customer.updated_at = datetime.now(timezone.utc)
            await db.commit()
        else:
            v_id = vehicle_id or ("bmw_x5" if b_id == "bmw" else "creta" if b_id == "hyundai" else "grand_vitara" if b_id == "maruti_suzuki" else "thar_roxx")
            default_budget = VEHICLE_PRICE_MAP.get(v_id, ("", "₹15.00 Lakh – ₹22.50 Lakh"))[1]
            customer = Customer(
                customer_id=cust_id_slug,
                brand_id=b_id,
                name=norm_name,
                phone=normalized_phone,
                city="Mumbai",
                preferred_language="Hinglish" if b_id != "bmw" else "English",
                current_phase="PRE_SALES",
                interested_vehicle_id=v_id,
                interested_variant="AX7L Diesel AT 4x4" if v_id == "thar_roxx" else "Official Variant",
                budget_range=default_budget
            )
            db.add(customer)
            await db.commit()
            await db.refresh(customer)

        # Always create a NEW ConversationSession (1:Many relationship against this Customer's Name + Phone)
        session_code = f"SESS-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        init_intel = extract_conversation_intelligence(
            [],
            default_vehicle_id=vehicle_id or customer.interested_vehicle_id or "thar_roxx",
            existing_budget=customer.budget_range
        )
        new_session = ConversationSession(
            session_id=session_code,
            brand_id=b_id,
            customer_id=customer.id,
            session_type=session_type,
            vehicle_id=vehicle_id or customer.interested_vehicle_id or "thar_roxx",
            summary=json.dumps(init_intel)
        )
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        cache.invalidate("sales_leads_")

        # Count total sessions for customer
        count_stmt = select(func.count(ConversationSession.id)).where(ConversationSession.customer_id == customer.id)
        count_res = await db.execute(count_stmt)
        total_sessions = count_res.scalar() or 1

        # Re-fetch customer with eager loads
        stmt_reload = (
            select(Customer)
            .where(Customer.id == customer.id)
            .options(
                selectinload(Customer.sessions).selectinload(ConversationSession.transcripts),
                selectinload(Customer.interactions)
            )
        )
        res_reload = await db.execute(stmt_reload)
        customer = res_reload.scalars().first()

        return customer, new_session, is_returning, total_sessions

    @staticmethod
    async def get_customer_by_id(db: AsyncSession, customer_id: str, brand_id: Optional[str] = None) -> Optional[Customer]:
        stmt = (
            select(Customer)
            .where(Customer.customer_id == customer_id)
            .options(
                selectinload(Customer.sessions).selectinload(ConversationSession.transcripts),
                selectinload(Customer.interactions),
                selectinload(Customer.bookings),
                selectinload(Customer.claims),
            )
        )
        if brand_id:
            stmt = stmt.where(Customer.brand_id == resolve_brand(brand_id))
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_customer_by_phone(
        db: AsyncSession,
        phone: str,
        brand_id: Optional[str] = None,
        name: Optional[str] = None
    ) -> Optional[Customer]:
        normalized = clean_phone(phone)
        norm_name = clean_name(name)
        b_id = resolve_brand(brand_id)
        if norm_name:
            stmt = (
                select(Customer)
                .where(
                    (Customer.phone == normalized) &
                    (func.lower(Customer.name) == norm_name.lower()) &
                    (Customer.brand_id == b_id)
                )
                .options(
                    selectinload(Customer.sessions).selectinload(ConversationSession.transcripts),
                    selectinload(Customer.interactions),
                    selectinload(Customer.bookings),
                    selectinload(Customer.claims),
                )
            )
            result = await db.execute(stmt)
            cust = result.scalars().first()
            if cust:
                return cust

        stmt = (
            select(Customer)
            .where((Customer.phone == normalized) & (Customer.brand_id == b_id))
            .order_by(Customer.updated_at.desc())
            .options(
                selectinload(Customer.sessions).selectinload(ConversationSession.transcripts),
                selectinload(Customer.interactions),
                selectinload(Customer.bookings),
                selectinload(Customer.claims),
            )
        )
        result = await db.execute(stmt)
        cust = result.scalars().first()
        if not cust:
            stmt_any = (
                select(Customer)
                .where(Customer.phone == normalized)
                .order_by(Customer.updated_at.desc())
                .options(
                    selectinload(Customer.sessions).selectinload(ConversationSession.transcripts),
                    selectinload(Customer.interactions),
                    selectinload(Customer.bookings),
                    selectinload(Customer.claims),
                )
            )
            r_any = await db.execute(stmt_any)
            cust = r_any.scalars().first()
        return cust

    @staticmethod
    async def log_interaction(
        db: AsyncSession,
        customer_id_str: str,
        speaker: str,
        message: str,
        channel: str = "VOICE_LIVE",
        session_id_str: Optional[str] = None,
        intent: Optional[str] = None,
        tool: Optional[str] = None,
        brand_id: Optional[str] = None
    ) -> Optional[InteractionLog]:
        b_id = resolve_brand(brand_id)
        customer = None
        if customer_id_str and customer_id_str != "GUEST-TRANSIENT":
            customer = await CustomerService.get_customer_by_id(db, customer_id_str, brand_id=b_id)
            if not customer:
                customer = await CustomerService.get_customer_by_phone(db, customer_id_str, brand_id=b_id)
        if not customer:
            stmt_latest = select(Customer).where(Customer.brand_id == b_id).order_by(Customer.updated_at.desc())
            res_latest = await db.execute(stmt_latest)
            customer = res_latest.scalars().first()
        if not customer:
            return InteractionLog(
                id=0,
                brand_id=b_id,
                session_id=None,
                customer_id=0,
                channel=channel,
                speaker=speaker,
                message=message,
                extracted_intent=intent,
                tool_triggered=tool
            )
        
        session_db_id = None
        sess = None
        if session_id_str:
            stmt = select(ConversationSession).where(ConversationSession.session_id == session_id_str)
            res = await db.execute(stmt)
            sess = res.scalars().first()
            if not sess:
                sess = ConversationSession(
                    session_id=session_id_str,
                    brand_id=b_id,
                    customer_id=customer.id,
                    session_type="LIVE_CALL" if channel == "VOICE_LIVE" else "CHAT_BOT",
                    vehicle_id=customer.interested_vehicle_id or "thar_roxx",
                    summary=f"Virtual Showroom Consultation for {customer.name}"
                )
                db.add(sess)
                await db.commit()
                await db.refresh(sess)
            session_db_id = sess.id

        log = InteractionLog(
            brand_id=b_id,
            session_id=session_db_id,
            customer_id=customer.id,
            channel=channel,
            speaker=speaker,
            message=message,
            extracted_intent=intent,
            tool_triggered=tool
        )
        db.add(log)
        await db.flush()

        # Continuously update conversation intelligence (car, features, budget) on each turn
        if sess:
            logs_res = await db.execute(
                select(InteractionLog)
                .where(InteractionLog.session_id == sess.id)
                .order_by(InteractionLog.created_at.asc())
            )
            sess_logs = logs_res.scalars().all()
            msg_list = [{"speaker": l.speaker, "message": l.message} for l in sess_logs]
            intel = extract_conversation_intelligence(
                msg_list,
                default_vehicle_id=sess.vehicle_id or customer.interested_vehicle_id or "thar_roxx",
                existing_budget=customer.budget_range
            )
            sess.vehicle_id = intel["primary_vehicle_id"]
            sess.summary = json.dumps(intel)
            customer.interested_vehicle_id = intel["primary_vehicle_id"]
            customer.budget_range = intel["budget"]
            customer.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(log)
        cache.invalidate("sales_leads_")
        return log

    @staticmethod
    async def get_customer_sessions(db: AsyncSession, customer_id_str: str, brand_id: Optional[str] = None) -> List[ConversationSession]:
        b_id = resolve_brand(brand_id)
        customer = await CustomerService.get_customer_by_id(db, customer_id_str, brand_id=b_id)
        if not customer:
            customer = await CustomerService.get_customer_by_phone(db, customer_id_str, brand_id=b_id)
        if not customer:
            return []
        stmt = (
            select(ConversationSession)
            .where(ConversationSession.customer_id == customer.id)
            .options(selectinload(ConversationSession.transcripts))
            .order_by(ConversationSession.created_at.desc())
        )
        if brand_id:
            stmt = stmt.where(ConversationSession.brand_id == b_id)
        res = await db.execute(stmt)
        return res.scalars().all()

    @staticmethod
    async def save_full_session_transcript(
        db: AsyncSession,
        session_id_str: str,
        customer_id_str: Optional[str] = None,
        customer_name: Optional[str] = None,
        customer_phone: Optional[str] = None,
        vehicle_id: Optional[str] = "thar_roxx",
        channel: str = "VOICE_LIVE",
        messages: List[dict] = [],
        brand_id: Optional[str] = None
    ) -> ConversationSession:
        """
        Guarantees full persistence of conversation session and all its transcript turns upon End Call,
        and extracts Interested Car, Features, and Budget for the Sales Consultant.
        """
        b_id = resolve_brand(brand_id)
        customer = None
        if customer_phone and customer_phone.strip():
            customer = await CustomerService.get_or_create_customer_by_phone(
                db,
                phone=customer_phone,
                name=customer_name or "Valued Customer",
                vehicle_id=vehicle_id or "thar_roxx",
                brand_id=b_id
            )
        elif customer_id_str and customer_id_str != "GUEST-TRANSIENT":
            customer = await CustomerService.get_customer_by_id(db, customer_id_str, brand_id=b_id)
            
        if not customer:
            stmt_latest = select(Customer).where(Customer.brand_id == b_id).order_by(Customer.updated_at.desc())
            res_latest = await db.execute(stmt_latest)
            customer = res_latest.scalars().first()
            if not customer:
                return ConversationSession(
                    id=0,
                    session_id=session_id_str,
                    brand_id=b_id,
                    customer_id=0,
                    session_type="LIVE_CALL" if channel == "VOICE_LIVE" else "CHAT_BOT",
                    vehicle_id=vehicle_id or "thar_roxx"
                )

        stmt = select(ConversationSession).where(ConversationSession.session_id == session_id_str)
        res = await db.execute(stmt)
        sess = res.scalars().first()
        if not sess:
            sess = ConversationSession(
                session_id=session_id_str,
                brand_id=b_id,
                customer_id=customer.id,
                session_type="LIVE_CALL" if channel == "VOICE_LIVE" else "CHAT_BOT",
                vehicle_id=vehicle_id or customer.interested_vehicle_id or "thar_roxx",
                summary=f"Virtual Showroom Consultation for {customer.name}"
            )
            db.add(sess)
            await db.commit()
            await db.refresh(sess)
        elif sess.customer_id != customer.id:
            sess.customer_id = customer.id

        # Query existing messages for deduplication
        existing_stmt = select(InteractionLog).where(InteractionLog.session_id == sess.id).order_by(InteractionLog.created_at.asc())
        e_res = await db.execute(existing_stmt)
        existing_logs = list(e_res.scalars().all())
        existing_texts = {(l.speaker, l.message.strip()) for l in existing_logs}

        for m in messages:
            spk = m.get("speaker", "customer")
            if spk == "system":
                continue
            text = m.get("text", "").strip()
            if not text or (spk, text) in existing_texts:
                continue

            log = InteractionLog(
                brand_id=b_id,
                session_id=sess.id,
                customer_id=customer.id,
                channel=channel or "VOICE_LIVE",
                speaker=spk,
                message=text,
                extracted_intent=m.get("toolCall"),
                tool_triggered=m.get("toolCall")
            )
            db.add(log)
            existing_logs.append(log)
            existing_texts.add((spk, text))

        sess.ended_at = datetime.now(timezone.utc)
        
        # Extract Car, Features, and Budget intelligence from the complete session dialogue
        all_turn_dicts = [{"speaker": l.speaker, "message": l.message} for l in existing_logs]
        intel = extract_conversation_intelligence(
            all_turn_dicts,
            default_vehicle_id=vehicle_id or sess.vehicle_id or customer.interested_vehicle_id or "thar_roxx",
            existing_budget=customer.budget_range
        )
        sess.vehicle_id = intel["primary_vehicle_id"]
        sess.summary = json.dumps(intel)
        db.add(sess)

        # Update Customer profile with latest interested car, budget, and checklist
        from app.services.checklist_service import ChecklistService
        from app.models.booking import TestDriveBooking
        from sqlalchemy.orm.attributes import flag_modified

        veh_id = intel["primary_vehicle_id"]
        customer.interested_vehicle_id = veh_id
        customer.budget_range = intel["budget"]
        customer.updated_at = datetime.now(timezone.utc)

        customer_dialogues = " ".join([d["message"] for d in all_turn_dicts if d.get("speaker") == "customer"])
        extracted_checklist = ChecklistService.extract_checklist_items(customer_dialogues, vehicle_id=veh_id)
        if not extracted_checklist:
            extracted_checklist = [f"Demonstrate / Discuss {feat}" for feat in intel["interested_features"]]
        if not extracted_checklist:
            extracted_checklist = ChecklistService.get_static_checklist(veh_id)

        # Merge with any previous conversation checklist items so multiple conversations accumulate asks
        prev_checklist = list(customer.advisor_checklist or [])
        merged_checklist = list(dict.fromkeys(list(extracted_checklist) + prev_checklist))[:6]
        customer.advisor_checklist = merged_checklist
        flag_modified(customer, "advisor_checklist")
        db.add(customer)

        # Update any active test drive bookings for this customer
        booking_stmt = select(TestDriveBooking).where(TestDriveBooking.customer_id == customer.id)
        b_res = await db.execute(booking_stmt)
        for b in b_res.scalars().all():
            b.advisor_checklist = merged_checklist
            flag_modified(b, "advisor_checklist")
            db.add(b)

        await db.commit()
        await db.refresh(sess)
        cache.invalidate("sales_leads_")
        return sess
