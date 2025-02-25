import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_convert_usd_to_sats():
    response = client.get("/convert/1.0")
    assert response.status_code == 200
    assert "sats" in response.json()
    assert isinstance(response.json()["sats"], int)
