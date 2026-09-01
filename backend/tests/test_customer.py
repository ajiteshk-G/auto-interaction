import pytest

@pytest.mark.asyncio
async def test_get_customer_profile(client):
    response = await client.get("/api/customer/profile?phone=+919820155432")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Aarav Sharma"
    assert data["phone"] == "+919820155432"

@pytest.mark.asyncio
async def test_identify_new_and_returning_customer(client):
    # 1. Register a fresh customer with valid Name & Phone
    new_user_payload = {
        "name": "Priya Patel",
        "phone": "+91 98765 43210",
        "session_type": "LIVE_CALL",
        "vehicle_id": "be_6e"
    }
    res1 = await client.post("/api/customer/identify", json=new_user_payload)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["name"] == "Priya Patel"
    assert data1["phone"] == "+919876543210"
    assert data1["is_returning"] is False
    assert data1["session_id"].startswith("SESS-")
    assert data1["past_session_count"] == 1
    session_id_1 = data1["session_id"]
    customer_id = data1["customer_id"]

    # 2. Add transcript turns to session 1
    t1_payload = {
        "session_id": session_id_1,
        "customer_id": customer_id,
        "speaker": "customer",
        "message": "What is the certified range of BE 6e Pack Three?",
        "extracted_intent": "VEHICLE_SPECS"
    }
    t_res1 = await client.post("/api/customer/transcript-turn", json=t1_payload)
    assert t_res1.status_code == 200

    # 3. Returning customer starts a SECOND session with same phone
    returning_user_payload = {
        "name": "Priya Patel",
        "phone": "9876543210",
        "session_type": "CHAT_BOT",
        "vehicle_id": "thar_roxx"
    }
    res2 = await client.post("/api/customer/identify", json=returning_user_payload)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["name"] == "Priya Patel"
    assert data2["phone"] == "+919876543210"
    assert data2["is_returning"] is True # Recognized as returning user!
    assert data2["session_id"] != session_id_1 # Separate session created!
    assert data2["past_session_count"] == 2
    session_id_2 = data2["session_id"]

    # 4. Fetch all sessions (1:Many relationship verification)
    sess_res = await client.get(f"/api/customer/sessions?customer_id={customer_id}")
    assert sess_res.status_code == 200
    sessions_list = sess_res.json()
    assert len(sessions_list) == 2
    session_ids = [s["session_id"] for s in sessions_list]
    assert session_id_1 in session_ids
    assert session_id_2 in session_ids

@pytest.mark.asyncio
async def test_regex_validation_errors(client):
    # Invalid Name (numbers/symbols)
    bad_name_payload = {
        "name": "Aarav123",
        "phone": "9820155432"
    }
    res_bad_name = await client.post("/api/customer/identify", json=bad_name_payload)
    assert res_bad_name.status_code == 422

    # Invalid Phone (too short / non-phone)
    bad_phone_payload = {
        "name": "Aarav Sharma",
        "phone": "12345"
    }
    res_bad_phone = await client.post("/api/customer/identify", json=bad_phone_payload)
    assert res_bad_phone.status_code == 422
