from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..services.websocket_manager import WebSocketManager
from ..config import config
import logging
import asyncio
import random
from ..services.messaging_service import MessagingService

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize WebSocket manager
websocket_manager = WebSocketManager(
    uri=config['HERD_WEBSOCKET'],
    logger=logger
)

@router.websocket("/ws/")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections."""
    await websocket_manager.add_client(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.remove_client(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.remove_client(websocket)

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

# Add startup event handler
@router.on_event("startup")
async def start_periodic_messages():
    asyncio.create_task(periodic_informational_messages())
