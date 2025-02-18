import asyncio
import logging
import websockets
from typing import Optional, Set
from asyncio import Lock, Event
from fastapi.websockets import WebSocket
from websockets.exceptions import (
    ConnectionClosedError,
    ConnectionClosedOK,
    InvalidURI,
    InvalidHandshake,
)

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self, uri: str, logger: logging.Logger, max_retries: Optional[int] = None):
        self.uri = uri
        self.logger = logger
        self.max_retries = max_retries
        self.websocket = None
        self.lock = Lock()
        self.should_run = True
        self.connected = Event()
        self.listen_task = None
        self._retry_count = 0
        self.connected_clients: Set[WebSocket] = set()

    # ...existing WebSocketManager methods...

    async def broadcast(self, message: str):
        """Send a message to all connected clients."""
        if not message:
            self.logger.warning("Attempted to send an empty message. Skipping.")
            return

        if self.connected_clients:
            self.logger.info(f"Broadcasting message to {len(self.connected_clients)} clients: {message}")
            for client in self.connected_clients.copy():
                try:
                    await client.send_text(message)
                except Exception as e:
                    self.logger.warning(f"Failed to send message to client: {e}")
                    self.connected_clients.remove(client)
        else:
            self.logger.debug("No connected clients to send messages to.")

    async def add_client(self, websocket: WebSocket):
        """Add a new WebSocket client."""
        await websocket.accept()
        self.connected_clients.add(websocket)
        self.logger.info(f"Client connected. Total clients: {len(self.connected_clients)}")

    def remove_client(self, websocket: WebSocket):
        """Remove a WebSocket client."""
        self.connected_clients.remove(websocket)
        self.logger.info(f"Client disconnected. Total clients: {len(self.connected_clients)}")
