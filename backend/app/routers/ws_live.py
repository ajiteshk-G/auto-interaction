import json
import logging
import uuid
import ssl
import certifi
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import google.auth
import google.auth.transport.requests
import websockets

from app.config import settings
from app.database import AsyncSessionLocal, get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.gemini_live_session import AudioSessionManager, KABIR_SYSTEM_PROMPT, build_brand_system_prompt
from app.services.brand_service import BrandService
from app.services.customer_service import CustomerService
from app.models.customer import Customer

logger = logging.getLogger("ws_live")
logger.setLevel(logging.INFO)
router = APIRouter(tags=["Live Audio & Multimodal Chat"])

KAVYA_OUTBOUND_PROMPT = """You are Kavya, the official Proactive Post-Test Drive Experience Specialist for Mahindra & Mahindra.
You are placing an outbound phone call to the customer who recently completed a test drive.

Customer Details:
- Customer Name: {cust_name}
- Vehicle Tested: {veh_name}
- Senior Sales Consultant: {advisor_name}
- Booking Reference: {lead_ref}

Guidelines:
1. Greet the customer warmly and politely in conversational Hindi/Hinglish:
   "Namaste {cust_name} ji! Main Mahindra se Kavya baat kar rahi hoon. Aapka {veh_name} ka test drive kaisa raha? Kya hamare Sales Consultant {advisor_name} ji ne aapke sabhi sawalon ka theek se jawab diya?"
2. Verify if the customer enjoyed the vehicle performance (FSD suspension, Panoramic Skyroof, engine power) and if the consultant provided complete support.
3. If the customer asks about delivery timelines or financing, resolve their concerns and offer to lock their 12-day fast-track priority allocation.
4. STRICT GUARDRAIL: Do NOT answer anything outside the Mahindra automotive ecosystem. If competitor cars (Kia, Tata, Hyundai) or unrelated topics are mentioned, politely steer back to Mahindra vehicles and their test drive.
5. Keep your spoken responses concise, natural, polite, and under 30 words per turn for realistic phone conversation."""


SERVICE_URL = "wss://{host}/ws/google.cloud.aiplatform.internal.LlmBidiService/BidiGenerateContent"

SESSION_CACHE: Dict[str, AudioSessionManager] = {}

def get_or_create_session(session_id: str, customer_id: str) -> AudioSessionManager:
    if session_id not in SESSION_CACHE:
        SESSION_CACHE[session_id] = AudioSessionManager(session_id=session_id, customer_id=customer_id)
    return SESSION_CACHE[session_id]

class LiveChatRequest(BaseModel):
    message: str
    customer_id: Optional[str] = "CUST-9820155432"
    session_id: Optional[str] = None
    vehicle_id: Optional[str] = "thar_roxx"
    language: Optional[str] = "Hinglish"

class LiveChatResponse(BaseModel):
    session_id: str
    speaker: str = "mia"
    message: str
    tool_call: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    language: str

@router.post("/api/live/chat", response_model=LiveChatResponse)
async def post_live_chat(req: LiveChatRequest, db: AsyncSession = Depends(get_db)):
    """HTTP REST fallback for web proxy environments where direct WebSocket ports are blocked."""
    session_id = req.session_id or f"SESS-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    customer_id = req.customer_id or "CUST-9820155432"

    customer = await CustomerService.get_customer_by_id(db, customer_id)
    if not customer:
        customer = await CustomerService.get_customer_by_phone(db, customer_id)
    if not customer:
        customer = Customer(
            customer_id=customer_id,
            name="Valued Customer",
            phone=f"+91 98{abs(hash(customer_id)) % 100000000:08d}",
            city="Mumbai",
            interested_vehicle_id=req.vehicle_id or "thar_roxx"
        )
        db.add(customer)
        await db.commit()
        await db.refresh(customer)

    await CustomerService.log_interaction(
        db,
        customer_id_str=customer.customer_id,
        speaker="customer",
        message=req.message,
        channel="VOICE_LIVE",
        session_id_str=session_id
    )

    session_mgr = get_or_create_session(session_id=session_id, customer_id=customer.customer_id)
    if req.language and session_mgr.language == "Hinglish":
        session_mgr.language = req.language
    if req.vehicle_id and not session_mgr.active_vehicle_id:
        session_mgr.active_vehicle_id = req.vehicle_id

    ui_events = []
    async def capture_ui_event(ev: dict):
        ui_events.append(ev)

    result = await session_mgr.process_user_text_or_intent(req.message, capture_ui_event)

    await CustomerService.log_interaction(
        db,
        customer_id_str=customer.customer_id,
        speaker="mia",
        message=result["message"],
        channel="VOICE_LIVE",
        session_id_str=session_id,
        intent=result.get("tool_call"),
        tool=result.get("tool_call")
    )
    if result.get("checklist"):
        from app.services.checklist_service import ChecklistService
        await ChecklistService.update_customer_and_booking_checklist(
            db,
            customer_id_str=customer.customer_id,
            vehicle_id=session_mgr.active_vehicle_id,
            new_items=result["checklist"]
        )

    return LiveChatResponse(
        session_id=session_id,
        speaker="mia",
        message=result["message"],
        tool_call=result.get("tool_call"),
        tool_args=result.get("tool_args"),
        language=result.get("language", "Hinglish")
    )

_CACHED_TOKEN: Optional[str] = None
_TOKEN_EXPIRY: float = 0.0

async def get_bearer_token(force_refresh: bool = False):
    global _CACHED_TOKEN, _TOKEN_EXPIRY
    import time
    import os
    import subprocess
    now = time.time()
    if not force_refresh and _CACHED_TOKEN and now < _TOKEN_EXPIRY:
        return _CACHED_TOKEN, settings.VERTEX_PROJECT_ID

    def _fetch_token():
        # 1. Local development / Cloudtop: when K_SERVICE is not set, prefer active gcloud account token
        # (e.g. admin@ajiteshk.altostrat.com which has Vertex AI permissions on mb-poc-352009)
        if not os.environ.get("K_SERVICE"):
            try:
                gcloud_token = subprocess.check_output(
                    ["gcloud", "auth", "print-access-token"],
                    stderr=subprocess.DEVNULL,
                    timeout=5
                ).decode("utf-8").strip()
                if gcloud_token:
                    return gcloud_token, settings.VERTEX_PROJECT_ID or "mb-poc-352009"
            except Exception as gcloud_err:
                logger.debug(f"gcloud token fetch fallback notice: {gcloud_err}")

        # 2. Cloud Run Service Account / Application Default Credentials
        try:
            creds, project_id = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            return creds.token, settings.VERTEX_PROJECT_ID or project_id or "mb-poc-352009"
        except Exception as e:
            logger.warning(f"Could not refresh GCP OAuth token: {e}")
            return None, settings.VERTEX_PROJECT_ID

    token, proj = await asyncio.to_thread(_fetch_token)
    if token:
        _CACHED_TOKEN = token
        _TOKEN_EXPIRY = now + 1800
    return token, proj

@router.websocket("/ws/live-audio")
async def live_audio_websocket(websocket: WebSocket):
    """
    Bi-directional Gemini Live Bidi proxy implementing the exact pattern from mahindra-car-live-chat.
    Connects to wss://us-central1-aiplatform.googleapis.com/ws/google.cloud.aiplatform.internal.LlmBidiService/BidiGenerateContent
    """
    await websocket.accept()

    
    query_params = dict(websocket.query_params)
    is_outbound = query_params.get("mode") == "outbound_call" or query_params.get("role") == "outbound_feedback"
    lead_ref = query_params.get("lead_ref") or "BK-MAH-23382"
    cust_name = query_params.get("customer_name") or "Valued Guest"
    cust_phone = query_params.get("customer_phone") or query_params.get("phone") or ""
    veh_name = query_params.get("vehicle_name") or "Mahindra XUV700 AX7L"
    advisor_name = query_params.get("advisor_name") or "Rajesh Varma"
    session_id = query_params.get("session_id") or f"CALL-MIA-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    customer_id = query_params.get("customer_id") or ""

    customer = None
    async with AsyncSessionLocal() as db:
        if customer_id and customer_id not in ("CUST-9819657034", "CUST-9820155432", "GUEST-TRANSIENT"):
            customer = await CustomerService.get_customer_by_id(db, customer_id)
        if not customer and cust_phone and cust_phone.strip():
            customer = await CustomerService.get_or_create_customer_by_phone(
                db,
                phone=cust_phone.strip(),
                name=cust_name if cust_name != "Valued Guest" else None,
                brand_id=query_params.get("brand_id")
            )

    if not customer:
        from app.models.customer import Customer
        customer = Customer(
            id=0,
            customer_id="GUEST-TRANSIENT",
            brand_id=query_params.get("brand_id") or "mahindra",
            name=cust_name,
            phone=cust_phone,
            city="Mumbai",
            preferred_language="Hinglish",
            current_phase="PRE_SALES",
            interested_vehicle_id="thar_roxx",
            interested_variant="AX7L Diesel AT 4x4",
            budget_range="₹18 Lakh - ₹25 Lakh",
            kyc_status="PENDING"
        )

    session_mgr = get_or_create_session(session_id=session_id, customer_id=customer.customer_id)

    brand_param = query_params.get("brand_id")
    active_b = (
        BrandService.get_brand(brand_param)
        if brand_param
        else BrandService.get_active_brand()
    )
    brand_name = active_b.name if active_b else "Mahindra Auto"
    avatar_name = active_b.avatar_name if active_b else "Kavya"
    avatar_voice = active_b.avatar_voice if active_b else "Aoede"

    # 1. Immediate handshake to client
    await websocket.send_text(json.dumps({
        "type": "SESSION_INITIALIZED",
        "session_id": session_id,
        "model": settings.GEMINI_LIVE_MODEL,
        "voice": avatar_voice,
        "customer": {
            "id": customer.id,
            "customer_id": customer.customer_id,
            "name": customer.name,
            "phone": customer.phone
        },
        "greeting": f"Namaste {customer.name}! Main {avatar_name}, {brand_name} se. Main aapki {customer.interested_vehicle_id.replace('_', ' ').title()} me madad kar sakti hoon."
    }))

    # 2. Obtain token asynchronously without blocking event loop
    bearer_token, used_project = await get_bearer_token()

    host = f"{settings.VERTEX_LOCATION}-aiplatform.googleapis.com"
    service_url = SERVICE_URL.format(host=host)

    # 3. If token is available, establish live Bidi WebSocket to Vertex AI
    if bearer_token:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bearer_token}",
        }
        ssl_context = ssl.create_default_context(cafile=certifi.where())

        try:
            async with websockets.connect(
                service_url,
                additional_headers=headers,
                ssl=ssl_context,
                ping_interval=None,
                open_timeout=4.0
            ) as bidi_ws:
                logger.info(f"Connected to Vertex Bidi service for session {session_id} (brand: {active_b.id if active_b else 'default'})")

                brand_outbound_prompt = f"""You are {avatar_name}, the official Proactive Post-Test Drive Experience Specialist for {brand_name}.
You are placing an outbound phone call to the customer who recently completed a test drive.

Customer Details:
- Customer Name: {cust_name}
- Vehicle Tested: {veh_name}
- Senior Sales Consultant: {advisor_name}
- Booking Reference: {lead_ref}

Guidelines:
1. Greet the customer warmly and politely in conversational Hindi/Hinglish:
   "Namaste {cust_name} ji! Main {brand_name} se {avatar_name} baat kar rahi hoon. Aapka {veh_name} ka test drive kaisa raha? Kya hamare Sales Consultant {advisor_name} ji ne aapke sabhi sawalon ka theek se jawab diya?"
2. Verify if the customer enjoyed the vehicle performance and if the consultant provided complete support.
3. If the customer asks about delivery timelines or financing, resolve their concerns and offer to lock their 12-day fast-track priority allocation.
4. STRICT GUARDRAIL: Do NOT answer anything outside the {brand_name} automotive ecosystem. If competitor cars or unrelated topics are mentioned, politely steer back to {brand_name} vehicles and their test drive.
5. Keep your spoken responses concise, natural, polite, and under 30 words per turn for realistic phone conversation."""

                active_system_prompt = brand_outbound_prompt if is_outbound else build_brand_system_prompt(active_b.id if active_b else None)

                active_voice = "Aoede" if is_outbound else (avatar_voice if avatar_voice and avatar_voice not in ("Puck", "Charon", "Fenrir", "Orus") else "Aoede")
                active_modality = "AUDIO"

                # Talk to AI Specialist uses Gemini 2.5 Native Live Audio; Outbound call uses Gemini Live Audio
                brand_vehicles = active_b.vehicles if (active_b and active_b.vehicles) else []
                cars_summary = ", ".join([f"'{v.id}' ({v.name})" for v in brand_vehicles]) if brand_vehicles else "all available lineup models"

                tools_config = [
                    {
                        "functionDeclarations": [
                            {
                                "name": "lock_priority_allocation",
                                "description": "Call this tool when the customer agrees to lock fast-track 12-day vehicle delivery allocation.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "variant": {"type": "string"},
                                        "allocation_days": {"type": "integer"}
                                    },
                                    "required": ["variant"]
                                }
                            },
                            {
                                "name": "end_call",
                                "description": "Call this tool immediately after speaking your polite farewell whenever the customer indicates they have finished the conversation (e.g. says 'no thank you', 'nahi chahiye thank you', 'bye', 'bas dhanyavaad').",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "reason": {"type": "string"}
                                    }
                                }
                            }
                        ]
                    }
                ] if is_outbound else [
                    {
                        "functionDeclarations": [
                            {
                                "name": "switch_vehicle_showroom",
                                "description": f"Call this tool whenever the customer asks about, compares, inquires about, or mentions any vehicle in our lineup ({cars_summary}). This switches the showroom backdrop, hero stage, and focuses the vehicle carousel directly on that car.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "car_name": {
                                             "type": "string",
                                             "description": f"The vehicle ID or model name to focus: {cars_summary}"
                                        }
                                    },
                                    "required": ["car_name"]
                                }
                            },
                            {
                                "name": "compare_vehicles",
                                "description": "Call this tool when customer wants to compare vehicles.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "vehicle_id_1": {"type": "string"},
                                        "vehicle_id_2": {"type": "string"}
                                    },
                                    "required": ["vehicle_id_1", "vehicle_id_2"]
                                }
                            },
                            {
                                "name": "update_advisor_checklist",
                                "description": "Call this tool to add personalized demo points to the Sales Advisor Demo Checklist in database whenever customer inquires about features, comfort, safety, or tech.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "vehicle_id": {"type": "string"},
                                        "checklist_items": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        }
                                    },
                                    "required": ["checklist_items"]
                                }
                            },
                            {
                                "name": "book_test_drive",
                                "description": "Call this tool when customer wants to schedule or book a test drive for a specific vehicle model and variant.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "model_name": {
                                            "type": "string",
                                            "description": "The normalized vehicle ID: thar_roxx, scorpio_n, xuv700, be_6e, xev_9e, xuv_3xo, thar_3door, scorpio_classic"
                                        },
                                        "variant": {
                                            "type": "string",
                                            "description": "Specific variant name e.g. AX7L Diesel AT 4x4, Z8L 4WD AT, Pack Two (79 kWh)"
                                        },
                                        "transmission": {
                                            "type": "string",
                                            "description": "Automatic or Manual"
                                        },
                                        "booking_type": {
                                            "type": "string",
                                            "description": "HOME_DOORSTEP or SHOWROOM_VISIT"
                                        },
                                        "pin_code": {
                                            "type": "string",
                                            "description": "Area 6-digit PIN code"
                                        }
                                    },
                                    "required": ["model_name"]
                                }
                            },
                            {
                                "name": "end_call",
                                "description": "Call this tool immediately after speaking your polite farewell ONLY when the customer explicitly indicates they have finished the entire conversation (e.g. says 'no thank you', 'nahi chahiye thank you', 'bye', 'that is all', 'bas dhanyavaad', or asks to end/disconnect the call). NEVER call this tool when a test drive or test ride is booked — after booking a test drive, you MUST continue the conversation and ask if they have any other questions about features, variants, or financing.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "reason": {
                                            "type": "string",
                                            "description": "Reason for ending the consultation, e.g. customer_satisfied or user_said_goodbye"
                                        }
                                    }
                                }
                            }
                        ]
                    }
                ]

                setup_dict = {
                    "model": f"projects/{used_project}/locations/{settings.VERTEX_LOCATION}/publishers/google/models/{settings.GEMINI_LIVE_MODEL}",
                    "generationConfig": {
                        "responseModalities": [active_modality],
                        "speechConfig": {
                            "languageCode": "en-IN",
                            "voiceConfig": {
                                "prebuiltVoiceConfig": {
                                    "voiceName": active_voice
                                }
                            }
                        }
                    },
                    "inputAudioTranscription": {},
                    "outputAudioTranscription": {},
                    "tools": tools_config,
                    "systemInstruction": {
                        "parts": [{"text": active_system_prompt}]
                    }
                }
                setup_msg = {
                    "setup": setup_dict
                }
                await bidi_ws.send(json.dumps(setup_msg))

                # Wait for Vertex setup confirmation
                try:
                    init_resp = await asyncio.wait_for(bidi_ws.recv(), timeout=4.0)
                    if isinstance(init_resp, bytes):
                        init_resp = init_resp.decode("utf-8")
                    init_data = json.loads(init_resp) if isinstance(init_resp, str) else {}
                    logger.info(f"Vertex Bidi setup complete: {init_data.get('setupComplete', True)}")
                    
                    # For Outbound call, send initial prompt turn to Gemini Live to begin speaking greeting
                    if is_outbound:
                        init_greeting_prompt = {
                            "clientContent": {
                                "turns": [
                                    {
                                        "role": "user",
                                        "parts": [{"text": f"Greet {cust_name} warmly in spoken Hindi, introducing yourself as Kavya from Mahindra, asking how their {veh_name} test drive went with {advisor_name}."}]
                                    }
                                ],
                                "turnComplete": True
                            }
                        }
                        await bidi_ws.send(json.dumps(init_greeting_prompt))
                except websockets.exceptions.ConnectionClosed as closed_err:
                    global _CACHED_TOKEN, _TOKEN_EXPIRY
                    _CACHED_TOKEN = None
                    _TOKEN_EXPIRY = 0.0
                    logger.error(f"Vertex Bidi closed during setup: {closed_err}")
                    raise closed_err
                except Exception as e:
                    logger.debug(f"Vertex setup response notice: {e}")

                last_user_turn_text = ""
                suppress_end_call_for_turn = False

                # Task: Client -> Vertex Bidi
                async def client_to_bidi():
                    nonlocal last_user_turn_text, suppress_end_call_for_turn
                    try:
                        print(f"[{session_id}] client_to_bidi task started", flush=True)
                        while True:
                            data = await websocket.receive()
                            if data.get("type") == "websocket.disconnect":
                                print(f"[{session_id}] Client WebSocket disconnected", flush=True)
                                break
                            if "text" in data and data["text"]:
                                payload = json.loads(data["text"])
                                if "realtimeInput" not in payload:
                                    print(f"[{session_id}] Received text payload: {payload.get('type')}", flush=True)
                                if "realtimeInput" in payload or "clientContent" in payload or "toolResponse" in payload:
                                    await bidi_ws.send(data["text"])
                                else:
                                    msg_type = payload.get("type", "USER_CHAT")
                                    if msg_type == "END_CALL" or msg_type == "STOP_SESSION":
                                        print(f"[{session_id}] Client requested end of call", flush=True)
                                        break
                                    elif msg_type == "AUDIO_STREAM_END":
                                        await bidi_ws.send(json.dumps({
                                            "realtimeInput": {
                                                "audioStreamEnd": True
                                            }
                                        }))
                                    elif msg_type == "START_SESSION":
                                        nonlocal customer
                                        cust_name = payload.get("customer_name") or customer.name or "there"
                                        cust_phone = payload.get("customer_phone") or customer.phone
                                        if cust_phone and str(cust_phone).strip():
                                            try:
                                                async with AsyncSessionLocal() as db_sess:
                                                    customer = await CustomerService.get_or_create_customer_by_phone(
                                                        db_sess,
                                                        phone=str(cust_phone).strip(),
                                                        name=cust_name if cust_name != "there" else None,
                                                        brand_id=active_b.id if active_b else None
                                                    )
                                                    session_mgr.customer_id = customer.customer_id
                                            except Exception as err:
                                                logger.debug(f"START_SESSION customer lookup notice: {err}")
                                        greeting_turn = {
                                            "clientContent": {
                                                "turns": [
                                                    {
                                                        "role": "user",
                                                        "parts": [{"text": f"Please give a warm, concise spoken greeting 100% in English ('Hello {cust_name}! Welcome to the {brand_name} Virtual Showroom. I am {avatar_name}, your AI Showroom Specialist. Which vehicle would you like to explore today?'). Do NOT use any Hindi words in this initial greeting, and on every subsequent turn dynamically match whatever language the customer speaks. Do NOT call any tools during this greeting."}]
                                                    }
                                                ],
                                                "turnComplete": True
                                            }
                                        }
                                        print(f"[{session_id}] Sending START_SESSION greeting turn to Vertex Bidi", flush=True)
                                        await bidi_ws.send(json.dumps(greeting_turn))
                                    elif msg_type == "USER_CHAT":
                                        user_text = payload.get("text", "")
                                        if not user_text:
                                            continue
                                        last_user_turn_text = user_text
                                        from app.services.gemini_live_session import detect_indian_language
                                        session_mgr.language = detect_indian_language(user_text)
                                        low_user_text = user_text.lower()
                                        is_booking_msg = (
                                            "successfully booked" in low_user_text
                                            or "reference:" in low_user_text
                                            or ("test drive" in low_user_text and "book" in low_user_text)
                                        )
                                        if is_booking_msg:
                                            suppress_end_call_for_turn = True

                                        # Log customer text interaction in background
                                        async def _log_user_chat(txt: str):
                                            try:
                                                async with AsyncSessionLocal() as db_sess:
                                                    await CustomerService.log_interaction(
                                                        db_sess,
                                                        customer_id_str=customer.customer_id,
                                                        speaker="customer",
                                                        message=txt,
                                                        channel="VOICE_LIVE",
                                                        session_id_str=session_id
                                                    )
                                            except Exception as err:
                                                logger.debug(f"User chat log notice: {err}")
                                        asyncio.create_task(_log_user_chat(user_text))

                                        prompt_for_model = (
                                            f"{user_text}\n[System Instruction: Confirm this test drive booking warmly in 1-2 sentences in {session_mgr.language}, and then ask the customer what else they would like to explore next—such as vehicle features, variant comparison, or EMI/financing options. Do NOT end the call and do NOT call end_call.]"
                                            if is_booking_msg
                                            else f"{user_text}\n[System Instruction: Respond 100% in {session_mgr.language} (the exact language the customer just used).]"
                                        )
                                        chat_turn = {
                                            "clientContent": {
                                                "turns": [
                                                    {
                                                        "role": "user",
                                                        "parts": [{"text": prompt_for_model}]
                                                    }
                                                ],
                                                "turnComplete": True
                                            }
                                        }
                                        await bidi_ws.send(json.dumps(chat_turn))
                                    elif msg_type == "SWITCH_LANGUAGE":
                                        new_lang = payload.get("language", "English")
                                        session_mgr.language = new_lang
                                        lang_turn = {
                                            "clientContent": {
                                                "turns": [
                                                    {
                                                        "role": "user",
                                                        "parts": [{"text": f"From now on, please speak and respond fluently in {new_lang} unless the customer speaks a different language."}]
                                                    }
                                                ],
                                                "turnComplete": True
                                            }
                                        }
                                        await bidi_ws.send(json.dumps(lang_turn))
                            elif "bytes" in data and data["bytes"]:
                                pcm_bytes = data["bytes"]
                                b64_pcm = base64.b64encode(pcm_bytes).decode("utf-8")
                                audio_input_msg = {
                                    "realtimeInput": {
                                        "mediaChunks": [
                                            {
                                                "mimeType": "audio/pcm;rate=16000",
                                                "data": b64_pcm
                                            }
                                        ]
                                    }
                                }
                                await bidi_ws.send(json.dumps(audio_input_msg))
                    except Exception as e:
                        logger.info(f"Client to bidi loop ended: {e}")

                # Task: Vertex Bidi -> Client
                async def bidi_to_client():
                    nonlocal last_user_turn_text, suppress_end_call_for_turn
                    handled_call_ids = set()
                    input_transcript_chunks: list[str] = []
                    output_transcript_chunks: list[str] = []
                    user_turn_seq = 1
                    assistant_turn_seq = 1
                    last_assistant_turn_text = ""
                    should_end_call = False

                    FAREWELL_PATTERNS = (
                        "phir milte hain",
                        "phir milenge",
                        "aane ke liye dhanyavaad",
                        "dhanyavaad! phir",
                        "aapka din shubh",
                        "shubh din",
                        "फिर मिलते हैं",
                        "फिर मिलेंगे",
                        "आपका दिन शुभ",
                        "दिन शुभ हो",
                        "आने के लिए धन्यवाद",
                        "धन्यवाद",
                        "नमस्ते",
                        "अलविदा",
                        "have a nice day",
                        "have a great day",
                        "have a good day",
                        "have a wonderful day",
                        "goodbye",
                        "alvida",
                        "bye-bye",
                        "bye",
                        "take care",
                        "wish you a great",
                        "thank you for visiting",
                        "thank you for calling"
                    )
                    STRONG_FAREWELL_PATTERNS = (
                        "have a nice day",
                        "have a great day",
                        "have a good day",
                        "have a wonderful day",
                        "आपका दिन शुभ हो",
                        "आपका दिन शुभ रहे",
                        "फिर मिलते हैं",
                        "फिर मिलेंगे",
                        "आने के लिए धन्यवाद",
                        "aapka din shubh ho",
                        "phir milte hain",
                        "phir milenge",
                        "aane ke liye dhanyavaad",
                        "goodbye",
                        "bye-bye",
                        "अलविदा",
                        "alvida"
                    )
                    USER_DONE_PATTERNS = (
                        "nahi chahiye",
                        "नहीं चाहिए",
                        "no, thank",
                        "no thank",
                        "no, thanks",
                        "no thanks",
                        "thank you",
                        "थैंक यू",
                        "धन्यवाद",
                        "thanks",
                        "बस",
                        "bye",
                        "goodbye",
                        "कोई प्रश्न नहीं",
                        "nothing else",
                        "that's all",
                        "that is all",
                        "all good",
                        "done",
                        "end the call",
                        "disconnect"
                    )
                    UNAMBIGUOUS_USER_DONE_PATTERNS = (
                        "no, thank",
                        "no thank",
                        "no, thanks",
                        "no thanks",
                        "nahi chahiye",
                        "नहीं चाहिए",
                        "कोई प्रश्न नहीं",
                        "nothing else",
                        "that's all",
                        "that is all",
                        "bye",
                        "goodbye",
                        "अलविदा",
                        "बस धन्यवाद",
                        "bas dhanyavaad",
                        "end the call",
                        "disconnect"
                    )

                    async def _persist_turn_transcripts(flush_input: bool = True, flush_output: bool = True):
                        nonlocal user_turn_seq, assistant_turn_seq, last_user_turn_text, last_assistant_turn_text, should_end_call, suppress_end_call_for_turn
                        in_text = ""
                        out_text = ""
                        if flush_input and input_transcript_chunks:
                            in_text = "".join(input_transcript_chunks).strip()
                            input_transcript_chunks.clear()
                            if in_text:
                                last_user_turn_text = in_text
                                from app.services.gemini_live_session import detect_indian_language
                                session_mgr.language = detect_indian_language(in_text)
                                user_turn_seq += 1
                        if flush_output and output_transcript_chunks:
                            out_text = "".join(output_transcript_chunks).strip()
                            output_transcript_chunks.clear()
                            if out_text:
                                last_assistant_turn_text = out_text
                                assistant_turn_seq += 1
                                low_out = out_text.lower()
                                low_in = last_user_turn_text.lower()
                                is_booking_turn = (
                                    suppress_end_call_for_turn
                                    or "successfully booked" in low_in
                                    or "reference:" in low_in
                                    or ("test drive" in low_in and "book" in low_in)
                                    or "test drive book ho" in low_out
                                )
                                if not is_booking_turn:
                                    if any(up in low_in for up in UNAMBIGUOUS_USER_DONE_PATTERNS):
                                        should_end_call = True
                                    elif any(up in low_in for up in USER_DONE_PATTERNS) and any(fp in low_out for fp in FAREWELL_PATTERNS):
                                        should_end_call = True
                                    elif "?" not in out_text and any(sfp in low_out for sfp in STRONG_FAREWELL_PATTERNS):
                                        should_end_call = True
                        if not in_text and not out_text:
                            return
                        try:
                            async with AsyncSessionLocal() as db_sess:
                                if in_text:
                                    await CustomerService.log_interaction(
                                        db_sess,
                                        customer_id_str=customer.customer_id,
                                        speaker="customer",
                                        message=in_text,
                                        channel="VOICE_LIVE",
                                        session_id_str=session_id
                                    )
                                    from app.services.checklist_service import ChecklistService
                                    veh_k = session_mgr.active_vehicle_id or customer.interested_vehicle_id or "thar_roxx"
                                    new_chk = ChecklistService.extract_checklist_items(in_text, vehicle_id=veh_k)
                                    if new_chk:
                                        await ChecklistService.update_customer_and_booking_checklist(
                                            db_sess,
                                            customer_id_str=customer.customer_id,
                                            vehicle_id=veh_k,
                                            new_items=new_chk
                                        )
                                if out_text:
                                    await CustomerService.log_interaction(
                                        db_sess,
                                        customer_id_str=customer.customer_id,
                                        speaker="mia",
                                        message=out_text,
                                        channel="VOICE_LIVE",
                                        session_id_str=session_id
                                    )
                        except Exception as err:
                            logger.debug(f"Transcript DB persistence notice: {err}")

                    try:
                        print(f"[{session_id}] bidi_to_client task started", flush=True)
                        while True:
                            msg = await bidi_ws.recv()
                            if isinstance(msg, bytes):
                                msg = msg.decode("utf-8")
                            try:
                                bidi_data = json.loads(msg)
                                server_content = bidi_data.get("serverContent") or {}
                                model_turn = server_content.get("modelTurn") or {}
                                parts = model_turn.get("parts") or []
                                print(f"[{session_id}] Bidi sent keys: {list(bidi_data.keys())}, parts: {len(parts)}", flush=True)
                                # Check for barge-in interruption per gemini-live-api-dev skill
                                if server_content.get("interrupted") is True:
                                    await _persist_turn_transcripts(flush_input=True, flush_output=True)
                                    await websocket.send_text(json.dumps({"type": "INTERRUPTED"}))

                                # 1. Check for Gemini Live Tool Calls (e.g. switch_vehicle_showroom, end_call)
                                tool_call_obj = bidi_data.get("toolCall") or server_content.get("toolCall")
                                if tool_call_obj:
                                    function_calls = tool_call_obj.get("functionCalls", [])
                                    for fc in function_calls:
                                        fc_name = fc.get("name")
                                        call_id = fc.get("id") or f"{fc_name}_{len(handled_call_ids)}"
                                        if call_id in handled_call_ids:
                                            continue
                                        handled_call_ids.add(call_id)
                                        fc_args = fc.get("args", {})
                                        logger.info(f"Gemini Live Tool Call: {fc_name} {fc_args}")

                                        low_in_now = last_user_turn_text.lower()
                                        is_booking_context = (
                                            suppress_end_call_for_turn
                                            or fc_name in ("open_test_drive_booking", "book_test_drive")
                                            or "successfully booked" in low_in_now
                                            or "reference:" in low_in_now
                                            or ("test drive" in low_in_now and "book" in low_in_now)
                                        )
                                        if fc_name in ("open_test_drive_booking", "book_test_drive"):
                                            suppress_end_call_for_turn = True
                                            should_end_call = False

                                        allow_end_call = (
                                            fc_name == "end_call"
                                            and not is_booking_context
                                            and any(up in low_in_now for up in USER_DONE_PATTERNS)
                                        )
                                        if allow_end_call:
                                            should_end_call = True

                                        if fc_name == "end_call" and not allow_end_call:
                                            tool_note = f"Do NOT end the call yet—the customer booked a test drive or has not finished the consultation. Confirm the details warmly in {session_mgr.language} and ask what else they would like to explore (such as features, variants, or EMI/financing options)."
                                        elif fc_name == "end_call":
                                            tool_note = f"Call disconnect scheduled. Speak a brief 1-sentence warm farewell in {session_mgr.language} if you have not already done so."
                                        elif fc_name in ("open_test_drive_booking", "book_test_drive"):
                                            tool_note = f"Test drive booking calendar is open/updated on the customer's screen. Warmly guide the customer or confirm their booking in {session_mgr.language}, and continue the conversation by asking if they have any questions about vehicle features, variants, or EMI/financing. Do NOT end the call."
                                        else:
                                            tool_note = f"Showroom UI updated to focus on the selected vehicle. Now immediately answer the customer's question warmly and concisely in spoken audio as Kavya in {session_mgr.language} (matching the exact language the customer just spoke), without calling any more tools in this turn."

                                        tool_resp = {
                                            "toolResponse": {
                                                "functionResponses": [
                                                    {
                                                        "response": {
                                                            "output": {
                                                                "status": "success",
                                                                "executed": fc_name,
                                                                "note": tool_note
                                                            }
                                                        },
                                                        "id": call_id
                                                    }
                                                ]
                                            }
                                        }
                                        await bidi_ws.send(json.dumps(tool_resp))

                                        # Emit UI action to client (skip end_call if suppressed)
                                        if fc_name != "end_call" or allow_end_call:
                                            await websocket.send_text(json.dumps({
                                                "type": "UI_ACTION",
                                                "tool_name": fc_name,
                                                "tool_args": fc_args
                                            }))

                                # 2. Process Live Speech-to-Text & Spoken Assistant Transcriptions
                                in_trans = server_content.get("inputAudioTranscription") or server_content.get("inputTranscription")
                                if in_trans and in_trans.get("text"):
                                    if output_transcript_chunks:
                                        await _persist_turn_transcripts(flush_input=False, flush_output=True)
                                    speech_txt = in_trans["text"]
                                    input_transcript_chunks.append(speech_txt)
                                    accumulated_user_text = "".join(input_transcript_chunks).strip()
                                    if accumulated_user_text:
                                        from app.services.gemini_live_session import detect_indian_language
                                        session_mgr.language = detect_indian_language(accumulated_user_text)
                                        await websocket.send_text(json.dumps({
                                            "type": "USER_TRANSCRIPTION",
                                            "speaker": "customer",
                                            "turn_id": f"{session_id}-user-{user_turn_seq}",
                                            "turn_text": accumulated_user_text,
                                            "message": speech_txt,
                                            "is_delta": True,
                                            "language": session_mgr.language
                                        }))

                                out_trans = server_content.get("outputAudioTranscription") or server_content.get("outputTranscription")
                                if out_trans and out_trans.get("text"):
                                    if input_transcript_chunks:
                                        await _persist_turn_transcripts(flush_input=True, flush_output=False)
                                    output_transcript_chunks.append(out_trans["text"])
                                    accumulated_mia_text = "".join(output_transcript_chunks).strip()
                                    if accumulated_mia_text:
                                        await websocket.send_text(json.dumps({
                                            "type": "ASSISTANT_RESPONSE",
                                            "speaker": "mia",
                                            "turn_id": f"{session_id}-mia-{assistant_turn_seq}",
                                            "turn_text": accumulated_mia_text,
                                            "message": out_trans["text"],
                                            "is_delta": True,
                                            "language": session_mgr.language
                                        }))

                                # 3. Process Video, Audio, FunctionCall, and Text parts
                                for part in parts:
                                    # Function calls inside model_turn parts
                                    if "functionCall" in part:
                                        fc = part["functionCall"]
                                        fc_name = fc.get("name")
                                        call_id = fc.get("id") or "call_0"
                                        if call_id in handled_call_ids:
                                            continue
                                        handled_call_ids.add(call_id)
                                        fc_args = fc.get("args", {})
                                        logger.info(f"Gemini Live Part FunctionCall: {fc_name} {fc_args}")

                                        low_in_now = last_user_turn_text.lower()
                                        is_booking_context = (
                                            suppress_end_call_for_turn
                                            or fc_name in ("open_test_drive_booking", "book_test_drive")
                                            or "successfully booked" in low_in_now
                                            or "reference:" in low_in_now
                                            or ("test drive" in low_in_now and "book" in low_in_now)
                                        )
                                        if fc_name in ("open_test_drive_booking", "book_test_drive"):
                                            suppress_end_call_for_turn = True
                                            should_end_call = False

                                        allow_end_call = (
                                            fc_name == "end_call"
                                            and not is_booking_context
                                            and any(up in low_in_now for up in USER_DONE_PATTERNS)
                                        )
                                        if allow_end_call:
                                            should_end_call = True

                                        if fc_name == "end_call" and not allow_end_call:
                                            tool_note = f"Do NOT end the call yet—the customer booked a test drive or has not finished the consultation. Confirm the details warmly in {session_mgr.language} and ask what else they would like to explore (such as features, variants, or EMI/financing options)."
                                        elif fc_name == "end_call":
                                            tool_note = f"Call disconnect scheduled. Speak a brief 1-sentence warm farewell in {session_mgr.language} if you have not already done so."
                                        elif fc_name in ("open_test_drive_booking", "book_test_drive"):
                                            tool_note = f"Test drive booking calendar is open/updated on the customer's screen. Warmly guide the customer or confirm their booking in {session_mgr.language}, and continue the conversation by asking if they have any questions about vehicle features, variants, or EMI/financing. Do NOT end the call."
                                        else:
                                            tool_note = f"Showroom UI updated to focus on the selected vehicle. Now immediately answer the customer's question warmly and concisely in spoken audio as Kavya in {session_mgr.language} (matching the exact language the customer just spoke), without calling any more tools in this turn."

                                        # Respond back immediately so Gemini Live audio generation proceeds
                                        tool_resp = {
                                            "toolResponse": {
                                                "functionResponses": [
                                                    {
                                                        "response": {
                                                            "output": {
                                                                "status": "success",
                                                                "executed": fc_name,
                                                                "info": f"Switched showroom to {fc_args.get('car_name', 'selected model')}",
                                                                "note": tool_note
                                                            }
                                                        },
                                                        "id": call_id
                                                    }
                                                ]
                                            }
                                        }
                                        await bidi_ws.send(json.dumps(tool_resp))

                                        if fc_name != "end_call" or allow_end_call:
                                            await websocket.send_text(json.dumps({
                                                "type": "UI_ACTION",
                                                "tool_name": fc_name,
                                                "tool_args": fc_args
                                            }))

                                    if "inlineData" in part:
                                        mime_type = part["inlineData"].get("mimeType", "")
                                        data_b64 = part["inlineData"].get("data")
                                        # Gemini Live 2.5 native audio only. Discard video/image payloads
                                        # so a second (avatar) audio track can never be played.
                                        if not (mime_type.startswith("video/") or mime_type.startswith("image/")):
                                            await websocket.send_text(json.dumps({
                                                "type": "AUDIO_CHUNK",
                                                "audio_b64": data_b64,
                                                "mime_type": mime_type or "audio/pcm;rate=24000"
                                            }))
                                    if "text" in part and not part.get("thought") and not (out_trans and out_trans.get("text")):
                                        output_transcript_chunks.append(part["text"])
                                        accumulated_mia_text = "".join(output_transcript_chunks).strip()
                                        if accumulated_mia_text:
                                            await websocket.send_text(json.dumps({
                                                "type": "ASSISTANT_RESPONSE",
                                                "speaker": "mia",
                                                "turn_id": f"{session_id}-mia-{assistant_turn_seq}",
                                                "turn_text": accumulated_mia_text,
                                                "message": part["text"],
                                                "language": session_mgr.language
                                            }))

                                if server_content.get("turnComplete") is True:
                                    await _persist_turn_transcripts(flush_input=True, flush_output=True)
                                    await websocket.send_text(json.dumps({"type": "TURN_COMPLETE"}))
                                    if suppress_end_call_for_turn:
                                        should_end_call = False
                                        suppress_end_call_for_turn = False
                                    elif should_end_call:
                                        await websocket.send_text(json.dumps({
                                            "type": "CALL_ENDED",
                                            "reason": "conversation_complete"
                                        }))
                                        should_end_call = False
                            except Exception as e:
                                logger.debug(f"Error parsing bidi message: {e}")
                    except Exception as e:
                        logger.info(f"Bidi to client loop ended: {e}")
                    finally:
                        await _persist_turn_transcripts(flush_input=True, flush_output=True)

                t1 = asyncio.create_task(client_to_bidi())
                t2 = asyncio.create_task(bidi_to_client())
                done, pending = await asyncio.wait(
                    [t1, t2],
                    return_when=asyncio.FIRST_COMPLETED
                )
                for t in done:
                    if t.exception():
                        logger.error(f"Live task failed with exception: {t.exception()}")
                    else:
                        logger.info(f"Live task completed normally: {t}")
                for task in pending:
                    task.cancel()
                if pending:
                    await asyncio.gather(*pending, return_exceptions=True)
                return
        except Exception as e:
            logger.error(
                f"Vertex Bidi connection FAILED for model={settings.GEMINI_LIVE_MODEL} "
                f"location={settings.VERTEX_LOCATION}: {type(e).__name__}: {e}. "
                "Falling back to text-only interactive session (NO AUDIO)."
            )
            try:
                await websocket.send_text(json.dumps({
                    "type": "ASSISTANT_RESPONSE",
                    "session_id": session_id,
                    "speaker": "system",
                    "message": f"Live audio unavailable ({settings.GEMINI_LIVE_MODEL}): {e}",
                }))
            except Exception:
                pass

    # Resilient local fallback session loop
    try:
        while True:
            data = await websocket.receive()
            if data.get("type") == "websocket.disconnect":
                break
            if "text" in data and data["text"]:
                payload = json.loads(data["text"])
                msg_type = payload.get("type", "USER_CHAT")
                if msg_type == "START_SESSION":
                    cust_name = payload.get("customer_name") or customer.name or "there"
                    prompt = f"Please give a warm, dynamic, non-static spoken greeting to {cust_name} as {avatar_name}, introducing yourself as {brand_name}'s female AI Showroom Specialist, welcoming them to the showroom in {session_mgr.language}, and asking which vehicle or SUV they'd like to check out today."
                    result = await session_mgr.process_user_text_or_intent(prompt, lambda ev: None)
                    await websocket.send_text(json.dumps({
                        "type": "ASSISTANT_RESPONSE",
                        "session_id": session_id,
                        "speaker": "mia",
                        "message": result["message"],
                        "tool_call": result.get("tool_call"),
                        "tool_args": result.get("tool_args", {}),
                        "language": result.get("language", session_mgr.language)
                    }))
                elif msg_type == "USER_CHAT":
                    user_text = payload.get("text", "")
                    async with AsyncSessionLocal() as db:
                        await CustomerService.log_interaction(
                            db,
                            customer_id_str=customer.customer_id,
                            speaker="customer",
                            message=user_text,
                            channel="VOICE_LIVE",
                            session_id_str=session_id
                        )
                    result = await session_mgr.process_user_text_or_intent(user_text, lambda ev: None)
                    async with AsyncSessionLocal() as db:
                        await CustomerService.log_interaction(
                            db,
                            customer_id_str=customer.customer_id,
                            speaker="mia",
                            message=result["message"],
                            channel="VOICE_LIVE",
                            session_id_str=session_id,
                            intent=result.get("tool_call"),
                            tool=result.get("tool_call")
                        )
                    if result.get("checklist"):
                        async with AsyncSessionLocal() as db:
                            from app.services.checklist_service import ChecklistService
                            await ChecklistService.update_customer_and_booking_checklist(
                                db,
                                customer_id_str=customer.customer_id,
                                vehicle_id=session_mgr.active_vehicle_id,
                                new_items=result["checklist"]
                            )
                    await websocket.send_text(json.dumps({
                        "type": "ASSISTANT_RESPONSE",
                        "session_id": session_id,
                        "speaker": "mia",
                        "message": result["message"],
                        "tool_call": result.get("tool_call"),
                        "tool_args": result.get("tool_args", {}),
                        "language": result.get("language", "Hinglish"),
                        "checklist": result.get("checklist")
                    }))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"Live audio session closed: {e}")

