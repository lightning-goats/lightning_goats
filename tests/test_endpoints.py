from fastapi.testclient import TestClient
from app import app
import pytest
from .test_config import setup_test_env

# Set up test environment
setup_test_env()
client = TestClient(app)

def test_get_balance():
    """Test balance endpoint."""
    response = client.get("/balance")  # This should now work
    assert response.status_code == 200
    assert "balance" in response.json()

def test_cyberherd_spots():
    """Test CyberHerd spots endpoint."""
    response = client.get("/cyberherd/spots_remaining")
    assert response.status_code == 200
    assert "spots_remaining" in response.json()

def test_trigger_amount():
    """Test trigger amount endpoint."""
    response = client.get("/trigger_amount")
    assert response.status_code == 200
    assert "trigger_amount" in response.json()

def test_create_payment():
    """Test payment creation endpoint."""
    payment_data = {"balance": 1000}
    response = client.post("/payment", json=payment_data)
    assert response.status_code == 200
    assert "payment_request" in response.json()

def test_convert_amount():
    """Test USD to sats conversion endpoint."""
    response = client.get("/convert/1.0")
    assert response.status_code == 200
    assert "sats" in response.json()
