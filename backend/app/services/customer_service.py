import uuid
import re
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from app.models.customer import Customer, ConversationSession, InteractionLog

def clean_phone(phone_str: str) -> str:
    """Normalizes phone numbers to standard E.164 / +91 format for consistent identification."""
    raw = re.sub(r"[\s\-\(\)\.]", "", str(phone_str).strip())
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

class CustomerService:
    @staticmethod
    async def get_or_create_customer_by_phone(
        db: AsyncSession,
        phone: str,
        name: Optional[str] = None,
        vehicle_id: str = "thar_roxx",
        brand_id: Optional[str] = None
    ) -> Customer:
        """Retrieves customer dynamically by their entered phone number and brand_id or registers them."""
        b_id = resolve_brand(brand_id)
        normalized_phone = clean_phone(phone)
        digits = re.sub(r"\D", "", phone)
        cust_slug = f"CUST-{b_id.upper()[:3]}-{digits[-10:] if len(digits) >= 10 else (digits or uuid.uuid4().hex[:8])}"

        stmt = (
            select(Customer)
            .where(
                (Customer.brand_id == b_id) & (
                    (Customer.phone == normalized_phone) |
                    (Customer.phone == phone) |
                    (Customer.customer_id == cust_slug)
                )
            )
            .options(
                selectinload(Customer.sessions).selectinload(ConversationSession.transcripts),
                selectinload(Customer.interactions),
                selectinload(Customer.bookings),
                selectinload(Customer.claims),
            )
        )
        result = await db.execute(stmt)
        customer = result.scalars().first()

        if customer:
            if name and name.strip() and customer.name in ["Valued Customer", "Guest"]:
                customer.name = name.strip()
                await db.commit()
            return customer

        # Create new customer for this brand
        customer = Customer(
            customer_id=cust_slug,
            brand_id=b_id,
            name=name.strip() if name and name.strip() else "Valued Customer",
            phone=normalized_phone,
            email=f"{cust_slug.lower()}@customer.{b_id}.com",
            city="Mumbai",
            preferred_language="Hinglish" if b_id != "bmw" else "English",
            current_phase="PRE_SALES",
            interested_vehicle_id=vehicle_id or ("bmw_x5" if b_id == "bmw" else "creta" if b_id == "hyundai" else "grand_vitara" if b_id == "maruti_suzuki" else "thar_roxx"),
            interested_variant="Official Edition",
            budget_range="Standard Range",
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
        Looks up by normalized phone number and brand_id:
        - If returning user: keeps single Customer entry for this brand, updates name/vehicle if needed, creates a NEW ConversationSession row.
        - If new user: creates single Customer entry for this brand, creates ConversationSession row.
        Returns (Customer, ConversationSession, is_returning, total_session_count).
        """
        b_id = resolve_brand(brand_id)
        normalized_phone = clean_phone(phone)
        
        stmt = (
            select(Customer)
            .where((Customer.phone == normalized_phone) & (Customer.brand_id == b_id))
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
            if name.strip():
                customer.name = name.strip()
            if vehicle_id:
                customer.interested_vehicle_id = vehicle_id
            await db.commit()
        else:
            digits = re.sub(r"\D", "", phone)
            cust_id_slug = f"CUST-{b_id.upper()[:3]}-{digits[-10:] if len(digits) >= 10 else digits}"
            customer = Customer(
                customer_id=cust_id_slug,
                brand_id=b_id,
                name=name.strip(),
                phone=normalized_phone,
                city="Mumbai",
                preferred_language="Hinglish" if b_id != "bmw" else "English",
                current_phase="PRE_SALES",
                interested_vehicle_id=vehicle_id or ("bmw_x5" if b_id == "bmw" else "creta" if b_id == "hyundai" else "grand_vitara" if b_id == "maruti_suzuki" else "thar_roxx"),
                interested_variant="Official Variant"
            )
            db.add(customer)
            await db.commit()
            await db.refresh(customer)

        # Create NEW ConversationSession (1:Many relationship) with brand_id
        session_code = f"SESS-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        new_session = ConversationSession(
            session_id=session_code,
            brand_id=b_id,
            customer_id=customer.id,
            session_type=session_type,
            vehicle_id=vehicle_id or customer.interested_vehicle_id or "thar_roxx"
        )
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)

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
    async def get_customer_by_phone(db: AsyncSession, phone: str, brand_id: Optional[str] = None) -> Optional[Customer]:
        normalized = clean_phone(phone)
        b_id = resolve_brand(brand_id)
        stmt = (
            select(Customer)
            .where((Customer.phone == normalized) & (Customer.brand_id == b_id))
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
            # Fallback check by phone alone if brand wasn't explicitly partitioned yet
            stmt_any = (
                select(Customer)
                .where(Customer.phone == normalized)
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
    ) -> InteractionLog:
        b_id = resolve_brand(brand_id)
        customer = await CustomerService.get_customer_by_id(db, customer_id_str, brand_id=b_id)
        if not customer:
            customer = await CustomerService.get_customer_by_phone(db, customer_id_str, brand_id=b_id)
        if not customer:
            customer = await CustomerService.get_or_create_default_customer(db, brand_id=b_id)
        
        session_db_id = None
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
        await db.commit()
        await db.refresh(log)
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
        Guarantees full persistence of conversation session and all its transcript turns upon End Call.
        """
        b_id = resolve_brand(brand_id)
        customer = None
        if customer_phone and customer_phone.strip():
            customer = await CustomerService.get_or_create_customer_by_phone(
                db, phone=customer_phone, name=customer_name or "Valued Customer", vehicle_id=vehicle_id or "thar_roxx", brand_id=b_id
            )
        elif customer_id_str:
            customer = await CustomerService.get_customer_by_id(db, customer_id_str, brand_id=b_id)
            
        if not customer:
            customer = await CustomerService.get_or_create_default_customer(db, brand_id=b_id)
            if customer_name and customer_name.strip() and customer.name in ["Valued Customer", "Guest"]:
                customer.name = customer_name.strip()
                await db.commit()

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

        # Query existing messages for deduplication
        existing_stmt = select(InteractionLog).where(InteractionLog.session_id == sess.id)
        e_res = await db.execute(existing_stmt)
        existing_logs = e_res.scalars().all()
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
            existing_texts.add((spk, text))

        sess.ended_at = datetime.now(timezone.utc)
        
        # Automatically extract and persist focus features for the Sales Advisor's Demo Checklist
        from app.services.checklist_service import ChecklistService
        from app.models.booking import TestDriveBooking
        from sqlalchemy.orm.attributes import flag_modified

        veh_id = vehicle_id or customer.interested_vehicle_id or "thar_roxx"
        customer_dialogues = " ".join([m.get("text", "") for m in messages if m.get("speaker") == "customer"])
        
        extracted_checklist = ChecklistService.extract_checklist_items(customer_dialogues, vehicle_id=veh_id)
        if not extracted_checklist:
            extracted_checklist = ChecklistService.get_static_checklist(veh_id)

        customer.advisor_checklist = list(extracted_checklist)
        flag_modified(customer, "advisor_checklist")
        db.add(customer)

        # Update any active test drive bookings for this customer
        booking_stmt = select(TestDriveBooking).where(TestDriveBooking.customer_id == customer.id)
        b_res = await db.execute(booking_stmt)
        for b in b_res.scalars().all():
            b.advisor_checklist = list(extracted_checklist)
            flag_modified(b, "advisor_checklist")
            db.add(b)

        await db.commit()
        await db.refresh(sess)
        return sess
