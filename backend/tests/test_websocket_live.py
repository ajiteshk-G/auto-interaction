import pytest
from app.main import app
from starlette.testclient import TestClient

def test_websocket_live_chat_and_tools():
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
                    if msg["type"] in ["ASSISTANT_RESPONSE", "UI_ACTION"]:
                        break
                except Exception:
                    break
            assert any(t in received_types for t in ["ASSISTANT_RESPONSE", "UI_ACTION", "VIDEO_CHUNK", "AUDIO_CHUNK"])
