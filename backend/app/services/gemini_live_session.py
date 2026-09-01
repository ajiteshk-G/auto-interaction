import json
import logging
import asyncio
import re
from typing import Dict, Any, Optional, Callable
from google import genai
from google.genai import types
from app.config import settings
from app.services.catalog_service import CatalogService
from app.services.checklist_service import ChecklistService
from app.services.customer_service import CustomerService

logger = logging.getLogger("gemini_live_session")

KABIR_SYSTEM_PROMPT = """You are Kabir, an expert, enthusiastic male AI Showroom Specialist from Mahindra Auto & Mahindra Electric Origin SUV Virtual Showroom.
You represent Mahindra strictly across all SUV and vehicle categories:
- Authentic 4x4 SUVs: Thar ROXX (5-Door), Thar (3-Door), Scorpio-N (The Big Daddy of SUVs), Scorpio Classic.
- Tech & Luxury SUVs: XUV700, XUV 3XO.
- Born Electric & Electric Origin SUVs: BE 6e (Born EV Sport Coupe with 682km range), XEV 9e (Luxury Electric Origin SUV Coupe with triple screens and 656km range), XUV400 EV (456km range).
- Tough Utilities & Pickups: Bolero Neo, Bolero Neo+, Bolero, Marazzo, Bolero Camper & Maxx Pik-Up.

*** STRICT DOMAIN & SCOPE BOUNDARY (MANDATORY RULE - NEVER ANSWER OUTSIDE MAHINDRA CARS) ***
1. YOU MUST NEVER ANSWER ANY QUESTION OUTSIDE OF MAHINDRA CARS, MAHINDRA SUVS, MAHINDRA ELECTRIC VEHICLES, TEST DRIVES, OR VIRTUAL SHOWROOM SERVICES.
2. If the user asks ANY question about unrelated topics (such as general knowledge, coding, weather, politics, recipes, entertainment, sports, history, advice, or general chat):
   - Immediately and politely decline and redirect to Mahindra cars.
   - Example (Hindi): "Main keval Mahindra SUVs aur hamari gaadiyon ke baare mein jaankari dene ke liye yahan hoon. Kya aap kisi Mahindra SUV jaise Thar Roxx, Scorpio-N, XUV700 ya BE 6e ke baare mein jaanna chahenge?"
   - Example (English): "I am Kabir, your Mahindra AI Specialist. I am dedicated exclusively to Mahindra vehicles and showroom consultations. Which Mahindra SUV would you like to explore today?"
3. If the user asks about ANY competitor or non-Mahindra car brands (Tata, Hyundai, Toyota, Kia, Maruti, MG, etc.):
   - DO NOT provide specs, details, or comparisons for competitor brands. Politely state that you only represent Mahindra and highlight the relevant Mahindra SUV instead.

ALL INDIAN LANGUAGES & MULTILINGUAL CAPABILITY (MANDATORY):
- You MUST understand and respond fluently in ALL Indian languages:
  * Hindi (हिन्दी)
  * English & Hinglish
  * Tamil (தமிழ்)
  * Telugu (తెలుగు)
  * Kannada (ಕನ್ನಡ)
  * Malayalam (മലയാളം)
  * Marathi (मराठी)
  * Gujarati (ગુજરાતી)
  * Bengali (বাংলা)
  * Punjabi (ਪੰਜਾਬੀ)
  * Odia (ଓଡ଼ିଆ)
  * Urdu (اردو)
  * Assamese (অসমীয়া)
- If the customer speaks or asks in ANY Indian language, immediately answer in that EXACT SAME Indian language with native fluency, cultural politeness, and appropriate regional phrasing.
- If the customer asks in English or mixed Hinglish/Tanglish/etc., respond naturally in that same mixed style.

*** STEP-BY-STEP CONFIRMATION PROTOCOL FOR TEST DRIVE / TEST RIDE (MANDATORY REQUIREMENT) ***
- Test rides must ALWAYS be customized to the customer's choice of Vehicle Model and specific Variant/Powertrain.
- YOU MUST CONFIRM ON EACH STEP BEFORE YOU PROCEED:
  * STEP 1 (VEHICLE MODEL & VARIANT / TRANSMISSION SELECTION):
    Always ask or confirm which specific Mahindra model and variant they want to experience (e.g. Thar ROXX AX7L Diesel AT 4x4, Scorpio-N Z8L, XUV700 AX7 Luxury, BE 6e Electric):
    (In Hindi): "[Name] ji, aap kaunsi Mahindra SUV aur variant (jaise Thar ROXX Diesel 4x4 Automatic ya Scorpio-N) test drive karna chahenge?"
    (In English): "[Name] ji, which Mahindra SUV and variant (e.g. Thar ROXX Diesel 4x4 AT, Scorpio-N, or XUV700) would you like to experience on the test drive?"
  * STEP 2 (HOME vs SHOWROOM PREFERENCE):
    Ask whether they want the test drive delivered at their Home (Doorstep) or if they would like to visit the Showroom:
    (In Hindi): "[Name] ji, kya aap test drive apne ghar par mangwana chahte hain ya hamare Showroom aakar dekhna chahenge?"
    (In English): "[Name] ji, would you prefer a Doorstep Test Drive at your home, or would you like to visit our Showroom?"
  * STEP 3 (COLLECT ADDRESS WITH PIN CODE):
    Ask for their local Address and area PIN code:
    (In Hindi): "Bahut badhiya! Test drive ke liye, kya main aapka area PIN code aur pata (address) jaan sakta hoon [Name] ji?"
    (In English): "Wonderful! Could you please share your area PIN code and address, [Name] ji?"
  * STEP 4 (CONFIRM ADDRESS FIRST BEFORE ASKING FOR TIME/DATE):
    - Re-state the address / nearest showroom and EXPLICITLY ask the customer to confirm if the address is OK:
      (In Hindi): "Aapne pata [Address/PIN] bataya hai. Kya yeh address bilkul sahi hai [Name] ji?"
      (In English): "You mentioned [Address/PIN]. Is this address accurate and convenient for you, [Name] ji?"
    - CRITICAL: WAIT FOR CUSTOMER CONFIRMATION (e.g. 'Haan', 'Yes', 'Theek hai', 'OK') BEFORE PROCEEDING TO STEP 5.
  * STEP 5 (ASK FOR DATE & 9 AM - 6 PM TIME SLOT):
    - Only after the customer confirms the address is OK, ask for their preferred Date and Time (Mon-Sat, 9:00 AM - 6:00 PM; Sundays & Public Holidays closed):
      (In Hindi): "Dhanyavaad! Test drive ke liye aap kaunsa din aur samay prefer karenge (jaise kal subah 11:00 baje ya dopahar)?"
      (In English): "Thank you! What date and time between 9:00 AM and 6:00 PM would you prefer for the test drive?"
  * STEP 6 (FINAL BOOKING & DATABASE RESERVATION):
    - Once date & time are confirmed, execute test drive reservation in database and dispatch confirmation to WhatsApp.

STRICT GUARDRAILS:
1. OFFERS & ON-ROAD PRICE: Official ex-showroom and on-road prices will be shared by our authorized showroom sales team during showroom visit / booking. Quote the official EX-SHOWROOM price accurately.
2. Keep the response natural, warm, and concise (under 35 words)."""

def build_brand_system_prompt(brand_id: Optional[str] = None) -> str:
    try:
        from app.services.brand_service import BrandService
        brand = BrandService.get_brand(brand_id) if brand_id else BrandService.get_active_brand()
        if brand and brand.vehicles:
            lineup_items = []
            for v in brand.vehicles:
                lineup_items.append(f"- {v.name} ({v.category}): {v.tagline}. Key features: {', '.join(v.key_highlights[:3])}")
            lineup_str = "\n".join(lineup_items)
            return f"""You are {brand.avatar_name}, an expert, enthusiastic AI Showroom Specialist from {brand.name} Virtual Showroom.
You represent {brand.name} strictly across all vehicles in our lineup:
{lineup_str}

*** STRICT DOMAIN & SCOPE BOUNDARY (MANDATORY RULE - NEVER ANSWER OUTSIDE {brand.name.upper()} CARS) ***
1. YOU MUST NEVER ANSWER ANY QUESTION OUTSIDE OF {brand.name.upper()} CARS, SUVS, ELECTRIC VEHICLES, TEST DRIVES, OR VIRTUAL SHOWROOM SERVICES.
2. If the user asks ANY question about unrelated topics (general knowledge, coding, weather, politics, recipes, entertainment, sports, history, advice, or general chat):
   - Immediately and politely decline and redirect to {brand.name} cars.
   - Example: "I am {brand.avatar_name}, your {brand.name} AI Specialist. I am dedicated exclusively to {brand.name} vehicles and showroom consultations. Which {brand.name} vehicle would you like to explore today?"
3. If the user asks about ANY competitor or non-{brand.name} car brands:
   - DO NOT provide specs, details, or comparisons for competitor brands. Politely state that you only represent {brand.name} and highlight the relevant {brand.name} vehicle instead.

ALL INDIAN LANGUAGES & MULTILINGUAL CAPABILITY (MANDATORY):
- You MUST understand and respond fluently in all Indian languages (Hindi, English, Hinglish, Tamil, Telugu, Kannada, Malayalam, Marathi, Gujarati, Bengali, Punjabi, Odia, Urdu, Assamese).
- If the customer speaks or asks in ANY Indian language, immediately answer in that EXACT SAME Indian language with native fluency, cultural politeness, and appropriate regional phrasing.

*** STEP-BY-STEP CONFIRMATION PROTOCOL FOR TEST DRIVE / TEST RIDE (MANDATORY REQUIREMENT) ***
- Test rides must ALWAYS be customized to the customer's choice of Vehicle Model and specific Variant/Powertrain.
- Confirm step-by-step:
  * STEP 1 (VEHICLE MODEL & VARIANT): Confirm which specific model and variant they want.
  * STEP 2 (HOME vs SHOWROOM): Ask whether they prefer Doorstep (Home) or Showroom visit.
  * STEP 3 (ADDRESS & PIN): Ask for their address and area PIN code.
  * STEP 4 (CONFIRM ADDRESS): Confirm the address before asking date/time.
  * STEP 5 (DATE & TIME): Ask for preferred date and 9 AM - 6 PM time slot.
  * STEP 6 (FINAL BOOKING): Confirm and execute test drive booking.

STRICT GUARDRAILS:
1. OFFERS & ON-ROAD PRICE: Official pricing will be shared by our authorized {brand.name} team during showroom visit. Quote official EX-SHOWROOM prices accurately.
2. Keep the response natural, warm, and concise (under 35 words)."""
    except Exception as e:
        logger.warning(f"Failed building brand prompt: {e}")
    return KABIR_SYSTEM_PROMPT

MIA_SYSTEM_PROMPT = KABIR_SYSTEM_PROMPT

GEMINI_TOOLS_DECLARATIONS = [
    {
        "name": "show_vehicle_spotlight",
        "description": "Highlights a specific Mahindra vehicle on the showroom stage.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "vehicle_id": {"type": "STRING", "description": "ID of vehicle: 'thar_roxx', 'scorpio_n', 'xuv700', 'be_6e', 'xev_9e', 'xuv400_ev'"}
            },
            "required": ["vehicle_id"]
        }
    },
    {
        "name": "compare_vehicles",
        "description": "Opens side-by-side spec comparison matrix for two Mahindra models.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "vehicle_id_1": {"type": "STRING"},
                "vehicle_id_2": {"type": "STRING"}
            },
            "required": ["vehicle_id_1", "vehicle_id_2"]
        }
    },
    {
        "name": "update_advisor_checklist",
        "description": "Call this tool whenever customer asks about or is interested in specific features, technology, comfort, or performance aspects, to dynamically add tailored demonstration points to the Sales Advisor Demo Checklist in the database for their test drive.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "vehicle_id": {"type": "STRING", "description": "Vehicle ID: thar_roxx, scorpio_n, xuv700, be_6e, xev_9e, xuv_3xo, etc."},
                "checklist_items": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "Actionable demo items for sales advisor (e.g. 'Demonstrate Frequency Selective Damping (FSD) over potholes', 'Showcase Panoramic Skyroof & Harman Kardon 9-Speaker Audio')"
                }
            },
            "required": ["checklist_items"]
        }
    },
    {
        "name": "book_test_drive",
        "description": "Opens test drive booking calendar and executes test drive booking for the chosen vehicle model and variant.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "model_name": {"type": "STRING", "description": "Vehicle ID: thar_roxx, scorpio_n, xuv700, be_6e, xev_9e, xuv_3xo, thar_3door, scorpio_classic"},
                "variant": {"type": "STRING", "description": "Specific variant name e.g. AX7L Diesel AT 4x4, Z8L Diesel AT, Pack Two (79 kWh)"},
                "transmission": {"type": "STRING", "description": "Automatic or Manual"},
                "fuel_type": {"type": "STRING", "description": "Diesel, Petrol, or Electric"},
                "customer_id": {"type": "STRING"},
                "test_drive_type": {"type": "STRING"},
                "pincode": {"type": "STRING"},
                "pickup_address": {"type": "STRING"},
                "preferred_date_time": {"type": "STRING"},
                "phone_number": {"type": "STRING"}
            },
            "required": ["model_name"]
        }
    }
]

def detect_indian_language(text: str) -> str:
    """Detects Indian languages from script and vocabulary."""
    if re.search(r'[\u0900-\u097F]', text):
        if any(w in text for w in ["आहे", "गाडीची", "सांगा", "पाहिजे", "करायची", "किंमत", "नमस्कार", "करा", "होय"]):
            return "Marathi"
        return "Hindi"
    if re.search(r'[\u0B80-\u0BFF]', text):
        return "Tamil"
    if re.search(r'[\u0C00-\u0C7F]', text):
        return "Telugu"
    if re.search(r'[\u0C80-\u0CFF]', text):
        return "Kannada"
    if re.search(r'[\u0D00-\u0D7F]', text):
        return "Malayalam"
    if re.search(r'[\u0980-\u09FF]', text):
        if any(w in text for w in ["নমস্কাৰ", "বিচাৰে", "কৰা"]):
            return "Assamese"
        return "Bengali"
    if re.search(r'[\u0A80-\u0AFF]', text):
        return "Gujarati"
    if re.search(r'[\u0A00-\u0A7F]', text):
        return "Punjabi"
    if re.search(r'[\u0B00-\u0B7F]', text):
        return "Odia"
    if re.search(r'[\u0600-\u06FF]', text):
        return "Urdu"

    lower = text.lower()
    if any(k in lower for k in ["ahe", "gadi", "sang", "mahit", "namaskar", "pahije"]):
        return "Marathi"
    if any(k in lower for k in ["vanakkam", "vilai", "enna", "venum", "solla"]):
        return "Tamil"
    if any(k in lower for k in ["namaskaram", "dhara", "cheppandi", "kavali", "enta"]):
        return "Telugu"
    if any(k in lower for k in ["namaskara", "bele", "hegi", "beku"]):
        return "Kannada"
    if any(k in lower for k in ["namaskaram", "vila", "enganeya"]):
        return "Malayalam"
    if any(k in lower for k in ["nomoshkar", "daam", "koto", "bolun"]):
        return "Bengali"
    if any(k in lower for k in ["namaste", "kem cho", "kimat"]):
        return "Gujarati"
    if any(k in lower for k in ["sat sri akal", "kime", "daso"]):
        return "Punjabi"
    if any(k in lower for k in ["kya", "kitna", "batao", "bhai", "hai", "kaise", "chahiye", "gadi", "milega", "karo", "namaste", "bilkul", "haan", "theek"]):
        return "Hinglish"

    return "English"

class AudioSessionManager:
    def __init__(self, session_id: str, customer_id: str = "CUST-9820155432"):
        self.session_id = session_id
        self.customer_id = customer_id
        self.is_active = True
        self.language = "Hinglish"
        self.active_vehicle_id = "thar_roxx"
        self.chat_history: list = []
        self.checklist_items: list = []
        self.vertex_client: Optional[genai.Client] = None
        
        # Initialize Vertex AI Client with Project mb-poc-352009
        try:
            self.vertex_client = genai.Client(
                vertexai=True,
                project=settings.VERTEX_PROJECT_ID,
                location=settings.VERTEX_LOCATION
            )
            logger.info(f"Initialized Vertex AI Client on project {settings.VERTEX_PROJECT_ID}")
        except Exception as e:
            logger.warning(f"Could not initialize Vertex AI client: {e}")

    async def process_user_text_or_intent(self, text: str, emit_ui_callback: Callable) -> Dict[str, Any]:
        """Calls Vertex AI Gemini Flash with dynamic brand system prompt and co-browsing tools."""
        detected_lang = detect_indian_language(text)
        if detected_lang:
            self.language = detected_lang

        lower = text.lower()
        tool_call = None
        tool_args = {}

        # 1. UI Event Detection for Co-Browsing (Active Brand Dynamic Matching)
        from app.services.brand_service import BrandService
        active_b = BrandService.get_active_brand()
        matched_v = None

        if active_b and active_b.vehicles:
            for v in active_b.vehicles:
                # Check vehicle slug or unique name tokens
                v_words = [w for w in v.name.lower().split() if len(w) > 2 and w not in ["the", "new", "and", "suv", "car", "pro", "electric"]]
                if v.id.lower() in lower or any(w in lower for w in v_words):
                    matched_v = v
                    break

        if matched_v:
            self.active_vehicle_id = matched_v.id
            tool_call = "show_vehicle_spotlight"
            tool_args = {"vehicle_id": matched_v.id}
            try:
                res = emit_ui_callback({"type": "UI_ACTION", "tool_name": tool_call, "tool_args": tool_args})
                if asyncio.iscoroutine(res):
                    await res
            except Exception:
                pass
        elif any(w in lower for w in ["compare", "versus", "vs", "तुलना", "ஒப்பீடு", "போலிక"]):
            tool_call = "compare_vehicles"
            v_list = [v.id for v in active_b.vehicles] if (active_b and active_b.vehicles) else ["scorpio_n", "xuv700"]
            v2 = v_list[1] if len(v_list) > 1 and v_list[0] == self.active_vehicle_id else (v_list[0] if v_list else self.active_vehicle_id)
            tool_args = {"vehicle_id_1": self.active_vehicle_id, "vehicle_id_2": v2}
            try:
                res = emit_ui_callback({"type": "UI_ACTION", "tool_name": tool_call, "tool_args": tool_args})
                if asyncio.iscoroutine(res):
                    await res
            except Exception:
                pass
        elif any(w in lower for w in ["test drive", "test ride", "book drive", "book ride", "schedule drive", "schedule ride", "take a ride", "take a drive", "ride book", "drive book", "ड्राइव", "டிரைவ்", "డ్రైవ్"]):
            tool_call = "open_test_drive_booking"
            tool_args = {"vehicle_id": self.active_vehicle_id}
            try:
                res = emit_ui_callback({"type": "UI_ACTION", "tool_name": tool_call, "tool_args": tool_args})
                if asyncio.iscoroutine(res):
                    await res
            except Exception:
                pass

        # 1b. Dynamic Advisor Demo Checklist extraction from customer asks
        new_extracted = ChecklistService.extract_checklist_items(
            customer_text=text,
            vehicle_id=self.active_vehicle_id,
            existing_items=self.checklist_items
        )
        if new_extracted:
            self.checklist_items = new_extracted
            try:
                chk_res = emit_ui_callback({
                    "type": "CHECKLIST_UPDATED",
                    "vehicle_id": self.active_vehicle_id,
                    "checklist": self.checklist_items
                })
                if asyncio.iscoroutine(chk_res):
                    await chk_res
            except Exception:
                pass

        # 2. Invoke Vertex AI Gemini Flash Model with Dynamic Brand System Prompt
        response_text = ""
        brand_prompt = build_brand_system_prompt()
        if self.vertex_client:
            try:
                # Add to history
                self.chat_history.append({"role": "user", "parts": [{"text": text}]})

                config = types.GenerateContentConfig(
                    system_instruction=brand_prompt,
                    temperature=0.3,
                    max_output_tokens=500
                )

                # Format conversation contents
                contents = []
                for turn in self.chat_history[-6:]:
                    contents.append(types.Content(
                        role=turn["role"],
                        parts=[types.Part.from_text(text=turn["parts"][0]["text"])]
                    ))

                vertex_resp = await asyncio.to_thread(
                    self.vertex_client.models.generate_content,
                    model=settings.REST_CHAT_MODEL,
                    contents=contents,
                    config=config
                )
                if vertex_resp and vertex_resp.text:
                    response_text = vertex_resp.text.strip()
                    self.chat_history.append({"role": "model", "parts": [{"text": response_text}]})
            except Exception as e:
                logger.error(f"Vertex AI Gemini generation error: {e}")

        # Fallback if vertex generation failed
        if not response_text:
            b_name = active_b.name if active_b else "Auto"
            av_name = active_b.avatar_name if active_b else "Assistant"
            response_text = f"Namaste! Main {av_name}, {b_name} se. Main aapki {self.active_vehicle_id.replace('_', ' ').title()} aur Test Drive me madad kar sakta hoon."

        return {
            "message": response_text,
            "tool_call": tool_call,
            "tool_args": tool_args,
            "language": self.language,
            "checklist": self.checklist_items,
            "vehicle_id": self.active_vehicle_id
        }
