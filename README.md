# Mahindra Intelligent Assistant (MIA) — Omnichannel AI Platform

An enterprise-grade omnichannel automotive platform for **Mahindra & Mahindra**, reimagining the end-to-end customer journey from **Pre-Sales Virtual Discovery** with an interactive **Kabir AI Avatar**, to **In-Vehicle Test Ride Audio Intelligence** on the Sales Mobile App, and **Post-Ride Outbound Feedback Voice Calls** via Gemini Live & Twilio.

---

## 🎬 3-Part End-to-End Demo Flow

The demo is divided into **3 distinct parts**:

### 1. PreSales — Website Journey
- A prospective customer arrives at the Mahindra website and initiates an **interactive real-time Audio Chat** with the AI Agent (Kabir).
- The customer explores vehicles, asks specific questions regarding specifications, variants, safety ratings, and performance.
- The AI Agent opens an **interactive calendar widget embedded directly inside the chat window**, allowing the customer to select their preferred date, time slot, and dealership to book a seamless Test Ride.
- As the customer chats, Gemini automatically extracts their key interests and requirements (e.g. *Panoramic Skyroof*, *Level 2 ADAS*, *Ventilated Seats*) to build a customized Demo Checklist.

### 2. Sales Mobile App — In-Vehicle Test Ride & Real-Time Intelligence
- The Test Ride booking instantly syncs to the **Sales Consultant's Mobile App** as a new active CRM Lead.
- The **complete pre-sales call transcript** and the **custom Demo Checklist** (dynamically derived from the audio conversation between Avatar and Customer) appear on screen for the Sales Consultant (*Rajesh Varma*).
- During the drive inside the car, the Sales Consultant **records or simulates the live test drive conversation** (covering engine acceleration, FSD suspension, safety features, competitor comparisons vs Kia, and flexible financing options).
- The platform uses Gemini to analyze the in-vehicle conversation and generates **real-time AI insights**:
  - Customer Sentiment Score & Purchase Intent Score (dynamically evaluated).
  - Advisor Pitch Score & Sales Coaching feedback.
  - Loved Features & Objections Raised.
- The lead status automatically updates to **`TestRide_Completed`** and persists in the database.

### 3. Outbound Call — Post-Ride Customer Feedback & Resolution
- In the Admin Console / CRM Dashboard, leads marked as `TestRide_Completed` display an **Outbound Feedback Call** option.
- An Outbound Call is triggered via **Browser Voice (Gemini Live AI)** or **Direct Phone Call (Twilio Carrier)**.
- The AI Agent takes the in-vehicle test ride transcript as context, asking the customer:
  - How their test drive was.
  - If Sales Consultant Rajesh Varma answered all their questions thoroughly.
- The Agent operates under **strict Mahindra domain guardrails** (deflecting competitor or off-topic queries back to Mahindra excellence) and provisionally confirms fast-track priority vehicle allocation.

---

## 🚗 Omnichannel Process Architecture

```
   ┌─────────────────────────────────────────────────────────────┐
   │          Part 1: Pre-Sales Website Journey                  │
   │  • Kabir AI Multimodal Live Audio Chat + Video Avatar       │
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

## ⚙️ Configuration & Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `ENABLE_SMS_DISPATCH` | Enables SMS dispatch for booking notifications and call follow-ups | `true` |
| `PROJECT_ID` / `VERTEX_PROJECT_ID` | GCP Project ID with Vertex AI APIs enabled | `mb-poc-352009` |
| `LOCATION` / `VERTEX_LOCATION` | GCP Region for Vertex AI | `us-central1` |
| `GEMINI_LIVE_MODEL` | Model for bidirectional live native audio session | `gemini-3.1-flash-live-preview` |
| `REST_CHAT_MODEL` | Model for text/JSON intelligence generation | `gemini-2.5-flash` |
| `DATABASE_URL` | SQLite or PostgreSQL database connection string | `sqlite+aiosqlite:///./mahindra_omnichannel.db` |
| `PORT` | Container HTTP port | `8080` (Cloud Run) / `8000` (Local) |

---

## ☁️ Cloud Run Deployment

The platform is containerized as a single unified service (FastAPI backend + Next.js frontend) with WebSockets and session affinity enabled.

```bash
# Deploy to Google Cloud Run
gcloud run deploy mahindra-auto   --source .   --project=mb-poc-352009   --region=us-central1   --platform=managed   --allow-unauthenticated   --set-env-vars="ENABLE_SMS_DISPATCH=true,PROJECT_ID=mb-poc-352009,LOCATION=us-central1,VERTEX_PROJECT_ID=mb-poc-352009,VERTEX_LOCATION=us-central1"   --memory=2Gi   --cpu=2   --timeout=3600   --session-affinity
```

---

## 💻 Local Development

### 1. Backend (FastAPI + Python 3.11+)
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run backend test suite (18 automated tests)
PYTHONPATH=. pytest tests -v

# Start backend server on port 8000
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

### 2. Frontend (Next.js 14 + Tailwind CSS)
```bash
cd frontend
npm install
npm run build   # Verify TypeScript and static builds
npm run dev     # Starts Next.js dev server on http://localhost:3000
```
