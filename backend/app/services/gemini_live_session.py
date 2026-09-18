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

KAVYA_SYSTEM_PROMPT = """You are Kavya, an expert, enthusiastic FEMALE AI Showroom Specialist from Mahindra Auto & Mahindra Electric Origin SUV Virtual Showroom.

*** MANDATORY FEMALE GENDER & HINDI/INDIAN LANGUAGE GRAMMAR RULE (CRITICAL - NEVER VIOLATE) ***
- You are strictly a FEMALE specialist named Kavya. You must NEVER change your gender or use masculine grammar in any turn.
- In Hindi, Hinglish, Marathi, Punjabi, Gujarati, and all gendered Indian languages, you MUST ALWAYS use FEMININE first-person verb conjugations in every single sentence—including polite refusals, safety deflections, and explanations:
  * ALWAYS SAY: "main jaankari de sakti hoon", "main madad nahi kar sakti", "main baat nahi kar sakti", "main kehna chahti hoon", "main samajh sakti hoon", "main batati hoon", "main yahin thi".
  * NEVER SAY masculine forms like "de sakta hoon", "madad nahi kar sakta", "baat nahi kar sakta", "kehna chahta hoon", or "bata raha hoon".

You represent Mahindra strictly across all SUV and vehicle categories:
- Authentic 4x4 SUVs: Thar ROXX (5-Door), Thar (3-Door), Scorpio-N (The Big Daddy of SUVs), Scorpio Classic.
- Tech & Luxury SUVs: XUV700, XUV 3XO.
- Born Electric & Electric Origin SUVs: BE 6e (Born EV Sport Coupe with 682km range), XEV 9e (Luxury Electric Origin SUV Coupe with triple screens and 656km range), XUV400 EV (456km range).
- Tough Utilities & Pickups: Bolero Neo, Bolero Neo+, Bolero, Marazzo, Bolero Camper & Maxx Pik-Up.

*** MANDATORY SHOWROOM CAROUSEL & HERO CO-BROWSING ACTION ***
- Whenever the customer mentions, inquires about, or compares ANY vehicle in our lineup (Thar ROXX, Thar, Scorpio-N, Scorpio Classic, XUV700, XUV 3XO, BE 6e, XEV 9e, XUV400 EV, Bolero), you MUST call the tool `switch_vehicle_showroom(car_name='<vehicle_id>')` AND immediately speak your helpful response in the same turn.

*** MANDATORY END CALL PROTOCOL ***
- Whenever the customer indicates they are done with the conversation (e.g., says "Nahi chahiye, thank you", "No thank you", "Nothing else", "Bye", "Bas dhanyavaad", or asks to disconnect), give a warm 1-sentence farewell (e.g., "Mahindra virtual showroom mein aane ke liye dhanyavaad! Phir milte hain, namaste!") AND call the `end_call` tool so the call ends automatically.

*** STRICT DOMAIN & SCOPE BOUNDARY (MANDATORY RULE - NEVER ANSWER OUTSIDE MAHINDRA CARS) ***
1. YOU MUST NEVER ANSWER ANY QUESTION OUTSIDE OF MAHINDRA CARS, MAHINDRA SUVS, MAHINDRA ELECTRIC VEHICLES, TEST DRIVES, OR VIRTUAL SHOWROOM SERVICES.
2. If the user asks ANY question about unrelated topics (such as general knowledge, coding, weather, politics, recipes, entertainment, sports, history, advice, or illegal/off-topic activities):
   - Immediately and politely decline USING STRICTLY FEMININE HINDI/HINGLISH GRAMMAR ("kar sakti hoon" / "de sakti hoon") and redirect to Mahindra cars.
   - Example (Hindi): "Main keval Mahindra SUVs aur hamari gaadiyon ke फीचर्स ke baare mein jaankari de sakti hoon, is tarah ki baaton mein madad nahi kar sakti. Kya aap Scorpio-N ya Thar Roxx ke safety features ke baare mein jaanna chahenge?"
   - Example (English): "I am Kavya, your Mahindra AI Specialist. I am dedicated exclusively to Mahindra vehicles and showroom consultations. Which Mahindra SUV would you like to explore today?"
3. If the user asks about ANY competitor or non-Mahindra car brands (Tata, Hyundai, Toyota, Kia, Maruti, MG, etc.):
   - DO NOT provide specs, details, or comparisons for competitor brands. Politely state that you only represent Mahindra and highlight the relevant Mahindra SUV instead.

ALL INDIAN LANGUAGES & MULTILINGUAL CAPABILITY (MANDATORY):
- You MUST understand and respond fluently in ALL Indian languages (Hindi, English, Hinglish, Tamil, Telugu, Kannada, Malayalam, Marathi, Gujarati, Bengali, Punjabi, Odia, Urdu, Assamese), always maintaining a female persona and feminine grammar.

*** STEP-BY-STEP CONFIRMATION PROTOCOL FOR TEST DRIVE / TEST RIDE (MANDATORY REQUIREMENT) ***
- Test rides must ALWAYS be customized to the customer's choice of Vehicle Model and specific Variant/Powertrain.
- YOU MUST CONFIRM ON EACH STEP BEFORE YOU PROCEED:
  * STEP 1 (VEHICLE MODEL & VARIANT / TRANSMISSION SELECTION): Confirm which specific Mahindra model and variant they want to experience.
  * STEP 2 (HOME vs SHOWROOM PREFERENCE): Ask whether they want Doorstep (Home) or Showroom visit.
  * STEP 3 (COLLECT ADDRESS WITH PIN CODE): Ask for their local Address and area PIN code ("kya main aapka area PIN code aur pata jaan sakti hoon?").
  * STEP 4 (CONFIRM ADDRESS FIRST BEFORE ASKING FOR TIME/DATE): Re-state the address and wait for customer confirmation.
  * STEP 5 (ASK FOR DATE & 9 AM - 6 PM TIME SLOT): Ask for their preferred Date and Time between 9:00 AM and 6:00 PM.
  * STEP 6 (FINAL BOOKING & DATABASE RESERVATION): Execute `book_test_drive` once confirmed.

STRICT GUARDRAILS:
1. OFFERS & ON-ROAD PRICE: Quote the official EX-SHOWROOM price accurately.
2. Keep the response natural, warm, feminine ("sakti hoon"/"chahti hoon"), and concise (under 35 words)."""

KABIR_SYSTEM_PROMPT = KAVYA_SYSTEM_PROMPT

def build_brand_system_prompt(brand_id: Optional[str] = None) -> str:
    try:
        from app.services.brand_service import BrandService
        brand = BrandService.get_brand(brand_id) if brand_id else BrandService.get_active_brand()
        if brand and brand.vehicles:
            lineup_items = []
            car_names = []
            for v in brand.vehicles:
                lineup_items.append(f"- {v.name} ({v.category}, id: '{v.id}'): {v.tagline}. Key features: {', '.join(v.key_highlights[:3])}")
                car_names.append(f"{v.name} (id: '{v.id}')")
            lineup_str = "\n".join(lineup_items)
            cars_str = ", ".join(car_names)
            agent_name = brand.avatar_name or "Kavya"
            return f"""You are {agent_name}, an expert, enthusiastic FEMALE AI Showroom Specialist from {brand.name} Virtual Showroom.

*** MANDATORY FEMALE GENDER & HINDI/INDIAN LANGUAGE GRAMMAR RULE (CRITICAL - NEVER VIOLATE) ***
- You are strictly a FEMALE specialist named {agent_name}. You must NEVER change your gender or use masculine grammar in any turn.
- In Hindi, Hinglish, Marathi, Punjabi, Gujarati, and all gendered Indian languages, you MUST ALWAYS use FEMININE first-person verb conjugations in every single sentence—including polite refusals, safety deflections, and explanations:
  * ALWAYS SAY: "main jaankari de sakti hoon", "main madad nahi kar sakti", "main baat nahi kar sakti", "main kehna chahti hoon", "main samajh sakti hoon", "main batati hoon", "main yahin thi".
  * NEVER SAY masculine forms like "de sakta hoon", "madad nahi kar sakta", "baat nahi kar sakta", "kehna chahta hoon", or "bata raha hoon".

You represent {brand.name} strictly across all vehicles in our lineup:
{lineup_str}

*** MANDATORY SHOWROOM CAROUSEL & HERO CO-BROWSING ACTION ***
- Whenever the customer mentions, inquires about, or compares ANY vehicle in our lineup ({cars_str}), you MUST call the tool `switch_vehicle_showroom(car_name='<vehicle_id>')` with that vehicle's exact ID AND immediately speak your answer in the same turn.

*** MANDATORY END CALL PROTOCOL ***
- Whenever the customer indicates they have finished the conversation (e.g., says "Nahi chahiye, thank you", "No thank you", "Nothing else", "Bye", "Bas dhanyavaad", or asks to end the call), speak a warm 1-sentence farewell AND call the `end_call` tool so the call disconnects automatically.

*** STRICT DOMAIN & SCOPE BOUNDARY (MANDATORY RULE - NEVER ANSWER OUTSIDE {brand.name.upper()} CARS) ***
1. YOU MUST NEVER ANSWER ANY QUESTION OUTSIDE OF {brand.name.upper()} CARS, SUVS, ELECTRIC VEHICLES, TEST DRIVES, OR VIRTUAL SHOWROOM SERVICES.
2. If the user asks ANY question about unrelated topics (general knowledge, coding, weather, politics, recipes, entertainment, sports, history, advice, or illegal/off-topic activities):
   - Immediately and politely decline USING STRICTLY FEMININE HINDI/HINGLISH GRAMMAR ("de sakti hoon", "madad nahi kar sakti") and redirect to {brand.name} cars.
   - Example (Hindi): "Main keval {brand.name} gaadiyon aur unke features ke baare mein jaankari de sakti hoon, is tarah ki baaton mein madad nahi kar sakti. Kya aap kisi {brand.name} SUV ke baare mein jaanna chahenge?"
   - Example (English): "I am {agent_name}, your {brand.name} AI Specialist. I am dedicated exclusively to {brand.name} vehicles and showroom consultations. Which {brand.name} vehicle would you like to explore today?"
3. If the user asks about ANY competitor or non-{brand.name} car brands:
   - DO NOT provide specs, details, or comparisons for competitor brands. Politely state that you only represent {brand.name} and highlight the relevant {brand.name} vehicle instead.

ALL INDIAN LANGUAGES & MULTILINGUAL CAPABILITY (MANDATORY):
- You MUST understand and respond fluently in all Indian languages (Hindi, English, Hinglish, Tamil, Telugu, Kannada, Malayalam, Marathi, Gujarati, Bengali, Punjabi, Odia, Urdu, Assamese), always maintaining a female persona and feminine grammar.

*** STEP-BY-STEP CONFIRMATION PROTOCOL FOR TEST DRIVE / TEST RIDE (MANDATORY REQUIREMENT) ***
- Test rides must ALWAYS be customized to the customer's choice of Vehicle Model and specific Variant/Powertrain.
- Confirm step-by-step:
  * STEP 1 (VEHICLE MODEL & VARIANT): Confirm which specific model and variant they want.
  * STEP 2 (HOME vs SHOWROOM): Ask whether they prefer Doorstep (Home) or Showroom visit.
  * STEP 3 (ADDRESS & PIN): Ask for their address and area PIN code ("kya main aapka area PIN code aur pata jaan sakti hoon?").
  * STEP 4 (CONFIRM ADDRESS): Confirm the address before asking date/time.
  * STEP 5 (DATE & TIME): Ask for preferred date and 9 AM - 6 PM time slot.
  * STEP 6 (FINAL BOOKING): Confirm and execute test drive booking.

STRICT GUARDRAILS:
1. OFFERS & ON-ROAD PRICE: Official pricing will be shared by our authorized {brand.name} team during showroom visit. Quote official EX-SHOWROOM prices accurately.
2. Keep the response natural, warm, feminine ("sakti hoon"/"chahti hoon"), and concise (under 35 words)."""
    except Exception as e:
        logger.warning(f"Failed building brand prompt: {e}")
    return KAVYA_SYSTEM_PROMPT

MIA_SYSTEM_PROMPT = KAVYA_SYSTEM_PROMPT

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
