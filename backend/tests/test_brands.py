import pytest
import io
from fastapi.testclient import TestClient
from app.main import app
from app.services.brand_service import BrandService

client = TestClient(app)

def test_list_brands():
    response = client.get("/api/brands")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    brand_ids = [b["id"] for b in data]
    assert "mahindra" in brand_ids
    assert "hyundai" in brand_ids
    assert "maruti_suzuki" in brand_ids

def test_get_active_brand():
    response = client.get("/api/brands/active")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "vehicles" in data
    assert len(data["vehicles"]) > 0

def test_switch_brand_and_dynamic_catalog():
    # 1. Switch to Hyundai
    switch_res = client.post("/api/brands/active", json={"brand_id": "hyundai"})
    assert switch_res.status_code == 200
    hyundai_brand = switch_res.json()
    assert hyundai_brand["id"] == "hyundai"
    assert hyundai_brand["primary_color"] == "#002c5f"

    # 2. Check that /api/catalog now dynamically returns Hyundai vehicles
    cat_res = client.get("/api/catalog")
    assert cat_res.status_code == 200
    vehicles = cat_res.json()
    v_ids = [v["id"] for v in vehicles]
    assert "ioniq_5" in v_ids
    assert "creta" in v_ids

    # 3. Switch back to Mahindra
    switch_back = client.post("/api/brands/active", json={"brand_id": "mahindra"})
    assert switch_back.status_code == 200
    assert switch_back.json()["id"] == "mahindra"

    # 4. Check that /api/catalog returns Mahindra vehicles
    cat_res2 = client.get("/api/catalog")
    v_ids2 = [v["id"] for v in cat_res2.json()]
    assert "thar_roxx" in v_ids2

def test_vehicle_edit_and_source_of_truth():
    # Update vehicle spec
    update_res = client.put(
        "/api/brands/hyundai/vehicles/ioniq_5",
        json={
            "tagline": "Custom Verified Source of Truth Tagline",
            "price_range": "₹48.00 Lakh"
        }
    )
    assert update_res.status_code == 200
    updated_v = update_res.json()
    assert updated_v["tagline"] == "Custom Verified Source of Truth Tagline"
    assert updated_v["price_range"] == "₹48.00 Lakh"
    assert updated_v["is_custom_source_of_truth"] is True

def test_upload_vehicle_image_source_of_truth():
    # Create fake image bytes
    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    
    response = client.post(
        "/api/brands/hyundai/upload-vehicle-image",
        data={"vehicle_id": "ioniq_5"},
        files={"image": ("ioniq5_user_upload.png", io.BytesIO(fake_png), "image/png")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_custom_source_of_truth"] is True
    assert "/uploads/hyundai/vehicles/" in data["hero_image"]
