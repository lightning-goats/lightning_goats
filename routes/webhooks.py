from fastapi import APIRouter, HTTPException, Depends
import logging
from typing import Dict
from services.payment_processor import PaymentProcessor
from dependencies import get_payment_processor

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/payment")
async def payment_webhook(
    payment_data: Dict,
    processor: PaymentProcessor = Depends(get_payment_processor)
):
    """Handle incoming payment webhook data."""
    try:
        if config['DEBUG']:
            logger.debug(f"Received payment webhook data: {payment_data}")
            
        await processor.process_payment(payment_data)
        
        if config['DEBUG']:
            logger.debug("Successfully processed payment webhook")
            
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error processing payment webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process payment webhook")

@router.post("/lnurl")
async def lnurl_webhook(
    data: Dict,
    processor: PaymentProcessor = Depends(get_payment_processor)
):
    """Handle incoming LNURL webhook data."""
    try:
        if config['DEBUG']:
            logger.debug(f"Received LNURL webhook data: {data}")
            
        # Process LNURL-specific webhook data
        await processor.process_lnurl_data(data)
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error processing LNURL webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process LNURL webhook")
