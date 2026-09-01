import pytest
from app.services.checklist_service import ChecklistService
from app.services.catalog_service import CatalogService

@pytest.mark.asyncio
async def test_static_vehicle_checklists():
    # Thar ROXX
    roxx_list = ChecklistService.get_static_checklist("thar_roxx")
    assert len(roxx_list) >= 3
    assert any("FSD" in item or "Damping" in item for item in roxx_list)

    # BE 6e
    be6e_list = ChecklistService.get_static_checklist("be_6e")
    assert len(be6e_list) >= 3
    assert any("EV" in item or "Charging" in item or "Range" in item for item in be6e_list)

    # Scorpio-N
    scorpio_list = ChecklistService.get_static_checklist("scorpio_n")
    assert any("4XPLOR" in item or "Terrain" in item for item in scorpio_list)

    # Fallback / default
    unknown_list = ChecklistService.get_static_checklist("unknown_car")
    assert len(unknown_list) >= 3


@pytest.mark.asyncio
async def test_dynamic_feature_extraction_from_customer_asks():
    # Customer asks about sunroof and audio
    query1 = "Does the Thar ROXX have a panoramic sunroof and good speakers for road trips?"
    extracted1 = ChecklistService.extract_checklist_items(query1, vehicle_id="thar_roxx")
    assert len(extracted1) >= 2
    assert any("Skyroof" in item or "Sunroof" in item for item in extracted1)
    assert any("Harman Kardon" in item or "Audio" in item or "Speaker" in item for item in extracted1)

    # Customer asks about ADAS and suspension comfort over potholes
    query2 = "How does the suspension handle potholes and does it have ADAS safety?"
    extracted2 = ChecklistService.extract_checklist_items(query2, vehicle_id="thar_roxx")
    assert any("FSD" in item or "Damping" in item or "Suspension" in item for item in extracted2)
    assert any("ADAS" in item for item in extracted2)

    # Customer asks about BE 6e battery charging and screens
    query3 = "How fast is the DC charging on BE 6e and what screens are in the cockpit?"
    extracted3 = ChecklistService.extract_checklist_items(query3, vehicle_id="be_6e")
    assert any("Charging" in item or "Range" in item for item in extracted3)
    assert any("Cockpit Screens" in item or "Display" in item for item in extracted3)


@pytest.mark.asyncio
async def test_presales_chat_persists_checklist_and_leads(client):
    # 1. Simulate Pre-sales chat where customer asks about specific features
    chat_payload = {
        "customer_id": "CUST-CHK-TEST-01",
        "message": "Tell me about Thar Roxx Harman Kardon sound system, ventilated seats and panoramic sunroof.",
        "vehicle_id": "thar_roxx"
    }
    chat_resp = await client.post("/api/live/chat", json=chat_payload)
    assert chat_resp.status_code == 200

    # 2. Book test drive for this customer
    book_payload = {
        "customer_id": "CUST-CHK-TEST-01",
        "vehicle_id": "thar_roxx",
        "variant": "AX7L Diesel AT 4x4",
        "scheduled_date": "Tomorrow",
        "scheduled_time_slot": "04:00 PM"
    }
    book_resp = await client.post("/api/bookings", json=book_payload)
    assert book_resp.status_code == 200

    # 3. Check /sales/leads returns the AI-extracted personalized checklist from DB
    leads_resp = await client.get("/api/sales/leads?dealership_id=ALL")
    assert leads_resp.status_code == 200
    leads = leads_resp.json()
    
    # Find our test lead
    matching_lead = next((l for l in leads if l["customer_id"] == "CUST-CHK-TEST-01"), None)
    assert matching_lead is not None
    assert matching_lead["advisor_checklist"] is not None
    assert len(matching_lead["advisor_checklist"]) > 0
    assert matching_lead["is_custom_checklist"] is True
