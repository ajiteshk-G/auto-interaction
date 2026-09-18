import pytest
from app.main import app
from starlette.testclient import TestClient

import asyncio
from tests.conftest import TestingSessionLocal, test_engine
from app.database import Base, get_db

async def _fake_bearer_token():
    return None, None

async def _override_get_db():
    async with TestingSessionLocal() as session:
        yield session

async def _init_mem_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

def test_websocket_live_chat_and_tools(monkeypatch):
    asyncio.run(_init_mem_db())
    monkeypatch.setattr("app.main.engine", test_engine)
    monkeypatch.setattr("app.main.AsyncSessionLocal", TestingSessionLocal)
    monkeypatch.setattr("app.routers.ws_live.get_bearer_token", _fake_bearer_token)
    monkeypatch.setattr("app.routers.ws_live.AsyncSessionLocal", TestingSessionLocal)
    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as client:
            with client.websocket_connect("/ws/live-audio") as websocket:
                # Check initial handshake
                data = websocket.receive_json()
                assert data["type"] == "SESSION_INITIALIZED"
                assert "name" in data["customer"] and len(data["customer"]["name"]) > 0

                # Send test drive query
                websocket.send_json({
                    "type": "USER_CHAT",
                    "text": "Can I book a test drive for Thar ROXX near Bandra tomorrow at 5pm?"
                })
                
                # We may receive VIDEO_CHUNK, AUDIO_CHUNK, UI_ACTION or ASSISTANT_RESPONSE
                received_types = []
                for _ in range(5):
                    try:
                        msg = websocket.receive_json()
                        received_types.append(msg["type"])
                        if msg["type"] in ["ASSISTANT_RESPONSE", "UI_ACTION", "AUDIO_CHUNK"]:
                            break
                    except Exception:
                        break
                assert any(t in received_types for t in ["ASSISTANT_RESPONSE", "UI_ACTION", "VIDEO_CHUNK", "AUDIO_CHUNK"])
    finally:
        app.dependency_overrides.clear()
