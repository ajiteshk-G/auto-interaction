import pytest

@pytest.mark.asyncio
async def test_create_test_drive_booking(client):
    payload = {
        "customer_id": "CUST-AARAV-001",
        "vehicle_id": "thar_roxx",
        "variant": "AX7L Diesel AT 4x4",
        "color": "Stealth Black",
        "dealership_id": "bayview_bandra",
        "booking_type": "HOME_DOORSTEP",
        "delivery_address": "Linking Road Office, Bandra West",
        "scheduled_date": "Tomorrow",
        "scheduled_time_slot": "5:00 PM",
        "notes": "Customer interested in FSD suspension on Sea Link"
    }
    response = await client.post("/api/bookings", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "BK-MAH" in data["booking_reference"]
    assert data["dealership_name"] == "Bayview Mahindra, Bandra West"
    assert data["status"] == "CONFIRMED"

@pytest.mark.asyncio
async def test_list_customer_bookings(client):
    # Book a slot first
    payload = {
        "customer_id": "CUST-AARAV-001",
        "vehicle_id": "be_6e",
        "variant": "Pack Three (79kWh)",
        "scheduled_date": "This Saturday",
        "scheduled_time_slot": "11:00 AM"
    }
    await client.post("/api/bookings", json=payload)
    
    response = await client.get("/api/bookings/my-bookings?customer_id=CUST-AARAV-001")
    assert response.status_code == 200
    bookings = response.json()
    assert len(bookings) >= 1
