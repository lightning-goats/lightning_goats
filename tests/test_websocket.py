import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_websocket_connection():
    with client.websocket_connect("/ws/") as websocket:
        websocket.send_text("Hello WebSocket")
        data = websocket.receive_text()
        assert data == "Message received: Hello WebSocket"
