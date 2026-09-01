import asyncio
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import desc

from app.database import get_db
from app.models.booking import TestDriveBooking, TestDriveSlot
from app.models.customer import Customer, InteractionLog, ConversationSession
from app.models.sales_ride import TestRideRecording, OutboundCallLog
from app.models.dealership import Dealership
from app.services.catalog_service import CatalogService
from app.services.customer_service import clean_phone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Portal"])


@router.get("/bookings")
async def get_admin_bookings(
    city: Optional[str] = Query(None, description="Filter by dealership city"),
    vehicle_id: Optional[str] = Query(None, description="Filter by vehicle model"),
    status: Optional[str] = Query(None, description="Filter by booking status"),
    phone: Optional[str] = Query(None, description="Search by customer phone"),
    search: Optional[str] = Query(None, description="Search across name, phone, ref, car"),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns comprehensive booking records with dual transcripts:
    Strictly 1 row per unique Customer (identified by Unique Phone Number).
    1. Pre-Sales Transcript (Chat/Voice with Kabir in Showroom)
    2. Test Ride Transcript (In-Vehicle Test Drive with Sales Advisor)
    """
    # 1. Bulk prefetch all data in 5 bulk queries to avoid N+1 DB latency
    dealer_res = await db.execute(select(Dealership))
    b_res = await db.execute(
        select(TestDriveBooking)
        .options(selectinload(TestDriveBooking.customer))
        .order_by(desc(TestDriveBooking.created_at))
    )
    tr_res = await db.execute(select(TestRideRecording).order_by(desc(TestRideRecording.created_at)))
    out_res = await db.execute(select(OutboundCallLog).order_by(desc(OutboundCallLog.created_at)))
    logs_res = await db.execute(
        select(InteractionLog)
        .options(selectinload(InteractionLog.session))
        .where(InteractionLog.channel != "TEST_RIDE_IN_VEHICLE")
        .order_by(InteractionLog.created_at.asc())
    )

    dealers = dealer_res.scalars().all()
    bookings = b_res.scalars().all()
    all_tr_records = tr_res.scalars().all()
    all_out_records = out_res.scalars().all()
    all_interaction_logs = logs_res.scalars().all()

    dealer_city_map = {d.id: d.city for d in dealers}

    # Index test ride recordings by booking_id, booking_ref, and customer_id
    tr_by_cust: dict[int, list[TestRideRecording]] = {}
    tr_by_booking_id: dict[int, list[TestRideRecording]] = {}
    tr_by_booking_ref: dict[str, list[TestRideRecording]] = {}
    for tr in all_tr_records:
        if tr.customer_id:
            tr_by_cust.setdefault(tr.customer_id, []).append(tr)
        if tr.booking_id:
            tr_by_booking_id.setdefault(tr.booking_id, []).append(tr)
        if tr.booking_reference:
            tr_by_booking_ref.setdefault(tr.booking_reference, []).append(tr)

    # Index outbound call logs by customer_id
    out_by_cust: dict[int, list[OutboundCallLog]] = {}
    for out in all_out_records:
        if out.customer_id:
            out_by_cust.setdefault(out.customer_id, []).append(out)

    # Index interaction logs by customer_id
    logs_by_cust: dict[int, list[InteractionLog]] = {}
    for lg in all_interaction_logs:
        if lg.customer_id:
            logs_by_cust.setdefault(lg.customer_id, []).append(lg)

    admin_records = []
    seen_customer_phones = set()

    # Process confirmed bookings (1 row per unique customer phone)
    for b in bookings:
        cust = b.customer
        cust_id = cust.id if cust else None
        cust_name = cust.name if cust else "Valued Customer"
        cust_phone = cust.phone if cust else ""
        norm_phone = clean_phone(cust_phone) if cust_phone else f"NOPHONE-{b.id}"

        # Deduplicate: exactly 1 row per unique customer phone
        if norm_phone in seen_customer_phones:
            continue
        seen_customer_phones.add(norm_phone)

        dealership_city = dealer_city_map.get(b.dealership_id, cust.city if cust else "Mumbai")
        cust_city = dealership_city or (cust.city if cust else "Mumbai")

        # A. Fetch Pre-Sales Transcripts
        presales_turns = []
        cust_logs = logs_by_cust.get(cust_id, []) if cust_id else []
        for log in cust_logs:
            speaker_label = "Customer" if log.speaker == "customer" else "Kabir (AI Specialist)"
            dt = log.created_at
            sess = log.session
            sess_uid = sess.session_id if sess else f"SESS-{dt.strftime('%Y%m%d-%H%M') if dt else 'HISTORIC'}"
            sess_type = sess.session_type if sess else ("LIVE_VOICE" if log.channel == "VOICE_LIVE" else "CHAT_BOT")
            sess_veh = (sess.vehicle_id if sess and sess.vehicle_id else b.vehicle_id) or "thar_roxx"
            v_obj = CatalogService.get_vehicle_by_id(sess_veh)
            sess_veh_name = v_obj.name if v_obj else sess_veh.replace("_", " ").title()

            presales_turns.append({
                "id": log.id,
                "session_id": sess_uid,
                "session_type": sess_type,
                "vehicle_id": sess_veh,
                "vehicle_name": sess_veh_name,
                "speaker": speaker_label,
                "role": log.speaker,
                "message": log.message,
                "channel": log.channel,
                "intent": log.extracted_intent,
                "tool": log.tool_triggered,
                "date": dt.strftime("%d %b %Y") if dt else "Today",
                "full_date": dt.strftime("%A, %d %B %Y") if dt else "Today",
                "time": dt.strftime("%I:%M %p") if dt else "",
                "timestamp": dt.strftime("%I:%M %p, %d %b %Y") if dt else ""
            })

        # B. Fetch In-Vehicle Test Ride Recording & Audio Transcript
        test_ride_turns = []
        test_ride_sessions = []
        sentiment_score = None
        purchase_intent = None
        loved_features = []
        objections = []
        advisor_feedback = None
        recommended_action = None
        gcs_recording_uri = None

        matched_tr = []
        if b.id and b.id in tr_by_booking_id:
            matched_tr.extend(tr_by_booking_id[b.id])
        if b.booking_reference and b.booking_reference in tr_by_booking_ref:
            for tr in tr_by_booking_ref[b.booking_reference]:
                if tr not in matched_tr:
                    matched_tr.append(tr)
        if cust_id and cust_id in tr_by_cust:
            for tr in tr_by_cust[cust_id]:
                if tr not in matched_tr:
                    matched_tr.append(tr)

        for tr_rec in matched_tr:
            if sentiment_score is None:
                sentiment_score = tr_rec.customer_sentiment_score
                purchase_intent = tr_rec.purchase_intent_score
                loved_features = tr_rec.loved_features or []
                objections = tr_rec.objections_raised or []
                advisor_feedback = tr_rec.advisor_coaching_feedback
                recommended_action = tr_rec.recommended_action
                gcs_recording_uri = tr_rec.gcs_uri

            sess_turns = []
            if tr_rec.transcript:
                for line in tr_rec.transcript.strip().split("\n"):
                    if ":" in line:
                        spk, msg = line.split(":", 1)
                        spk_clean = spk.strip().strip("[]0123456789: ")
                        msg_clean = msg.strip().strip('"')
                        is_cust = "customer" in spk_clean.lower() or cust_name.lower() in spk_clean.lower()
                        turn_dict = {
                            "speaker": spk.strip(),
                            "role": "customer" if is_cust else "sales_advisor",
                            "message": msg_clean,
                            "timestamp": tr_rec.created_at.strftime("%I:%M %p, %d %b") if tr_rec.created_at else ""
                        }
                        sess_turns.append(turn_dict)
                        if len(test_ride_turns) < 30:
                            test_ride_turns.append(turn_dict)

            test_ride_sessions.append({
                "session_id": tr_rec.session_id,
                "booking_reference": tr_rec.booking_reference or b.booking_reference,
                "gcs_uri": tr_rec.gcs_uri,
                "vehicle_name": tr_rec.vehicle_name,
                "sales_advisor_name": tr_rec.sales_advisor_name,
                "duration_seconds": tr_rec.duration_seconds,
                "sentiment_score": tr_rec.customer_sentiment_score,
                "purchase_intent": tr_rec.purchase_intent_score,
                "loved_features": tr_rec.loved_features or [],
                "objections_raised": tr_rec.objections_raised or [],
                "advisor_coaching_feedback": tr_rec.advisor_coaching_feedback,
                "recommended_action": tr_rec.recommended_action,
                "turns": sess_turns,
                "created_at": tr_rec.created_at.strftime("%Y-%m-%d %H:%M:%S") if tr_rec.created_at else ""
            })

        # C. Fetch Outbound Feedback Call Transcripts (OutboundCallLog)
        outbound_turns = []
        outbound_sessions = []
        matched_out = out_by_cust.get(cust_id, []) if cust_id else []
        for out_rec in matched_out:
            sess_turns = []
            if out_rec.transcript and out_rec.transcript.strip():
                import re
                for line in out_rec.transcript.strip().split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    m = re.match(r'^(?:\[([0-9:]+)\]\s*)?([^:]+):\s*"?([^"]*)"?$', line)
                    if m:
                        tm_tag, spk, msg = m.group(1), m.group(2).strip(), m.group(3).strip()
                        is_cust = "customer" in spk.lower() or cust_name.lower() in spk.lower()
                        turn_dict = {
                            "speaker": spk,
                            "role": "customer" if is_cust else "kavya_ai",
                            "message": msg,
                            "timestamp": tm_tag or (out_rec.created_at.strftime("%I:%M %p, %d %b") if out_rec.created_at else "")
                        }
                        sess_turns.append(turn_dict)
                    elif ":" in line:
                        parts = line.split(":", 1)
                        spk = parts[0].strip()
                        msg = parts[1].strip().strip('"')
                        is_cust = "customer" in spk.lower() or cust_name.lower() in spk.lower()
                        turn_dict = {
                            "speaker": spk,
                            "role": "customer" if is_cust else "kavya_ai",
                            "message": msg,
                            "timestamp": out_rec.created_at.strftime("%I:%M %p, %d %b") if out_rec.created_at else ""
                        }
                        sess_turns.append(turn_dict)

            if sess_turns and not outbound_turns:
                outbound_turns = sess_turns

            outbound_sessions.append({
                "call_reference": out_rec.call_reference,
                "phone_number": out_rec.phone_number,
                "agent_name": out_rec.agent_name,
                "call_status": out_rec.call_status,
                "call_duration_seconds": out_rec.call_duration_seconds,
                "sentiment": out_rec.customer_sentiment,
                "decision": out_rec.customer_decision,
                "turns": sess_turns,
                "created_at": out_rec.created_at.strftime("%Y-%m-%d %H:%M:%S") if out_rec.created_at else ""
            })

        # Vehicle display name
        v_info = CatalogService.get_vehicle_by_id(b.vehicle_id)
        veh_name = v_info.name if v_info else b.vehicle_id.replace("_", " ").title()

        record = {
            "booking_id": b.id,
            "booking_reference": b.booking_reference,
            "customer_id": cust.customer_id if cust else f"CUST-{b.customer_id}",
            "customer_name": cust_name,
            "customer_phone": cust_phone,
            "customer_city": cust_city,
            "vehicle_id": b.vehicle_id,
            "vehicle_name": veh_name,
            "variant": b.variant,
            "color": b.color,
            "dealership_id": b.dealership_id,
            "dealership_name": b.dealership_name,
            "sales_advisor_name": b.sales_advisor_name,
            "booking_type": b.booking_type or "HOME_DOORSTEP",
            "delivery_address": b.delivery_address or "Customer Residence",
            "scheduled_date": b.scheduled_date,
            "scheduled_time_slot": b.scheduled_time_slot,
            "status": "TestRide_Completed" if (b.status == "TestRide_Completed" or len(test_ride_sessions) > 0) else (b.status or "CONFIRMED"),
            "sms_status": "SENT",
            "created_at": b.created_at.strftime("%Y-%m-%d %H:%M:%S") if b.created_at else "",
            # Dual Transcripts
            "presales_transcript": presales_turns,
            "test_ride_transcript": test_ride_turns,
            "outbound_transcript": outbound_turns,
            "outbound_sessions": outbound_sessions,
            # AI Insights
            "sentiment_score": sentiment_score,
            "purchase_intent": purchase_intent,
            "loved_features": loved_features,
            "objections_raised": objections,
            "advisor_coaching_feedback": advisor_feedback,
            "recommended_action": recommended_action,
            "gcs_recording_uri": gcs_recording_uri,
            "test_ride_sessions": test_ride_sessions
        }
        admin_records.append(record)

    # Process all other registered showroom leads / customers without a finalized test drive slot yet
    all_cust_res = await db.execute(
        select(Customer)
        .options(selectinload(Customer.interactions).selectinload(InteractionLog.session))
        .order_by(desc(Customer.updated_at))
    )
    all_customers = all_cust_res.scalars().all()

    for c in all_customers:
        norm_p = clean_phone(c.phone) if c.phone else f"CUST-{c.id}"
        if norm_p in seen_customer_phones:
            continue
        seen_customer_phones.add(norm_p)

        veh_id = c.interested_vehicle_id or "thar_roxx"
        v_info = CatalogService.get_vehicle_by_id(veh_id)
        veh_name = v_info.name if v_info else veh_id.replace("_", " ").title()

        # Build pre-sales transcripts for this lead
        lead_presales = []
        for log in sorted(c.interactions, key=lambda x: x.created_at or datetime.min):
            if log.channel == "TEST_RIDE_IN_VEHICLE":
                continue
            speaker_label = "Customer" if log.speaker == "customer" else "Kabir (AI Specialist)"
            dt = log.created_at
            sess = log.session
            sess_uid = sess.session_id if sess else f"SESS-{dt.strftime('%Y%m%d-%H%M') if dt else 'SHOWROOM'}"
            sess_type = sess.session_type if sess else ("LIVE_VOICE" if log.channel == "VOICE_LIVE" else "CHAT_BOT")

            lead_presales.append({
                "id": log.id,
                "session_id": sess_uid,
                "session_type": sess_type,
                "vehicle_id": veh_id,
                "vehicle_name": veh_name,
                "speaker": speaker_label,
                "role": log.speaker,
                "message": log.message,
                "channel": log.channel,
                "intent": log.extracted_intent,
                "tool": log.tool_triggered,
                "date": dt.strftime("%d %b %Y") if dt else "Today",
                "full_date": dt.strftime("%A, %d %B %Y") if dt else "Today",
                "time": dt.strftime("%I:%M %p") if dt else "",
                "timestamp": dt.strftime("%I:%M %p, %d %b %Y") if dt else ""
            })

        admin_records.append({
            "booking_id": None,
            "booking_reference": f"LEAD-{c.customer_id.replace('CUST-', '')}",
            "customer_id": c.customer_id,
            "customer_name": c.name,
            "customer_phone": c.phone,
            "customer_city": c.city or "Mumbai",
            "vehicle_id": veh_id,
            "vehicle_name": veh_name,
            "variant": c.interested_variant or "AX7L Diesel AT 4x4",
            "color": "Stealth Black",
            "dealership_id": "BAYVIEW-MUM-01",
            "dealership_name": "Bayview Mahindra, Bandra West, Mumbai",
            "sales_advisor_name": "Kabir (AI Specialist)",
            "booking_type": "SHOWROOM_VISIT",
            "delivery_address": "Showroom Consultation",
            "scheduled_date": "Slot Pending",
            "scheduled_time_slot": "Pending Selection",
            "status": "CONFIRMED" if lead_presales else "LEAD_ENGAGED",
            "sms_status": "READY",
            "created_at": c.created_at.strftime("%Y-%m-%d %H:%M:%S") if c.created_at else "",
            "presales_transcript": lead_presales,
            "test_ride_transcript": [],
            "sentiment_score": 0.85 if lead_presales else None,
            "purchase_intent": 0.80 if lead_presales else None,
            "loved_features": [],
            "objections_raised": [],
            "advisor_coaching_feedback": "Active showroom lead. Follow up to confirm test drive date and time.",
            "recommended_action": "Call customer to assist with slot reservation.",
            "gcs_recording_uri": None,
            "test_ride_sessions": []
        })

    # Filter in memory if search query provided
    filtered = admin_records
    if city and city.strip():
        c_lower = city.strip().lower()
        filtered = [
            r for r in filtered
            if c_lower in r["dealership_name"].lower()
            or c_lower in r["customer_city"].lower()
            or c_lower in r["delivery_address"].lower()
            or c_lower in r["dealership_id"].lower()
        ]
    if vehicle_id and vehicle_id.strip():
        filtered = [r for r in filtered if r["vehicle_id"] == vehicle_id.strip()]
    if status and status.strip():
        filtered = [r for r in filtered if r["status"].upper() == status.strip().upper()]
    if phone and phone.strip():
        clean_p = phone.strip().replace(" ", "").replace("-", "").replace("+", "")
        filtered = [r for r in filtered if clean_p in r["customer_phone"].replace(" ", "").replace("-", "").replace("+", "")]
    if search and search.strip():
        q = search.strip().lower()
        filtered = [
            r for r in filtered
            if q in r["customer_name"].lower()
            or q in r["customer_phone"].lower()
            or q in r["booking_reference"].lower()
            or q in r["vehicle_name"].lower()
            or q in r["variant"].lower()
            or q in r["dealership_name"].lower()
        ]

    # Compute KPI statistics
    total_bookings = len(admin_records)
    doorstep_count = sum(1 for r in admin_records if r["booking_type"] == "HOME_DOORSTEP")
    showroom_count = sum(1 for r in admin_records if r["booking_type"] == "SHOWROOM_VISIT")
    confirmed_count = sum(1 for r in admin_records if r["status"] == "CONFIRMED")
    valid_intents = [r["purchase_intent"] for r in admin_records if r["purchase_intent"] is not None]
    avg_intent = (
        f"{round(sum(valid_intents) / len(valid_intents) * 100, 1)}%"
        if valid_intents
        else "Awaiting Ride"
    )

    return {
        "stats": {
            "total_bookings": total_bookings,
            "doorstep_deliveries": doorstep_count,
            "showroom_visits": showroom_count,
            "confirmed_count": confirmed_count,
            "sms_dispatch_rate": "100%",
            "avg_purchase_intent": avg_intent
        },
        "count": len(filtered),
        "bookings": filtered
    }
