# Mahindra Intelligent Assistant (MIA) — Omnichannel AI Platform

An enterprise-grade omnichannel automotive platform for **Mahindra & Mahindra**, reimagining the end-to-end customer journey from **Pre-Sales Virtual Discovery** with an interactive **AI Voice Avatar**, to **In-Vehicle Test Ride Audio Intelligence** on the Sales Mobile App, and **Post-Ride Outbound Feedback Voice Calls** via Gemini Live & Twilio.

**Live deployment:** https://auto-interaction-hobr26cxda-uc.a.run.app

---

## 🎬 3-Part End-to-End Demo Flow

The demo is divided into **3 distinct parts**:

### 1. PreSales — Website Journey
- A prospective customer arrives at the Mahindra website and initiates an **interactive real-time Audio Chat** with the AI Agent.
- The customer explores vehicles, asks specific questions regarding specifications, variants, safety ratings, and performance.
- The AI Agent opens an **interactive calendar widget embedded directly inside the chat window**, allowing the customer to select their preferred date, time slot, and dealership to book a seamless Test Ride.
- As the customer chats, Gemini automatically extracts their key interests and requirements (e.g. *Panoramic Skyroof*, *Level 2 ADAS*, *Ventilated Seats*) to build a customized Demo Checklist.

### 2. Sales Mobile App — In-Vehicle Test Ride & Real-Time Intelligence
- The Test Ride booking instantly syncs to the **Sales Consultant's Mobile App** as a new active CRM Lead.
- The **complete pre-sales call transcript** and the **custom Demo Checklist** (dynamically derived from the audio conversation between Avatar and Customer) appear on screen for the Sales Consultant.
- During the drive inside the car, the Sales Consultant **records or simulates the live test drive conversation** (covering engine acceleration, FSD suspension, safety features, competitor comparisons, and flexible financing options).
- The platform uses Gemini to analyze the in-vehicle conversation and generates **real-time AI insights**:
  - Customer Sentiment Score & Purchase Intent Score (dynamically evaluated).
  - Advisor Pitch Score & Sales Coaching feedback.
  - Loved Features & Objections Raised.
- The lead status automatically updates to **`TestRide_Completed`** and persists in the database.

### 3. Outbound Call — Post-Ride Customer Feedback & Resolution
- In the Admin Console / CRM Dashboard, leads marked as `TestRide_Completed` display an **Outbound Feedback Call** option.
- An Outbound Call is triggered via **Browser Voice (Gemini Live AI)** or **Direct Phone Call (Twilio Carrier)**.
- The AI Agent takes the in-vehicle test ride transcript as context, asking the customer how their test drive was and whether the Sales Consultant answered all their questions thoroughly.
- The Agent operates under **strict Mahindra domain guardrails** (deflecting competitor or off-topic queries back to Mahindra excellence) and provisionally confirms fast-track priority vehicle allocation.

---

## 🚗 Omnichannel Process Architecture

```
   ┌─────────────────────────────────────────────────────────────┐
   │          Part 1: Pre-Sales Website Journey                  │
   │  • Multimodal Live Audio Chat + Video Avatar                │
   │  • Synchronized Co-Browsing Tool Calling                    │
   │  • Dynamic Feature Checklist Extraction from Customer Chat  │
   │  • Test Drive Booking with Embedded In-Chat Calendar Widget │
   └──────────────────────────────┬──────────────────────────────┘
                                  │
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │          Part 2: Sales Mobile App & Test Ride               │
   │  • Test Ride Booking Appears as CRM Lead with Call Transcript│
   │  • Dynamic Demo Checklist on Screen for Sales Consultant    │
   │  • In-Vehicle Test Drive Audio Recording / Simulation       │
   │  • Gemini Dynamic Audio Insights (Sentiment, Pitch Score)   │
   │  • Lead Status Updates to 'TestRide_Completed'              │
   └──────────────────────────────┬──────────────────────────────┘
                                  │
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │          Part 3: Outbound Feedback Call & Admin Console     │
   │  • Trigger Outbound Voice Call for 'TestRide_Completed' Leads│
   │  • Dual-Mode: Browser Call (Gemini Live) & Twilio Carrier   │
   │  • In-Vehicle Transcript Context & Advisor Review           │
   │  • Strict Mahindra Domain Guardrails & Objection Resolution │
   │  • Priority Fast-Track Allocation Confirmation              │
   └─────────────────────────────────────────────────────────────┘
```

---

## 🗂️ Repository Layout

| Path | Description |
| :--- | :--- |
| `backend/` | FastAPI service — REST APIs, Gemini Live WebSocket bridge, SQLAlchemy models, services |
| `backend/app/routers/ws_live.py` | Bidirectional Gemini Live proxy (browser ⇄ Vertex AI Bidi), tool calling, transcript persistence |
| `backend/app/services/gemini_live_session.py` | System prompts, language detection, audio session state |
| `frontend/` | Next.js 14 App Router UI (React 18 + Tailwind CSS) |
| `frontend/src/hooks/useLiveVoice.ts` | Browser-side live audio capture, playback, and WebSocket session lifecycle |
| `android/` | Sales Consultant mobile app assets |
| `Dockerfile` / `entrypoint.sh` | Combined single-container build (Next.js + FastAPI) for Cloud Run |

---

## 🗣️ Live Voice Session Behaviour

The pre-sales voice agent runs on **Gemini Live native audio** over the Vertex AI Bidi WebSocket endpoint.

- **Default language is `en-IN`.** The greeting is always delivered in English.
- **Dynamic follow-up language mode.** Each turn, the user's speech transcript and text input are inspected and the assistant is instructed to mirror that language for the reply. A customer who switches to Hindi mid-call gets Hindi replies; switching back to English switches the assistant back.
- **Booking a test ride does not end the call.** Turns identified as booking confirmations suppress the `end_call` tool so the conversation continues after the slot is confirmed. The in-chat calendar collapses shortly after a slot is chosen.
- **Automatic call termination on farewells.** The call ends only when the customer signals they are done (e.g. *"no, thank you"*, *"nothing else"*, *"bye"*) or when the assistant delivers an unambiguous closing line. Both romanized and Devanagari farewell phrasings are recognised.

### Local authentication for Gemini Live

The Bidi endpoint requires a token with `aiplatform.endpoints.predict` on the target project.

- **On Cloud Run** (`K_SERVICE` is set) the service account's Application Default Credentials are used.
- **Locally** the token is sourced from `gcloud auth print-access-token`, because ADC on a developer workstation is often a different identity than the one authorised for Vertex AI.

If `Start Live` fails locally, confirm the active gcloud account can reach Vertex AI:

```bash
gcloud auth list
gcloud config get-value project
```

A wrong identity surfaces as the WebSocket closing with `1008 policy violation — Permission 'aiplatform.endpoints.predict' denied`.

---

## ⚙️ Configuration & Environment Variables

All values below are read from the environment, falling back to the listed default (see `backend/app/config.py`).

| Variable | Description | Default |
| :--- | :--- | :--- |
| `PROJECT_ID` / `VERTEX_PROJECT_ID` | GCP Project ID with Vertex AI APIs enabled | `mb-poc-352009` |
| `LOCATION` / `VERTEX_LOCATION` | GCP Region for Vertex AI | `us-central1` |
| `GEMINI_LIVE_MODEL` | Model for the bidirectional live native audio session | `gemini-live-2.5-flash-native-audio` |
| `REST_CHAT_MODEL` | Model for text/JSON intelligence generation | `gemini-2.5-flash` |
| `AVATAR_NAME` | Display name of the voice avatar | `Kavya` |
| `AVATAR_VOICE` | Vertex AI prebuilt voice for the avatar | `Aoede` |
| `AVATAR_MODALITY` | Live session response modality | `AUDIO` |
| `DATABASE_URL` | SQLite or PostgreSQL connection string | `sqlite+aiosqlite:///data/auto.db` |
| `GCS_RECORDINGS_BUCKET` / `GCS_BUCKET` | Bucket for test-drive audio recordings | `mb-poc-352009-sales-recordings` |
| `ENABLE_SMS_DISPATCH` | Enables SMS dispatch for booking notifications and call follow-ups | `true` |
| `PORT` | Frontend HTTP port exposed by the container | `8080` |

> [!NOTE]
> `DEFAULT_LOCALE` is still declared in `config.py` (default `hi-IN`) but is not referenced anywhere in the application. The live session language is controlled by the `en-IN` default in the Bidi `speechConfig` plus per-turn language detection, not by this setting.

### Frontend variables

Both are optional; when unset the frontend uses the current origin and relies on the Next.js rewrites.

| Variable | Description |
| :--- | :--- |
| `NEXT_PUBLIC_API_URL` | Overrides the REST API base URL |
| `NEXT_PUBLIC_WS_URL` | Overrides the live-audio WebSocket URL |

### Port model

The container runs two processes. The **backend is always bound to port `8000`** internally; the **Next.js frontend binds to `$PORT`** (`8080` by default) and proxies `/api`, `/uploads`, and `/ws` to `127.0.0.1:8000` via the rewrites in `frontend/next.config.mjs`. Only `$PORT` is exposed.

---

## 💻 Local Development

### 1. Backend (FastAPI + Python 3.11+)
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run backend test suite (23 automated tests)
PYTHONPATH=. pytest tests -v

# Start backend server on port 8000
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify it is up:
```bash
curl -s http://127.0.0.1:8000/api/health
```

### 2. Frontend (Next.js 14 + Tailwind CSS)
```bash
cd frontend
npm install
npm run build   # Verify TypeScript and static builds
npm run dev     # Starts Next.js dev server on http://localhost:3000
```

Open http://localhost:3000. The frontend proxies API and WebSocket traffic to the backend on `127.0.0.1:8000`, so **both processes must be running**.

> [!IMPORTANT]
> Browse to the app over the **same origin** the frontend is served from. The live-voice WebSocket only dials port `8000` directly for `localhost` / `127.0.0.1`; on any other host (remote workstation, proxy domain, Cloud Run) it uses the current origin and relies on the Next.js rewrite.

### 3. Docker Compose (optional)
```bash
docker compose up --build
```

---

## ☁️ Cloud Run Deployment

The platform is containerized as a single unified service (FastAPI backend + Next.js frontend) with WebSockets and session affinity enabled.

```bash
gcloud run deploy auto-interaction \
  --source . \
  --project=mb-poc-352009 \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars="ENABLE_SMS_DISPATCH=true,PROJECT_ID=mb-poc-352009,LOCATION=us-central1,VERTEX_PROJECT_ID=mb-poc-352009,VERTEX_LOCATION=us-central1" \
  --memory=2Gi \
  --cpu=2 \
  --timeout=3600 \
  --session-affinity
```

Notes:
- `--session-affinity` and the long `--timeout` are required to keep the live audio WebSocket pinned to a single instance for the duration of a call.
- `gcloud run deploy --source .` builds the **current working directory**, not a git ref. Check out the branch you intend to ship before deploying.
- The deploying service account must hold `aiplatform.endpoints.predict` on the target project, otherwise live voice sessions will fail at runtime while the rest of the app stays healthy.

---

## 🗃️ Data & Customer Identity

- A customer is uniquely identified by **name + phone number**. Repeat conversations from the same person are attributed to that single customer record.
- Conversations are grouped **per calendar day** in the Sales Consultant view, surfacing the vehicle of interest, features discussed, and stated budget for each day's interactions.
- The default database is SQLite at `backend/data/auto.db`. Set `DATABASE_URL` to a PostgreSQL DSN (`asyncpg` is installed) for a shared or persistent deployment — the container filesystem is ephemeral, so SQLite data does not survive a Cloud Run revision change.
