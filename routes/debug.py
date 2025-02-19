from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import logging
from config import config, TRIGGER_AMOUNT_SATS
from services.payment_processor import PaymentProcessor
from dependencies import get_payment_processor
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter()

class DebugPayment(BaseModel):
    amount: int
    memo: Optional[str] = "debug payment"

@router.post("/simulate_payment")
async def simulate_payment(
    payment: DebugPayment,
    processor: PaymentProcessor = Depends(get_payment_processor)
):
    """Simulate an incoming payment."""
    if not config['DEBUG']:
        raise HTTPException(status_code=403, detail="Debug endpoints only available in DEBUG mode")

    try:
        # Create simulated payment data
        payment_data = {
            "wallet_balance": payment.amount,  # Balance in sats
            "payment": {
                "amount": payment.amount * 1000,  # Amount in millisats
                "memo": payment.memo,
                "status": "success",
                "pending": False,
                "time": 1234567890,
                "fee": 0,
            }
        }

        logger.info(f"Simulating payment: {payment_data}")
        await processor.process_payment(payment_data)
        
        return {
            "status": "success",
            "message": f"Simulated payment of {payment.amount} sats processed",
            "payment_request": "lnbc..."
        }

    except Exception as e:
        logger.error(f"Error simulating payment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trigger_amount")
async def get_trigger_amount():
    """Get trigger amount for testing."""
    return {"trigger_amount": TRIGGER_AMOUNT_SATS}

@router.get("/feeder_status")
async def get_feeder_status():
    """Get feeder status for testing."""
    return {"status": False}

@router.get("/cyberherd/list")
async def get_cyberherd():
    """Get CyberHerd list for testing."""
    return {"members": []}
