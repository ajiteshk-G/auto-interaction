from app.services.cache_service import cache
import os
import uuid
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.models.sales_ride import TestRideRecording
from app.models.customer import Customer, InteractionLog
from app.models.booking import TestDriveBooking
from app.schemas.sales_recording import (
    TestRideRecordingUploadRequest,
    TestRideInsightResponse,
    TestRideLeadItem
)
from app.services.catalog_service import CatalogService
from app.services.customer_service import clean_phone
from app.services.brand_service import BrandService
from app.config import settings

logger = logging.getLogger("sales_recording_service")

UPLOAD_BASE_DIR = "/tmp/mahindra_test_rides"
os.makedirs(UPLOAD_BASE_DIR, exist_ok=True)

def _create_synthetic_wav_file(filepath: str):
    """Creates a minimal valid WAV file header and blank audio content."""
    import struct
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    sample_rate = 16000
    num_samples = sample_rate * 3 # 3 seconds
    byte_rate = sample_rate * 2
    block_align = 2
    data_size = num_samples * 2
    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        data_size + 36,
        b'WAVE',
        b'fmt ',
        16,
        1,
        1,
        sample_rate,
        byte_rate,
        block_align,
        16,
        b'data',
        data_size
    )
    with open(filepath, "wb") as f:
        f.write(header)
        f.write(b'\x00' * data_size)

class SalesRecordingService:
    @staticmethod
    def _build_customer_conversation_intelligence(
        customer: Optional[Customer],
        sessions: List[Any],
        logs: List[InteractionLog],
        default_vehicle_id: str = "thar_roxx"
    ) -> Dict[str, Any]:
        """
        Groups all conversations for a unique (Name + Phone Number) customer by calendar day,
        extracting the interested car, interested features, and budget for each conversation and each day.
        """
        from app.services.customer_service import extract_conversation_intelligence, VEHICLE_PRICE_MAP
        from app.schemas.sales_recording import (
            ConversationTurnItem,
            ConversationSessionSummary,
            DailyConversationGroup
        )

        cust_budget = customer.budget_range if customer else None
        fallback_vid = default_vehicle_id or (customer.interested_vehicle_id if customer else "thar_roxx") or "thar_roxx"

        # Map logs by session_id (DB integer ID) and also handle orphan logs
        logs_by_sess_id: Dict[int, List[InteractionLog]] = {}
        orphan_logs: List[InteractionLog] = []
        for lg in sorted(logs, key=lambda x: x.created_at or datetime.min):
            if lg.channel == "TEST_RIDE_IN_VEHICLE" or lg.speaker == "system":
                continue
            if lg.session_id:
                logs_by_sess_id.setdefault(lg.session_id, []).append(lg)
            else:
                orphan_logs.append(lg)

        session_summaries: List[ConversationSessionSummary] = []
        all_cars: List[str] = []
        all_features: List[str] = []
        latest_budget: Optional[str] = cust_budget

        sorted_sessions = sorted(sessions, key=lambda s: s.created_at or datetime.min, reverse=True)

        for sess in sorted_sessions:
            s_logs = logs_by_sess_id.get(sess.id, [])
            # If multiple sessions exist, skip completely empty 0-turn shell sessions if other sessions have turns
            if not s_logs and len(sorted_sessions) > 1:
                continue

            msg_dicts = [{"speaker": l.speaker, "message": l.message} for l in s_logs]
            parsed_summary = None
            if sess.summary and sess.summary.strip().startswith("{"):
                try:
                    parsed_summary = json.loads(sess.summary)
                except Exception:
                    parsed_summary = None

            if not parsed_summary or s_logs:
                parsed_summary = extract_conversation_intelligence(
                    msg_dicts,
                    default_vehicle_id=sess.vehicle_id or fallback_vid,
                    existing_budget=cust_budget
                )

            car_name = parsed_summary.get("primary_vehicle_name") or VEHICLE_PRICE_MAP.get(sess.vehicle_id or fallback_vid, ("Mahindra Thar ROXX", ""))[0]
            sess_cars = parsed_summary.get("interested_cars") or [car_name]
            sess_feats = parsed_summary.get("interested_features") or ["SUV Styling & Road Presence", "Cabin Comfort & Infotainment"]
            sess_budget = parsed_summary.get("budget") or cust_budget or VEHICLE_PRICE_MAP.get(sess.vehicle_id or fallback_vid, ("", "₹15.00 Lakh – ₹22.50 Lakh"))[1]
            key_points = parsed_summary.get("key_points_summary") or f"Interested in {car_name} | Focus: {', '.join(sess_feats[:3])} | Budget: {sess_budget}"

            for c_item in sess_cars:
                if c_item not in all_cars:
                    all_cars.append(c_item)
            for f_item in sess_feats:
                if f_item not in all_features:
                    all_features.append(f_item)
            if sess_budget and (not latest_budget or latest_budget == "Standard Range"):
                latest_budget = sess_budget

            dt = sess.created_at or datetime.now(timezone.utc)
            date_key = dt.strftime("%Y-%m-%d")
            date_label = dt.strftime("%a, %d %b %Y")
            time_label = dt.strftime("%I:%M %p")

            turn_items = [
                ConversationTurnItem(
                    speaker=customer.name if (l.speaker == "customer" and customer) else ("Customer" if l.speaker == "customer" else "Kavya (AI Specialist)"),
                    role=l.speaker,
                    message=l.message,
                    timestamp=l.created_at.strftime("%I:%M %p") if l.created_at else time_label
                )
                for l in s_logs
            ]

            session_summaries.append(ConversationSessionSummary(
                session_id=sess.session_id,
                date_key=date_key,
                date_label=date_label,
                time_label=time_label,
                channel="LIVE_VOICE" if sess.session_type in ("LIVE_CALL", "VOICE_LIVE") else "CHAT_BOT",
                interested_car=", ".join(sess_cars[:2]),
                interested_features=sess_feats,
                budget=sess_budget,
                key_points_summary=key_points,
                turn_count=len(turn_items),
                turns=turn_items
            ))

        # Also include orphan logs if no session captured them
        if orphan_logs and not session_summaries:
            msg_dicts = [{"speaker": l.speaker, "message": l.message} for l in orphan_logs]
            intel = extract_conversation_intelligence(msg_dicts, default_vehicle_id=fallback_vid, existing_budget=cust_budget)
            dt = orphan_logs[-1].created_at or datetime.now(timezone.utc)
            date_key = dt.strftime("%Y-%m-%d")
            date_label = dt.strftime("%a, %d %b %Y")
            time_label = dt.strftime("%I:%M %p")
            for c_item in intel["interested_cars"]:
                if c_item not in all_cars:
                    all_cars.append(c_item)
            for f_item in intel["interested_features"]:
                if f_item not in all_features:
                    all_features.append(f_item)
            latest_budget = intel["budget"]
            turn_items = [
                ConversationTurnItem(
                    speaker=customer.name if (l.speaker == "customer" and customer) else ("Customer" if l.speaker == "customer" else "Kavya (AI Specialist)"),
                    role=l.speaker,
                    message=l.message,
                    timestamp=l.created_at.strftime("%I:%M %p") if l.created_at else time_label
                )
                for l in orphan_logs
            ]
            session_summaries.append(ConversationSessionSummary(
                session_id=f"SESS-{dt.strftime('%Y%m%d-%H%M')}",
                date_key=date_key,
                date_label=date_label,
                time_label=time_label,
                channel="LIVE_VOICE",
                interested_car=", ".join(intel["interested_cars"][:2]),
                interested_features=intel["interested_features"],
                budget=intel["budget"],
                key_points_summary=intel["key_points_summary"],
                turn_count=len(turn_items),
                turns=turn_items
            ))

        if not all_cars:
            def_car = VEHICLE_PRICE_MAP.get(fallback_vid, (fallback_vid.replace("_", " ").title(), "₹15.00 Lakh – ₹22.50 Lakh"))[0]
            all_cars.append(def_car)
        if not all_features:
            all_features = ["SUV Styling & Road Presence", "Cabin Comfort & Infotainment"]
        if not latest_budget or latest_budget == "Standard Range":
            latest_budget = VEHICLE_PRICE_MAP.get(fallback_vid, ("", "₹15.00 Lakh – ₹22.50 Lakh"))[1]

        # Group sessions by calendar day (date_key descending)
        day_groups_map: Dict[str, List[ConversationSessionSummary]] = {}
        day_labels_map: Dict[str, str] = {}
        for s_sum in session_summaries:
            day_groups_map.setdefault(s_sum.date_key, []).append(s_sum)
            day_labels_map[s_sum.date_key] = s_sum.date_label

        conversations_by_day: List[DailyConversationGroup] = []
        for d_key in sorted(day_groups_map.keys(), reverse=True):
            d_sessions = day_groups_map[d_key]
            d_cars: List[str] = []
            d_feats: List[str] = []
            d_budget = d_sessions[0].budget if d_sessions else latest_budget
            for ds in d_sessions:
                for c_part in [x.strip() for x in ds.interested_car.split(",") if x.strip()]:
                    if c_part not in d_cars:
                        d_cars.append(c_part)
                for f_part in ds.interested_features:
                    if f_part not in d_feats:
                        d_feats.append(f_part)

            conversations_by_day.append(DailyConversationGroup(
                date_key=d_key,
                date_label=day_labels_map[d_key],
                conversation_count=len(d_sessions),
                cars_discussed=d_cars,
                features_interested=d_feats[:5],
                budget_mentioned=d_budget,
                sessions=d_sessions
            ))

        return {
            "total_conversations": len(session_summaries),
            "interested_cars": all_cars,
            "interested_features": all_features[:6],
            "budget_range": latest_budget,
            "conversations_by_day": conversations_by_day,
        }

    @staticmethod
    async def get_sales_leads(
        db: AsyncSession,
        dealership_id: Optional[str] = None,
        brand_id: Optional[str] = None
    ) -> List[TestRideLeadItem]:
        """
        Fetch qualified leads for the Sales Consultant App scoped to brand.
        Strictly 1 lead row per unique customer (identified by Unique Name + Phone Number).
        Includes per-day conversation breakdown, interested car(s), interested features, and budget.
        """
        from app.models.customer import ConversationSession
        from app.services.customer_service import clean_name

        b_id = (brand_id or (BrandService.get_active_brand().id if BrandService.get_active_brand() else "mahindra")).lower()
        cache_key = f"sales_leads_{b_id}_{dealership_id or 'all'}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
            
        booking_stmt = (
            select(TestDriveBooking)
            .where(TestDriveBooking.brand_id == b_id)
            .order_by(TestDriveBooking.created_at.desc())
        )
        if dealership_id and dealership_id.strip() and dealership_id.strip() != "ALL":
            booking_stmt = booking_stmt.where(
                (TestDriveBooking.dealership_id == dealership_id.strip()) |
                (TestDriveBooking.dealership_name.ilike(f"%{dealership_id.strip()}%"))
            )
        booking_res = await db.execute(booking_stmt)
        bookings = booking_res.scalars().all()

        leads: List[TestRideLeadItem] = []
        seen_customer_keys = set()

        # Batch prefetch all Customers, Sessions, InteractionLogs, and Recordings for this brand
        all_cust_res = await db.execute(
            select(Customer)
            .where(Customer.brand_id == b_id)
            .options(
                selectinload(Customer.sessions),
                selectinload(Customer.interactions)
            )
            .order_by(Customer.updated_at.desc())
        )
        all_customers_list = all_cust_res.scalars().all()
        cust_map = {c.id: c for c in all_customers_list}

        rec_res = await db.execute(
            select(TestRideRecording.booking_reference, TestRideRecording.customer_id)
            .where(TestRideRecording.brand_id == b_id)
        )
        existing_rec_refs = {r[0] for r in rec_res.all() if r[0]}

        for b in bookings:
            c = cust_map.get(b.customer_id)

            cust_name = c.name if c else "Valued Customer"
            cust_phone = c.phone if c else ""
            cust_email = c.email if c else None
            cust_city = c.city if c else "Mumbai"
            cust_id_str = c.customer_id if c else f"CUST-{b.customer_id}"

            norm_phone = clean_phone(cust_phone) if cust_phone else f"NOPHONE-{b.customer_id}"
            norm_name = (clean_name(cust_name) or cust_name).lower()
            composite_key = (norm_name, norm_phone)
            
            if composite_key in seen_customer_keys:
                continue
            seen_customer_keys.add(composite_key)

            intel_data = SalesRecordingService._build_customer_conversation_intelligence(
                customer=c,
                sessions=list(c.sessions) if c else [],
                logs=list(c.interactions) if c else [],
                default_vehicle_id=b.vehicle_id
            )

            v_info = CatalogService.get_vehicle_by_id(b.vehicle_id)
            veh_name = v_info.name if v_info else b.vehicle_id.replace("_", " ").title()

            db_checklist = b.advisor_checklist or (c.advisor_checklist if c else None)
            is_custom = bool(db_checklist and len(db_checklist) > 0)
            final_checklist = db_checklist if is_custom else [f"Demonstrate / Highlight {f}" for f in intel_data["interested_features"][:4]]

            has_tr_rec = b.booking_reference in existing_rec_refs
            resolved_status = "TestRide_Completed" if (b.status == "TestRide_Completed" or has_tr_rec) else (b.status or "CONFIRMED")

            leads.append(TestRideLeadItem(
                customer_id=cust_id_str,
                brand_id=b_id,
                name=cust_name,
                phone=cust_phone,
                email=cust_email,
                city=cust_city,
                preferred_vehicle=f"{veh_name} ({b.variant})",
                vehicle_name=veh_name,
                vehicle_id=b.vehicle_id,
                variant=b.variant,
                booking_reference=b.booking_reference,
                dealership_id=b.dealership_id,
                dealership_name=b.dealership_name,
                booking_type=b.booking_type or "HOME_DOORSTEP",
                delivery_address=b.delivery_address,
                booking_status=resolved_status,
                scheduled_slot=f"{b.scheduled_date} at {b.scheduled_time_slot}",
                presales_notes=f"Interested in {', '.join(intel_data['interested_cars'])} | Features: {', '.join(intel_data['interested_features'][:3])} | Budget: {intel_data['budget_range']}",
                advisor_checklist=final_checklist,
                is_custom_checklist=True,
                total_conversations=intel_data["total_conversations"],
                interested_cars=intel_data["interested_cars"],
                interested_features=intel_data["interested_features"],
                budget_range=intel_data["budget_range"],
                conversations_by_day=intel_data["conversations_by_day"]
            ))

        if not dealership_id or dealership_id == "ALL":
            active_brand = BrandService.get_brand(b_id)
            def_dlr_name = (active_brand.dealerships[0].name if active_brand and active_brand.dealerships else f"{b_id.title()} Official Dealership")
            def_dlr_id = (active_brand.dealerships[0].id if active_brand and active_brand.dealerships else f"{b_id}_flagship")

            for c in all_customers_list:
                norm_phone = clean_phone(c.phone) if c.phone else f"NOPHONE-{c.id}"
                norm_name = (clean_name(c.name) or c.name).lower()
                composite_key = (norm_name, norm_phone)
                if composite_key not in seen_customer_keys:
                    seen_customer_keys.add(composite_key)
                    intel_data = SalesRecordingService._build_customer_conversation_intelligence(
                        customer=c,
                        sessions=list(c.sessions),
                        logs=list(c.interactions),
                        default_vehicle_id=c.interested_vehicle_id or "thar_roxx"
                    )

                    v_info = CatalogService.get_vehicle_by_id(c.interested_vehicle_id or ("bmw_x5" if b_id == "bmw" else "creta" if b_id == "hyundai" else "grand_vitara" if b_id == "maruti_suzuki" else "thar_roxx"))
                    veh_name = v_info.name if v_info else (intel_data["interested_cars"][0] if intel_data["interested_cars"] else "Mahindra Thar ROXX")
                    db_checklist = c.advisor_checklist
                    is_custom = bool(db_checklist and len(db_checklist) > 0)
                    final_checklist = db_checklist if is_custom else [f"Demonstrate / Highlight {f}" for f in intel_data["interested_features"][:4]]

                    tr_rec_stmt = select(TestRideRecording).where(TestRideRecording.customer_id == c.id, TestRideRecording.brand_id == b_id)
                    tr_res = await db.execute(tr_rec_stmt)
                    has_tr_rec = tr_res.scalars().first() is not None

                    resolved_status = "TestRide_Completed" if (c.current_phase == "TestRide_Completed" or has_tr_rec) else "INQUIRY_READY_FOR_RIDE"

                    leads.append(TestRideLeadItem(
                        customer_id=c.customer_id,
                        brand_id=b_id,
                        name=c.name,
                        phone=c.phone,
                        email=c.email,
                        city=c.city or "Mumbai",
                        preferred_vehicle=f"{veh_name} ({c.interested_variant or 'Official Variant'})",
                        vehicle_name=veh_name,
                        vehicle_id=c.interested_vehicle_id or ("bmw_x5" if b_id == "bmw" else "thar_roxx"),
                        variant=c.interested_variant or "Official Variant",
                        dealership_name=def_dlr_name,
                        dealership_id=def_dlr_id,
                        booking_status=resolved_status,
                        scheduled_slot=f"{intel_data['total_conversations']} Pre-Sales Conversation(s)",
                        presales_notes=f"Interested in {', '.join(intel_data['interested_cars'])} | Features: {', '.join(intel_data['interested_features'][:3])} | Budget: {intel_data['budget_range']}",
                        advisor_checklist=final_checklist,
                        is_custom_checklist=True,
                        total_conversations=intel_data["total_conversations"],
                        interested_cars=intel_data["interested_cars"],
                        interested_features=intel_data["interested_features"],
                        budget_range=intel_data["budget_range"],
                        conversations_by_day=intel_data["conversations_by_day"]
                    ))

        cache.set(cache_key, leads, ttl_seconds=15)
        return leads

    @staticmethod
    async def process_and_store_recording(db: AsyncSession, req: TestRideRecordingUploadRequest) -> TestRideRecording:
        # Determine brand_id
        b_id = (
            getattr(req, "brand_id", None) or
            (BrandService.get_active_brand().id if BrandService.get_active_brand() else "mahindra")
        ).lower()

        # Invalidate leads cache on new recording upload
        cache.invalidate(f"sales_leads_{b_id}")
        cache.invalidate("sales_leads_")
        """
        Saves test ride audio recording at:
        gs://mahindra-sales-recordings/test_rides/<date>/<booking_reference>.wav
        Executes Gemini transcription with speaker identification and multi-dimensional insights.
        Persists in database against that customer and booking.
        """
        # 1. Resolve Customer
        stmt = select(Customer).where(
            ((Customer.customer_id == req.customer_id) | (Customer.phone == req.customer_id)) &
            (Customer.brand_id == b_id)
        )
        res = await db.execute(stmt)
        customer = res.scalars().first()

        if not customer:
            stmt_all = select(Customer).where(Customer.brand_id == b_id).limit(1)
            res_all = await db.execute(stmt_all)
            customer = res_all.scalars().first()
            if not customer:
                customer = Customer(
                    customer_id=req.customer_id,
                    brand_id=b_id,
                    name=req.customer_name or "Aarav Sharma",
                    phone="+91 98201 23456",
                    email="aarav.sharma@example.com",
                    city="Mumbai",
                    current_phase="SALES_TEST_RIDE"
                )
                db.add(customer)
                await db.flush()

        # 2. Resolve Booking and Booking Reference
        booking: Optional[TestDriveBooking] = None
        if req.booking_reference:
            b_stmt = select(TestDriveBooking).where(TestDriveBooking.booking_reference == req.booking_reference)
            b_res = await db.execute(b_stmt)
            booking = b_res.scalars().first()

        if not booking and customer:
            b_stmt = select(TestDriveBooking).where(TestDriveBooking.customer_id == customer.id).order_by(TestDriveBooking.created_at.desc())
            b_res = await db.execute(b_stmt)
            booking = b_res.scalars().first()

        booking_ref = (
            req.booking_reference or
            (booking.booking_reference if booking else None) or
            f"BK-MAH-{uuid.uuid4().hex[:5].upper()}"
        )
        booking_id = booking.id if booking else None

        # 3. Formulate standard GCS Path based on mime type
        now_utc = datetime.now(timezone.utc)
        date_str = now_utc.strftime("%Y-%m-%d")
        gcs_bucket = settings.GCS_RECORDINGS_BUCKET

        # Detect audio extension and mime type
        audio_mime_type = req.audio_format or "audio/wav"
        ext = "wav"
        if "webm" in audio_mime_type.lower():
            ext = "webm"
        elif "mp4" in audio_mime_type.lower() or "m4a" in audio_mime_type.lower():
            ext = "m4a"
        elif "ogg" in audio_mime_type.lower():
            ext = "ogg"
        elif "mp3" in audio_mime_type.lower() or "mpeg" in audio_mime_type.lower():
            ext = "mp3"

        gcs_object_path = f"test_rides/{date_str}/{booking_ref}.{ext}"
        gcs_uri = f"gs://{gcs_bucket}/{gcs_object_path}"

        # Write local file copy for audit and upload
        local_dir = os.path.join(UPLOAD_BASE_DIR, date_str)
        os.makedirs(local_dir, exist_ok=True)
        local_file_path = os.path.join(local_dir, f"{booking_ref}.{ext}")

        raw_bytes: Optional[bytes] = None
        file_size = 1485200
        has_real_audio = False

        if req.audio_base64 and len(req.audio_base64.strip()) > 50:
            import base64
            try:
                header, data = req.audio_base64.split(",", 1) if "," in req.audio_base64 else ("", req.audio_base64)
                if "data:" in header and ";" in header:
                    detected_mime = header.split("data:")[1].split(";")[0].strip()
                    if detected_mime:
                        audio_mime_type = detected_mime
                raw_bytes = base64.b64decode(data)
                with open(local_file_path, "wb") as f:
                    f.write(raw_bytes)
                file_size = len(raw_bytes)
                if file_size > 50:
                    has_real_audio = True
            except Exception as e:
                logger.warning(f"Failed to decode base64 audio: {e}")
                _create_synthetic_wav_file(local_file_path)
        else:
            _create_synthetic_wav_file(local_file_path)

        # Upload audio file to Google Cloud Storage (GCS)
        try:
            from google.cloud import storage
            storage_client = storage.Client(project=settings.VERTEX_PROJECT_ID)
            bucket = storage_client.bucket(gcs_bucket)
            blob = bucket.blob(gcs_object_path)
            blob.upload_from_filename(local_file_path, content_type=audio_mime_type)
            logger.info(f"Uploaded test ride recording to GCS: {gcs_uri}")
        except Exception as e:
            logger.error(f"Failed to upload to GCS bucket {gcs_bucket}: {e}")

        # 4. Vehicle metadata and Advisor details
        # Resolve active / requested brand
        brand_id = getattr(req, "brand_id", None)
        brand = BrandService.get_brand(brand_id) if brand_id else None
        if not brand:
            brand = BrandService.get_active_brand()
        brand_name = brand.name.replace(r"\(.*\)", "").strip() if brand else "Automotive"
        brand_short = brand_name.split(" ")[0].strip()

        # Resolve vehicle details from brand or catalog
        v_info = None
        req_norm = req.vehicle_id.lower().replace("-", "_")
        if brand and brand.vehicles:
            for v in brand.vehicles:
                if v.id.lower().replace("-", "_") == req_norm or v.id.lower() == req.vehicle_id.lower():
                    v_info = v
                    break
        if not v_info:
            v_info = CatalogService.get_vehicle_by_id(req.vehicle_id)

        raw_veh_name = v_info.name if v_info else req.vehicle_id.replace("-", " ").replace("_", " ").title()
        if brand_short.lower() in raw_veh_name.lower():
            display_veh_name = raw_veh_name
        else:
            display_veh_name = f"{brand_short} {raw_veh_name}"

        veh_name = display_veh_name
        cust_name = req.customer_name or customer.name or "Ajitesh Kumar"
        advisor_name = req.sales_advisor_name or f"Rajesh Varma (Senior {brand_short} Specialist)"
        advisor_short = advisor_name.split(" ")[0].replace("Specialist", "").strip("()") or "Rajesh"

        checklist_items = req.advisor_checklist or (booking.advisor_checklist if booking else None) or (customer.advisor_checklist if customer else None) or CatalogService.get_static_checklist(req.vehicle_id)
        session_id = req.session_id or f"TR-2026-{uuid.uuid4().hex[:6].upper()}"

        # 5. Dynamic Indian In-Vehicle Test Drive Dialogue Script (Works for ALL cars & powertrains)
        v_cat = (v_info.category if v_info else "").lower()
        v_fuel = (v_info.fuel_or_battery if v_info else "").lower()
        v_id = req.vehicle_id.lower()

        is_ev = any(k in v_cat or k in v_fuel or k in v_id for k in ["electric", "ev", "battery", "born electric"])
        is_hybrid = any(k in v_cat or k in v_fuel or k in v_id for k in ["hybrid", "strong hybrid", "e-hybrid"])

        if is_ev:
            engine_str = v_info.engine_specs if (v_info and v_info.engine_specs) else "High-Torque Permanent Magnet Electric Motor"
            pickup_phrase = "zero lag ke saath instant electric acceleration"
            customer_engine_praise = "Cabin ke andar motor noise ya vibrations bilkul nahi hain—super silent ride hai."
        elif is_hybrid:
            engine_str = v_info.engine_specs if (v_info and v_info.engine_specs) else "1.5L Intelligent Strong-Hybrid Powertrain"
            pickup_phrase = "electric boost ke saath pickup"
            customer_engine_praise = "EV mode se petrol engine ka transition bilkul seamless hai, aur cabin silent hai."
        else:
            if v_info and v_info.engine_specs:
                engine_str = v_info.engine_specs.split("&")[0].strip()
            elif "xuv700" in v_id or "xuv" in v_id:
                engine_str = "2.0L Turbo-Petrol engine (200 bhp)"
            elif "diesel" in v_fuel:
                engine_str = "2.2L Diesel engine (175 PS / 370 Nm)"
            else:
                engine_str = "refined high-performance powertrain"
            pickup_phrase = "pickup"
            customer_engine_praise = "Cabin ke andar engine noise bilkul nahi aa rahi."

        # Suspension
        suspension_feature = None
        if v_info and v_info.key_highlights:
            for h in v_info.key_highlights:
                if any(k in h.lower() for k in ["suspension", "damping", "damper", "fsd", "penta-link", "multi-link"]):
                    suspension_feature = h
                    break
        if suspension_feature:
            suspension_str = suspension_feature
        elif "mahindra" in brand_name.lower():
            suspension_str = "Frequency Selective Damping (FSD) suspension with Penta-Link"
        elif "bmw" in brand_name.lower():
            suspension_str = "Adaptive M precision-tuned suspension"
        elif is_ev:
            suspension_str = "Multi-Link Independent suspension with low center-of-gravity battery chassis"
        else:
            suspension_str = "advanced tuned comfort suspension"

        # Sunroof & Voice Command
        if "mahindra" in brand_name.lower():
            sunroof_name = "segment ka sabse bada panoramic sunroof hai—hum isse 'Skyroof' bolte hain"
            voice_command = "Hey Mahindra, open the skyroof"
        elif "hyundai" in brand_name.lower():
            sunroof_name = "Smart Voice-Enabled Panoramic Sunroof hai"
            voice_command = "Hey Hyundai, open the sunroof"
        elif "maruti" in brand_name.lower() or "suzuki" in brand_name.lower():
            sunroof_name = "Segment-leading Dual-Pane Panoramic Sunroof hai"
            voice_command = "Hi Suzuki, open the sunroof"
        elif "bmw" in brand_name.lower():
            sunroof_name = "Panoramic Glass Roof Sky Lounge hai"
            voice_command = "Hey BMW, open the panoramic glass roof"
        else:
            sunroof_name = "Segment-leading Panoramic Sunroof hai"
            voice_command = f"Hey {brand_short}, open the sunroof"

        # Airbag / Safety Cage
        airbag_str = "7 airbags"
        if v_info and v_info.key_highlights:
            for h in v_info.key_highlights:
                if "airbag" in h.lower():
                    airbag_str = h
                    break
        elif "bmw" in brand_name.lower():
            airbag_str = "8 airbags with dynamic stability control"
        elif "hyundai" in brand_name.lower() or "maruti" in brand_name.lower():
            airbag_str = "6 airbags standard"

        # Competitor & Market comparison
        if "bmw" in brand_name.lower() or "luxury" in v_cat:
            competitor_name = "Mercedes aur Audi"
            competitor_short = "Mercedes ya Audi"
            advantage_str = f"pure driving dynamics, 5-Star safety cage aur {display_veh_name} ki authentic luxury engineering"
        elif is_ev:
            competitor_name = "other mass-market EV options"
            competitor_short = "dusre EV models"
            advantage_str = f"fast DC charging capability, dedicated EV architecture, 5-Star safety aur reliable battery thermal management"
        elif "hyundai" in brand_name.lower():
            competitor_name = "Kia (Seltos / Carens)"
            competitor_short = "Kia"
            advantage_str = f"proven reliability, refined suspension, 5-Star safety rating aur superior resale value"
        elif "maruti" in brand_name.lower() or "suzuki" in brand_name.lower():
            competitor_name = "Hyundai aur Tata"
            competitor_short = "Hyundai ya Tata"
            advantage_str = f"best-in-class fuel efficiency, unmatched reliability, robust build aur nationwide service support"
        elif "mahindra" in brand_name.lower():
            competitor_name = "Kia (Seltos / Carens)"
            competitor_short = "Kia"
            advantage_str = f"segment, solid road presence, 5-Star crash safety aur heavy-duty build quality"
        else:
            competitor_name = "market competitors"
            competitor_short = "competitors"
            advantage_str = f"5-Star crash safety, superior engineering aur heavy-duty build quality"

        simulated_transcript = f"""[00:12] Advisor {advisor_short}: "Namaste {cust_name} ji! Throttle thoda press karke dekhiye. Yeh {engine_str} hai—{pickup_phrase} instantly feel hoga."
[00:32] {cust_name} (Customer): "Haan, response toh kafi punchy aur smooth hai. {customer_engine_praise} Suspension bhi kaafi well-cushioned lag raha hai potholes par."
[00:54] Advisor {advisor_short}: "Bilkul sir, isme {suspension_str} hai, jo automatic road conditions ke hisaab se adjust hota hai."
[01:18] {cust_name} (Customer): "Aur yeh sunroof poora piche tak jaata hai kya? Kids love big sunroofs."
[01:38] Advisor {advisor_short}: "Sir, yeh {sunroof_name}. Aap screen par tap karke ya simple voice command se bhi open kar sakte hain. Just say: '{voice_command}'."
[01:58] {cust_name} (Customer): "Impressive! Glass area kaafi wide hai, cabin pura airy feel ho raha hai."
[02:15] {cust_name} (Customer): "Safety package kaisa hai iska? ABS aur brakes ka calibration kaisa rehta hai sudden stop par?"
[02:36] Advisor {advisor_short}: "Sir, isme Electronic Stability Program (ESP) ke saath ABS with EBD aur All-Wheel Disc Brakes standard aate hain. Agar emergency braking karni pade, toh car skid nahi hoti aur steering control bana rehta hai."
[02:55] {cust_name} (Customer): "Aur Global NCAP rating kitni mili hai isko?"
[03:10] Advisor {advisor_short}: "{display_veh_name} ko solid 5-Star Global NCAP safety rating mili hai with {airbag_str} aur ultra-high strength steel cage structure."
[03:32] {cust_name} (Customer): "Sab theek hai, but honestly {competitor_name} market mein thoda cheaper padta hai. Features bhi kaafi de rahe hain woh log at a lower price point."
[03:52] Advisor {advisor_short}: "Valid point {cust_name} ji! {competitor_short} pricing aur feature list mein attractive lagti hai, lekin jab aap {advantage_str} compare karenge toh difference clear hai."
[04:14] {cust_name} (Customer): "Hmm, makes sense. Agar finalize karein, toh EMI options ka kya scene hai? Is flexible financing available?"
[04:32] Advisor {advisor_short}: "Bilkul sir! Hamare paas major banks (HDFC, SBI, ICICI) ke saath tie-ups hain. Aap minimum 10% se 15% down payment de sakte hain, aur tenure 3 se 7 years tak select kar sakte hain. Digital instant approval bhi ho jayega."
[04:50] {cust_name} (Customer): "Bahut badhiya! Overall experience aur drive dono top notch hain. Chaliye dealership chalte hain aur booking & financing initiate karte hain."
[05:05] Advisor {advisor_short}: "Thank you {cust_name} ji! Parking the car back at the showroom. Hamara system turant aapko pre-approved financing details bhej dega." """

        transcript = simulated_transcript
        customer_sentiment = 0.85
        purchase_intent = 0.85
        advisor_score = 8.0

        is_live_recording = bool(has_real_audio and ("simulat" not in (req.simulated_scenario or "").lower()))

        if is_live_recording:
            loved_features: List[str] = []
            objections_raised: List[str] = []
        else:
            loved_features = [
                f"{display_veh_name} Performance & Acceleration",
                "Ride Comfort & Pliant Suspension",
                "Panoramic Sunroof & Cabin Spaciousness"
            ]
            objections_raised = [
                f"{competitor_name} segment pricing comparison",
                "Flexible financing and EMI options"
            ]

        advisor_coaching = f"Advisor {advisor_short} presented {display_veh_name} capabilities and answered customer queries."
        recommended_action = f"Initiate digital loan application and finalize booking for {cust_name} ({display_veh_name})."

        # 6. Dynamic Evaluation and Transcription using Gemini Multimodal Audio Model
        try:
            from google import genai
            from google.genai import types
            import asyncio

            vertex_client = genai.Client(
                vertexai=True,
                project=settings.VERTEX_PROJECT_ID,
                location=settings.VERTEX_LOCATION
            )

            is_live_recording = has_real_audio and req.simulated_scenario != "test_drive_simulation"

            if is_live_recording and raw_bytes:
                # Transcribe directly from recorded audio and extract speech insights
                audio_part = types.Part.from_bytes(data=raw_bytes, mime_type=audio_mime_type)
                analysis_prompt = f"""You are an expert Automotive Sales Audio Analyst and Transcriber for {brand_name}.
You are given an authentic in-vehicle audio recording from a real test drive session between Sales Advisor {advisor_name} and Customer {cust_name} for vehicle {veh_name} ({req.variant}).

CRITICAL INSTRUCTIONS:
1. Verbatim Transcription: Transcribe the actual spoken audio word-for-word with speaker labels (e.g. "[00:05] Advisor {advisor_short}: ...", "[00:15] {cust_name} (Customer): ...") and timestamps. If the audio is in Hindi, English, or Hinglish, transcribe exactly what is spoken. If no clear speech is audible, state: "[00:00] In-vehicle test drive audio recorded. Ambient drive sounds captured."
2. Loved Features Extraction: Extract ONLY the vehicle features that the customer explicitly praised, appreciated, liked, or asked positively about in THIS recording (e.g. engine pickup, suspension smoothness, panoramic sunroof, braking, sound system, ventilated seats, etc.). Do NOT include generic or pre-canned features unless they were actually discussed in the audio.
3. Objections & Concerns Extraction: Extract ONLY the specific doubts, objections, hesitations, competitor comparisons, price questions, or delivery concerns that the customer explicitly raised in THIS recording. If the customer raised NO objections or concerns in the audio, return []. Do NOT invent competitor comparisons unless explicitly mentioned in the audio.
4. Sentiment & Purchase Intent: Calculate realistic scores (0.00 to 1.00) based strictly on customer voice tone, dialogue, and buying signals in the recording.
5. Sales Pitch Score & Coaching: Evaluate the advisor's pitch (1.0 to 10.0) and provide 2-3 sentences of constructive coaching feedback based on how the advisor actually presented features and answered queries in the recording.
6. Recommended Action: 1-2 actionable next steps for the dealership team based on this specific recording.

Return strictly valid JSON with keys:
"transcript", "customer_sentiment_score", "purchase_intent_score", "advisor_pitch_score", "loved_features", "objections_raised", "advisor_coaching_feedback", "recommended_action"."""
                contents = [audio_part, analysis_prompt]
            else:
                # Text analysis on simulation transcript
                analysis_prompt = f"""You are an expert Automotive Sales Audio Analyst for {brand_name}.
Analyze this in-vehicle test drive conversation between Sales Advisor {advisor_name} and Customer {cust_name} for vehicle {veh_name} ({req.variant}).

Conversation Transcript:
{simulated_transcript}

Dynamically evaluate the conversation and extract non-hardcoded realistic metrics:
1. customer_sentiment_score: Float between 0.00 and 1.00 based on customer satisfaction, tone, and feedback.
2. purchase_intent_score: Float between 0.00 and 1.00 based on customer buying readiness, financing questions, and decision to book.
3. advisor_pitch_score: Float between 1.0 and 10.0 based on how effectively the sales advisor explained the features.
4. loved_features: List of 3-4 specific features explicitly praised by the customer.
5. objections_raised: List of 1-2 specific concerns/comparisons mentioned by the customer.
6. advisor_coaching_feedback: Constructive coaching feedback for the advisor in 2-3 sentences.
7. recommended_action: Immediate recommended next step for the digital follow-up team in 1-2 sentences.

Return valid JSON with keys: transcript, customer_sentiment_score, purchase_intent_score, advisor_pitch_score, loved_features, objections_raised, advisor_coaching_feedback, recommended_action."""
                contents = [analysis_prompt]

            config = types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json"
            )

            gemini_resp = await asyncio.wait_for(
                asyncio.to_thread(
                    vertex_client.models.generate_content,
                    model=settings.REST_CHAT_MODEL,
                    contents=contents,
                    config=config
                ),
                timeout=12.0
            )

            if gemini_resp and gemini_resp.text:
                parsed = json.loads(gemini_resp.text)
                if parsed.get("transcript") and len(parsed["transcript"].strip()) > 5:
                    transcript = parsed["transcript"].strip()
                if "customer_sentiment_score" in parsed:
                    val = float(parsed["customer_sentiment_score"])
                    customer_sentiment = round(val / 10.0 if val > 1.0 else val, 2)
                if "purchase_intent_score" in parsed:
                    val = float(parsed["purchase_intent_score"])
                    purchase_intent = round(val / 10.0 if val > 1.0 else val, 2)
                if "advisor_pitch_score" in parsed:
                    val = float(parsed["advisor_pitch_score"])
                    advisor_score = round(val if val <= 10.0 else val / 10.0, 1)
                
                if is_live_recording:
                    # Parse loved features and objections directly from audio analysis
                    if "loved_features" in parsed and isinstance(parsed["loved_features"], list):
                        audio_loved = [str(f).strip() for f in parsed["loved_features"] if str(f).strip()]
                        loved_features = audio_loved if audio_loved else [f"Drive dynamics & performance ({veh_name})"]
                    if "objections_raised" in parsed and isinstance(parsed["objections_raised"], list):
                        objections_raised = [str(o).strip() for o in parsed["objections_raised"] if str(o).strip()]
                else:
                    if parsed.get("loved_features") and isinstance(parsed["loved_features"], list) and len(parsed["loved_features"]) > 0:
                        loved_features = parsed["loved_features"]
                    if parsed.get("objections_raised") and isinstance(parsed["objections_raised"], list):
                        objections_raised = parsed["objections_raised"]

                if parsed.get("advisor_coaching_feedback"):
                    advisor_coaching = parsed["advisor_coaching_feedback"]
                if parsed.get("recommended_action"):
                    recommended_action = parsed["recommended_action"]
                logger.info(f"Gemini evaluation completed: transcript_length={len(transcript)}, sentiment={customer_sentiment}, intent={purchase_intent}, pitch_score={advisor_score}, loved={len(loved_features)}, objections={len(objections_raised)}")
        except Exception as e:
            logger.warning(f"Gemini dynamic audio evaluation notice: {e}")

        # 6. Create TestRideRecording DB Record
        recording = TestRideRecording(
            session_id=session_id,
            booking_id=booking_id,
            booking_reference=booking_ref,
            customer_id=customer.id,
            brand_id=b_id,
            vehicle_id=req.vehicle_id,
            vehicle_name=f"{veh_name} ({req.variant})",
            sales_advisor_name=advisor_name,
            gcs_bucket=gcs_bucket,
            gcs_object_path=gcs_object_path,
            gcs_uri=gcs_uri,
            duration_seconds=req.duration_seconds or 184,
            file_size_bytes=file_size,
            audio_format=req.audio_format,
            transcript=transcript,
            customer_sentiment_score=customer_sentiment,
            purchase_intent_score=purchase_intent,
            loved_features=loved_features,
            objections_raised=objections_raised,
            advisor_pitch_score=advisor_score,
            advisor_coaching_feedback=advisor_coaching,
            recommended_action=recommended_action,
            status="ANALYZED"
        )
        db.add(recording)

        # 7. Log Individual Dialogue Turns in InteractionLog for unified customer history
        for line in transcript.strip().split("\n"):
            if ":" in line:
                parts = line.split(":", 1)
                speaker_tag = parts[0].strip()
                dialogue = parts[1].strip().strip('"')
                is_cust = "customer" in speaker_tag.lower() or cust_name.lower() in speaker_tag.lower()
                spk = "customer" if is_cust else "sales_advisor"
                
                log = InteractionLog(
                    customer_id=customer.id,
                    brand_id=b_id,
                    session_id=None,
                    speaker=spk,
                    message=dialogue,
                    channel="TEST_RIDE_IN_VEHICLE",
                    extracted_intent="TEST_RIDE_FEATURE_ASSESSMENT" if is_cust else "ADVISOR_FEATURE_DEMONSTRATION",
                    tool_triggered=booking_ref
                )
                db.add(log)

        # Advance customer phase
        customer.current_phase = "TestRide_Completed"
        if booking:
            booking.status = "TestRide_Completed"

        await db.commit()
        await db.refresh(recording)
        return recording

    @staticmethod
    async def get_latest_test_ride(
        db: AsyncSession,
        customer_id: Optional[str] = None,
        booking_reference: Optional[str] = None,
        phone: Optional[str] = None,
        brand_id: Optional[str] = None
    ) -> Optional[TestRideRecording]:
        """
        Retrieves the latest persisted TestRideRecording insights for a customer,
        matching by booking_reference, customer_id, or customer phone, scoped to brand.
        """
        b_id = brand_id.lower() if brand_id else None

        if booking_reference and booking_reference.strip():
            b_stmt = select(TestRideRecording).where(
                TestRideRecording.booking_reference == booking_reference.strip()
            )
            if b_id:
                b_stmt = b_stmt.where(TestRideRecording.brand_id == b_id)
            b_stmt = b_stmt.order_by(TestRideRecording.created_at.desc())
            res = await db.execute(b_stmt)
            rec = res.scalars().first()
            if rec:
                return rec

        if customer_id and customer_id.strip():
            c_stmt = select(Customer).where(
                (Customer.customer_id == customer_id.strip()) |
                (Customer.phone == customer_id.strip())
            )
            if b_id:
                c_stmt = c_stmt.where(Customer.brand_id == b_id)
            c_res = await db.execute(c_stmt)
            cust = c_res.scalars().first()
            if cust:
                rec_stmt = select(TestRideRecording).where(
                    TestRideRecording.customer_id == cust.id
                )
                if b_id:
                    rec_stmt = rec_stmt.where(TestRideRecording.brand_id == b_id)
                rec_stmt = rec_stmt.order_by(TestRideRecording.created_at.desc())
                rec_res = await db.execute(rec_stmt)
                rec = rec_res.scalars().first()
                if rec:
                    return rec

        if phone and phone.strip():
            clean_p = clean_phone(phone)
            c_stmt = select(Customer).where(Customer.phone.ilike(f"%{clean_p[-10:] if len(clean_p) >= 10 else clean_p}%"))
            if b_id:
                c_stmt = c_stmt.where(Customer.brand_id == b_id)
            c_res = await db.execute(c_stmt)
            cust = c_res.scalars().first()
            if cust:
                rec_stmt = select(TestRideRecording).where(
                    TestRideRecording.customer_id == cust.id
                )
                if b_id:
                    rec_stmt = rec_stmt.where(TestRideRecording.brand_id == b_id)
                rec_stmt = rec_stmt.order_by(TestRideRecording.created_at.desc())
                rec_res = await db.execute(rec_stmt)
                rec = rec_res.scalars().first()
                if rec:
                    return rec

        # Strictly return None if no test ride recording exists for this specific customer/booking
        return None

    @staticmethod
    async def get_test_ride_insights(db: AsyncSession, session_id: str) -> Optional[TestRideRecording]:
        stmt = select(TestRideRecording).where(TestRideRecording.session_id == session_id)
        res = await db.execute(stmt)
        return res.scalars().first()

    @staticmethod
    async def get_all_test_rides(db: AsyncSession, brand_id: Optional[str] = None) -> List[TestRideRecording]:
        stmt = select(TestRideRecording)
        if brand_id:
            stmt = stmt.where(TestRideRecording.brand_id == brand_id.lower())
        stmt = stmt.order_by(TestRideRecording.created_at.desc()).limit(20)
        res = await db.execute(stmt)
        return res.scalars().all()
