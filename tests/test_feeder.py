import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_feeder_status():
    response = client.get("/feeder/status")
    assert response.status_code == 200
    assert "feeder_override_enabled" in response.json()

def test_trigger_feeder():
    response = client.post("/feeder/trigger")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
