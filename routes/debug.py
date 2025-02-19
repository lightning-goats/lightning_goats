from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import logging
from config import config
from services.payment_processor import PaymentProcessor
from dependencies import get_payment_processor
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter()

class SimulatedPayment(BaseModel):
    amount: int  # Amount in millisats
    memo: str = "debug payment"
    is_cyberherd: bool = False
    pubkey: Optional[str] = None
    event_id: Optional[str] = None

@router.post("/simulate_payment")
async def simulate_payment(
    payment: SimulatedPayment,
    processor: PaymentProcessor = Depends(get_payment_processor)
):
    """Simulate an incoming payment (only works in DEBUG mode)."""
    if not config['DEBUG']:
        raise HTTPException(status_code=403, detail="Debug endpoints only available in DEBUG mode")

    try:
        # Create simulated payment data
        payment_data = {
            "wallet_balance": payment.amount,  # Use full amount as balance for simulation
            "payment": {
                "amount": payment.amount,
                "memo": payment.memo,
                "status": "success",
                "pending": False,
                "time": 1234567890,
                "fee": 0,
            }
        }

        # Add Nostr data if this is a CyberHerd payment
        if payment.is_cyberherd and payment.pubkey and payment.event_id:
            payment_data["payment"]["extra"] = {
                "nostr": {
                    "pubkey": payment.pubkey,
                    "id": payment.event_id,
                    "kind": 9734,
                    "tags": [["e", payment.event_id]],
                    "content": "#cyberherd"
                }
            }

        logger.debug(f"Simulating payment: {payment_data}")
        await processor.process_payment(payment_data)
        
        return {
            "status": "success",
            "message": f"Simulated payment of {payment.amount/1000} sats processed",
            "data": payment_data
        }

    except Exception as e:
        logger.error(f"Error simulating payment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/simulate_zap")
async def simulate_zap(
    amount: int = 21000,  # 21 sats in millisats
    processor: PaymentProcessor = Depends(get_payment_processor)
):
    """Simulate a zap payment with CyberHerd tag (only works in DEBUG mode)."""
    if not config['DEBUG']:
        raise HTTPException(status_code=403, detail="Debug endpoints only available in DEBUG mode")

    # Example pubkey and event_id for testing
    test_payment = SimulatedPayment(
        amount=amount,
        memo="debug zap",
        is_cyberherd=True,
        pubkey="dd9b879f25694204a76e53427e10dfe765fd4d0f27510a1b95542c28ad82c297",
        event_id="fa75c355e6c39adb41e2576af7c94eccf5e0d74ff1f5b3831baef5e7a6ac78c6"
    )
    
    return await simulate_payment(test_payment, processor)
