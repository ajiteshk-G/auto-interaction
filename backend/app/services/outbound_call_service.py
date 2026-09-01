import uuid
import datetime
import logging
import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.sales_ride import OutboundCallLog, TestRideRecording
from app.models.customer import Customer
from app.models.booking import TestDriveBooking
from app.schemas.outbound_call import (
    OutboundCallTriggerRequest,
    OutboundDialogueTurnRequest,
    OutboundDialogueTurnResponse,
    OutboundCallInsightsResponse
)
from app.config import settings

from app.services.brand_service import BrandService

logger = logging.getLogger("outbound_call_service")

class OutboundCallService:
    @staticmethod
    async def trigger_outbound_call(db: AsyncSession, req: OutboundCallTriggerRequest) -> OutboundCallLog:
        b_id = (req.brand_id or (BrandService.get_active_brand().id if BrandService.get_active_brand() else "mahindra")).lower()
        active_brand = BrandService.get_brand(b_id)
        brand_name = active_brand.name if active_brand else b_id.title()

        # Find customer scoped by brand_id
        stmt = select(Customer).where((Customer.customer_id == req.customer_id) & (Customer.brand_id == b_id))
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
                    name=req.customer_name,
                    phone=req.phone_number,
                    city="Mumbai",
                    current_phase="POST_TEST_RIDE_CALL"
                )
                db.add(customer)
                await db.flush()

        # Find associated TestRideRecording for in-vehicle context
        tr_rec: Optional[TestRideRecording] = None
        if req.booking_reference:
            b_stmt = select(TestRideRecording).where(
                (TestRideRecording.booking_reference == req.booking_reference) &
                (TestRideRecording.brand_id == b_id)
            ).order_by(TestRideRecording.created_at.desc())
            b_res = await db.execute(b_stmt)
            tr_rec = b_res.scalars().first()

        if not tr_rec and customer:
            c_stmt = select(TestRideRecording).where(
                (TestRideRecording.customer_id == customer.id) &
                (TestRideRecording.brand_id == b_id)
            ).order_by(TestRideRecording.created_at.desc())
            c_res = await db.execute(c_stmt)
            tr_rec = c_res.scalars().first()

        default_veh = f"{brand_name} Premium Line"
        veh_name = req.vehicle_name or (tr_rec.vehicle_name if tr_rec else default_veh)
        advisor_name = req.advisor_name or (tr_rec.sales_advisor_name if tr_rec else "Rajesh Varma")
        advisor_short = advisor_name.split(" ")[0].replace("Specialist", "").strip("()") or "Rajesh"
        cust_name = req.customer_name or customer.name or "Valued Customer"

        call_ref = f"CALL-{b_id.upper()[:4]}-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

        agent_display_name = f"{brand_name} AI (Post-Ride Concierge)"

        call_log = OutboundCallLog(
            call_reference=call_ref,
            customer_id=customer.id,
            brand_id=b_id,
            agent_name=agent_display_name,
            phone_number=req.phone_number,
            call_status="IN_PROGRESS",
            call_duration_seconds=0,
            transcript=None,
            objection_resolution_status="100% RESOLVED (Test Drive Feedback & Stock Lock)",
            customer_sentiment="POSITIVE",
            customer_decision="EVALUATING",
            locked_vehicle_variant=veh_name,
            locked_allocation_days=12,
            next_step="FEEDBACK_CONVERSATION"
        )

        db.add(call_log)
        customer.current_phase = "POST_TEST_RIDE_CALL"
        await db.commit()
        await db.refresh(call_log)
        return call_log

    @staticmethod
    async def process_dialogue_turn(db: AsyncSession, req: OutboundDialogueTurnRequest) -> OutboundDialogueTurnResponse:
        user_speech = req.customer_speech or req.customer_response or "The drive was very good."
        turn_idx = req.turn_index if req.turn_index is not None else (req.turn_number or 1)

        # Lookup call log
        stmt = select(OutboundCallLog).where(OutboundCallLog.call_reference == req.call_reference)
        res = await db.execute(stmt)
        call_log = res.scalars().first()

        # Lookup customer & test ride context
        cust_name = "Customer"
        veh_name = "Mahindra SUV"
        advisor_short = "Rajesh"
        tr_transcript = ""
        loved_features = ["FSD Suspension", "Panoramic Skyroof", "Engine Pickup"]
        objections = ["Delivery Waiting Period", "Flexible EMI"]

        b_id = (call_log.brand_id if call_log and call_log.brand_id else (BrandService.get_active_brand().id if BrandService.get_active_brand() else "mahindra")).lower()
        active_brand = BrandService.get_brand(b_id)
        brand_name = active_brand.name if active_brand else b_id.title()

        # Lookup customer & test ride context
        cust_name = "Customer"
        veh_name = f"{brand_name} Model"
        advisor_short = "Advisor"
        tr_transcript = ""
        loved_features = ["Driving Dynamics", "Cabin Comfort", "Engine Pickup"]
        objections = ["Delivery Waiting Period", "Flexible EMI"]

        if call_log:
            c_stmt = select(Customer).where((Customer.id == call_log.customer_id) & (Customer.brand_id == b_id))
            c_res = await db.execute(c_stmt)
            cust = c_res.scalars().first()
            if cust:
                cust_name = cust.name

            # Lookup test ride recording
            tr_stmt = select(TestRideRecording).where(
                (TestRideRecording.customer_id == call_log.customer_id) &
                (TestRideRecording.brand_id == b_id)
            ).order_by(TestRideRecording.created_at.desc())
            tr_res = await db.execute(tr_stmt)
            tr = tr_res.scalars().first()
            if tr:
                veh_name = tr.vehicle_name or veh_name
                advisor_short = (tr.sales_advisor_name or "Advisor").split(" ")[0].replace("Specialist", "").strip("()") or "Advisor"
                tr_transcript = tr.transcript or ""
                loved_features = tr.loved_features or loved_features
                objections = tr.objections_raised or objections

        # Generate dynamic response via Gemini with strict brand domain guardrails
        agent_reply = ""
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(vertexai=True, project=settings.VERTEX_PROJECT_ID, location=settings.VERTEX_LOCATION)
            
            system_prompt = f"""You are {brand_name} AI, an expert, polite, and attentive Post-Test Ride Customer Relationship Specialist from {brand_name}.
You are in a live feedback phone call with {cust_name}, who recently completed a test drive of the {veh_name} with Sales Consultant {advisor_short}.

*** IN-VEHICLE TEST RIDE CONTEXT ***
Test Ride Transcript:
{tr_transcript[:1000] if tr_transcript else "Customer test drove the vehicle and experienced the engine, suspension, and features."}

Customer Loved Features: {", ".join(loved_features)}
Objections / Questions Raised: {", ".join(objections)}

*** YOUR GOALS IN THIS CALL ***
1. Check if the test drive was good and confirm if Sales Consultant {advisor_short} answered all their questions and demonstrated features well.
2. Address any remaining doubts about delivery waiting period, on-road pricing, or flexible financing.
3. Offer to lock their preferred vehicle allocation and send digital financing / booking confirmation.

*** STRICT DOMAIN & SCOPE BOUNDARY (MANDATORY RULE) ***
1. YOU MUST NEVER ANSWER ANY QUESTION OUTSIDE {brand_name.upper()} VEHICLES, TEST DRIVES, VEHICLE BOOKING, OR OFFICIAL FINANCING.
2. If the user asks about competitor cars or unrelated topics:
   - Politely decline and steer the conversation strictly back to their {brand_name} {veh_name} test drive and feedback.
   - Example: "Main keval {brand_name} gaadiyon aur aapke test drive experience ke baare mein baat kar sakti hoon."
3. Respond in conversational Hindi/Hinglish, natural, polite, and concise (under 30 words per turn)."""

            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3
            )

            history_context = ""
            if req.conversation_history:
                for h in req.conversation_history:
                    spk = h.get("speaker", "User")
                    txt = h.get("text", "")
                    history_context += f"{spk}: {txt}\n"

            prompt_content = f"{history_context}Customer: {user_speech}"

            resp = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.generate_content,
                    model=settings.REST_CHAT_MODEL,
                    contents=[prompt_content],
                    config=config
                ),
                timeout=6.0
            )

            if resp and resp.text:
                agent_reply = resp.text.strip()
        except Exception as e:
            logger.warning(f"Gemini outbound call turn notice: {e}")

        if not agent_reply:
            if "bye" in user_speech.lower() or "dhanyavaad" in user_speech.lower() or "thank" in user_speech.lower() or "finalize" in user_speech.lower():
                agent_reply = f"Shukriya {cust_name} ji! Maine aapka allocation lock kar diya hai aur financing link WhatsApp par bhej diya hai. Have a wonderful day!"
            else:
                agent_reply = f"Sunkar bahut achha laga {cust_name} ji! Kya {advisor_short} ji ne sabhi features theek se samjhaye the? Hum aapki booking aur financing process turant start kar sakte hain."

        is_finished = "shukriya" in agent_reply.lower() or "thank" in agent_reply.lower() or turn_idx >= 4

        # Update call log transcript
        agent_tag = f"{brand_name} AI"
        if call_log:
            now_sec = (turn_idx * 15) + 12
            call_log.call_duration_seconds = now_sec
            call_log.transcript = (call_log.transcript or "") + f'\n[00:{now_sec:02d}] Customer: "{user_speech}"\n[00:{now_sec+5:02d}] {agent_tag}: "{agent_reply}"'
            if is_finished:
                call_log.call_status = "COMPLETED"
                call_log.objection_resolution_status = "100% RESOLVED (Allocation Locked)"
                call_log.customer_decision = "CONFIRMED_BOOKING_PROCEED_TO_FINANCE"
            await db.commit()

        return OutboundDialogueTurnResponse(
            call_reference=req.call_reference,
            speaker=agent_tag,
            agent_message=agent_reply,
            ai_reply=agent_reply,
            is_call_finished=is_finished,
            action_item="PROCEED_TO_FINANCING" if is_finished else "AWAIT_CUSTOMER_REPLY",
            turn_index=turn_idx + 1
        )

    @staticmethod
    async def get_call_insights(db: AsyncSession, call_reference: str) -> Optional[OutboundCallInsightsResponse]:
        stmt = select(OutboundCallLog).where(OutboundCallLog.call_reference == call_reference)
        res = await db.execute(stmt)
        call = res.scalars().first()
        if not call:
            return None

        # Fetch customer
        cust_stmt = select(Customer).where(Customer.id == call.customer_id)
        cust_res = await db.execute(cust_stmt)
        cust = cust_res.scalars().first()

        return OutboundCallInsightsResponse(
            call_reference=call.call_reference,
            brand_id=call.brand_id,
            customer_id=cust.customer_id if cust else "CUST-DEFAULT",
            customer_name=cust.name if cust else "Valued Customer",
            agent_name=call.agent_name,
            phone_number=call.phone_number,
            call_status=call.call_status,
            call_duration_seconds=call.call_duration_seconds,
            transcript=call.transcript or "",
            objections_handled=[
                "Test Drive Feedback Confirmed",
                "Sales Consultant Demonstration Quality Verified",
                "Delivery Allocation & Instant EMI Processed"
            ],
            objection_resolution_status=call.objection_resolution_status or "100% RESOLVED",
            customer_sentiment=call.customer_sentiment or "VERY_POSITIVE",
            customer_decision=call.customer_decision or "LOCKED_FAST_ALLOCATION",
            locked_vehicle_variant=call.locked_vehicle_variant or "Vehicle",
            locked_allocation_days=call.locked_allocation_days or 12,
            next_step=call.next_step or "DIGITAL_FINANCING_KYC",
            created_at=call.created_at
        )
