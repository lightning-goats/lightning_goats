from fastapi import APIRouter, WebSocket, Depends
from services.websocket_manager import WebSocketManager
from services.payment_processor import PaymentProcessor
from services.messaging_service import MessagingService
import logging
import asyncio
import random
from config import config
from dependencies import _external_api, _notifier, _db

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
payment_processor = PaymentProcessor(_external_api, _notifier, _db)

# Initialize WebSocket manager with payment processor
websocket_manager = WebSocketManager(
    uri=config['HERD_WEBSOCKET'],
    payment_processor=payment_processor,
    logger=logger
)

@router.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for client connections."""
    await websocket.accept()
    try:
        await websocket_manager.register(websocket)
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message received: {data}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket_manager.unregister(websocket)

@router.get("/ws")
async def get_ws_info():
    """Get WebSocket connection information."""
    return {"message": "WebSocket endpoint available at /ws/"}

async def periodic_informational_messages():
    """Send an informational message via WebSockets with a 40% chance every minute."""
    messaging = MessagingService()
    while True:
        await asyncio.sleep(60)
        if random.random() < 0.4:  # 40% chance
            message, _ = await messaging.make_messages(
                config['NOS_SEC'], 
                0, 
                0, 
                "interface_info"
            )
            await websocket_manager.broadcast(message)

# Start periodic messages
@router.on_event("startup")
async def start_periodic_messages():
    asyncio.create_task(periodic_informational_messages())
