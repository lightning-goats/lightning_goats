import asyncio
import websockets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def connect_websocket():
    """Connect to WebSocket server and display messages."""
    uri = "ws://localhost:8000/ws/"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("Connected to WebSocket server")
            
            while True:
                try:
                    message = await websocket.recv()
                    logger.info(f"Received message: {message}")
                except websockets.ConnectionClosed:
                    logger.error("Connection closed")
                    break
                except Exception as e:
                    logger.error(f"Error: {e}")
                    break
    except Exception as e:
        logger.error(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(connect_websocket())
