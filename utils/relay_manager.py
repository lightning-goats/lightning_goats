import asyncio
import json
import logging
from typing import List, Set, Optional
import websockets
from websockets.exceptions import ConnectionClosed
from config import DEFAULT_RELAYS

logger = logging.getLogger(__name__)

class RelayManager:
    def __init__(self, relays: List[str] = None):
        self.relays = relays or DEFAULT_RELAYS.copy()
        self.connections: Set[websockets.WebSocketClientProtocol] = set()
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Connect to all configured relays."""
        async with self._lock:
            for relay_url in self.relays:
                try:
                    websocket = await websockets.connect(relay_url)
                    self.connections.add(websocket)
                    logger.info(f"Connected to relay: {relay_url}")
                except Exception as e:
                    logger.error(f"Failed to connect to relay {relay_url}: {e}")

    async def disconnect(self) -> None:
        """Disconnect from all relays."""
        async with self._lock:
            for websocket in self.connections:
                try:
                    await websocket.close()
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")
            self.connections.clear()

    async def publish_event(self, event: dict) -> List[str]:
        """Publish an event to all connected relays."""
        successful_relays = []
        message = json.dumps(["EVENT", event])

        for websocket in self.connections.copy():
            try:
                await websocket.send(message)
                response = await websocket.recv()
                if "OK" in response:
                    successful_relays.append(websocket.url)
            except ConnectionClosed:
                self.connections.remove(websocket)
            except Exception as e:
                logger.error(f"Error publishing to relay {websocket.url}: {e}")

        return successful_relays

    async def subscribe(self, filters: List[dict]) -> Optional[dict]:
        """Subscribe to events matching the given filters."""
        subscription_id = "cyberherd_sub"
        message = json.dumps(["REQ", subscription_id, *filters])

        for websocket in self.connections.copy():
            try:
                await websocket.send(message)
                while True:
                    response = await websocket.recv()
                    event_data = json.loads(response)
                    if event_data[0] == "EVENT" and event_data[1] == subscription_id:
                        return event_data[2]
            except ConnectionClosed:
                self.connections.remove(websocket)
            except Exception as e:
                logger.error(f"Error in subscription: {e}")

        return None
