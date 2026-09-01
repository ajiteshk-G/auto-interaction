import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_sales_leads_flow(client: AsyncClient):
    resp = await client.get("/api/sales/leads")
    assert resp.status_code == 200
    leads = resp.json()
    assert isinstance(leads, list)
    assert len(leads) >= 1
    assert leads[0]["name"] == "Aarav Sharma"

@pytest.mark.asyncio
async def test_test_ride_recording_and_insights(client: AsyncClient):
    payload = {
        "customer_id": "CUST-AARAV-001",
        "vehicle_id": "thar_roxx",
        "variant": "AX7L Diesel AT 4x4",
        "sales_advisor_name": "Rajesh Varma (Bayview Mahindra)",
        "duration_seconds": 195,
        "audio_format": "audio/webm",
        "simulated_scenario": "bandra_sea_link_test_ride"
    }
    resp = await client.post("/api/sales/test-ride/upload-recording", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"].startswith("TR-2026-")
    assert "/test_rides/" in data["gcs_uri"] and data["gcs_uri"].startswith("gs://")
    assert data["customer_sentiment_score"] >= 0.8
    assert data["purchase_intent_score"] >= 0.8
    assert len(data["loved_features"]) > 0
    assert len(data["objections_raised"]) > 0
    assert "Rajesh" in data["sales_advisor_name"]

    # Retrieve insights by session ID
    session_id = data["session_id"]
    get_resp = await client.get(f"/api/sales/test-ride/insights/{session_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["session_id"] == session_id

@pytest.mark.asyncio
async def test_outbound_call_and_dialogue_turns(client: AsyncClient):
    # 1. Trigger call
    trigger_payload = {
        "customer_id": "CUST-AARAV-001",
        "customer_name": "Aarav Sharma",
        "phone_number": "+91 98201 23456",
        "vehicle_name": "Mahindra Thar ROXX AX7L Diesel AT",
        "advisor_name": "Rajesh Varma"
    }
    resp = await client.post("/api/outbound/trigger-call", json=trigger_payload)
    assert resp.status_code == 200
    call_ref = resp.json()["call_reference"]
    assert call_ref.startswith("CALL-")

    # 2. Dialogue Turn 1
    turn_payload = {
        "call_reference": call_ref,
        "customer_speech": "The engine and suspension were amazing! But my wife is concerned on rear legroom and waiting times.",
        "turn_index": 0
    }
    turn_resp = await client.post("/api/outbound/dialogue-turn", json=turn_payload)
    assert turn_resp.status_code == 200
    assert ("MIA" in turn_resp.json()["speaker"] or "AI" in turn_resp.json()["speaker"])

    # 3. Retrieve call insights
    insights_resp = await client.get(f"/api/outbound/call-insights/{call_ref}")
    assert insights_resp.status_code == 200
    insights = insights_resp.json()
    assert insights["objection_resolution_status"].startswith("100%")
    assert insights["locked_allocation_days"] == 12
