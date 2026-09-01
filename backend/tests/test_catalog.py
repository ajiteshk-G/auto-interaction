import pytest

@pytest.mark.asyncio
async def test_list_all_vehicles(client):
    response = await client.get("/api/catalog")
    assert response.status_code == 200
    vehicles = response.json()
    assert len(vehicles) >= 10
    
    ids = [v["id"] for v in vehicles]
    assert "thar_roxx" in ids
    assert "be_6e" in ids
    assert "scorpio_n" in ids
    assert "xuv700" in ids

@pytest.mark.asyncio
async def test_get_vehicle_detail(client):
    response = await client.get("/api/catalog/thar_roxx")
    assert response.status_code == 200
    data = response.json()
    assert "Thar ROXX" in data["name"]
    assert len(data["variants"]) >= 2
    assert "FSD" in str(data["key_highlights"]) or "Frequency" in str(data["key_highlights"])

@pytest.mark.asyncio
async def test_compare_vehicles(client):
    response = await client.post("/api/catalog/compare", json={"vehicle_ids": ["thar_roxx", "be_6e"]})
    assert response.status_code == 200
    compared = response.json()
    assert len(compared) == 2
    assert compared[0]["id"] == "thar_roxx"
    assert compared[1]["id"] == "be_6e"

@pytest.mark.asyncio
async def test_dealerships(client):
    response = await client.get("/api/catalog/dealerships")
    assert response.status_code == 200
    dealers = response.json()
    assert len(dealers) >= 3
    assert any("Bayview" in d["name"] for d in dealers)
