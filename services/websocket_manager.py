import asyncio
import logging
import json
import websockets
from typing import Optional, Set
from asyncio import Lock, Event
from fastapi.websockets import WebSocket
from websockets.exceptions import (
    ConnectionClosedError,
    ConnectionClosedOK,
    InvalidURI,
    InvalidHandshake,
    ConnectionClosed,
)
from config import config

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(
        self,
        uri: str,
        payment_processor,  # Add payment processor
        logger: Optional[logging.Logger] = None
    ):
        self.uri = uri
        self.payment_processor = payment_processor
        self.logger = logger or logging.getLogger(__name__)
        self.connection: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.clients: Set[WebSocket] = set()
        self._connection_event = asyncio.Event()
        self.logger.debug(f"WebSocketManager initialized with URI: {uri}")

    async def connect(self) -> None:
        """Connect to the WebSocket server."""
        while True:
            try:
                self.logger.debug(f"Attempting to connect to WebSocket server: {self.uri}")
                self.connection = await websockets.connect(self.uri)
                self.connected = True
                self._connection_event.set()
                self.logger.info(f"Connected to WebSocket server: {self.uri}")
                
                # Keep the connection alive and handle messages
                while True:
                    try:
                        message = await self.connection.recv()
                        self.logger.debug(f"Received WebSocket message: {message}")
                        await self._handle_message(message)
                    except ConnectionClosed:
                        self.logger.warning("WebSocket connection closed")
                        break
                    except Exception as e:
                        self.logger.error(f"Error handling message: {e}", exc_info=True)
                
            except Exception as e:
                self.logger.error(f"WebSocket connection error: {e}", exc_info=True)
                self.connected = False
                self._connection_event.clear()
            
            self.logger.debug("Waiting 5 seconds before reconnection attempt")
            await asyncio.sleep(5)

    async def disconnect(self) -> None:
        """Disconnect from the WebSocket server."""
        if self.connection:
            self.logger.info("Disconnecting from WebSocket server")
            await self.connection.close()
            self.connected = False
            self._connection_event.clear()

    async def wait_for_connection(self, timeout: Optional[float] = None) -> bool:
        """Wait for the WebSocket connection to be established."""
        try:
            await asyncio.wait_for(self._connection_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def _handle_message(self, message: str) -> None:
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)
            
            # Process payment data
            await self.payment_processor.process_payment(data)
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse message: {message}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def broadcast(self, message: str) -> None:
        """Broadcast a message to all connected clients."""
        if config['DEBUG']:
            logger.debug(f"Broadcasting formatted message: {message}")
            
        if not self.clients:
            logger.debug("No clients connected to broadcast message")
            return

        failed_clients = []
        for client in self.clients.copy():
            try:
                await client.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}", exc_info=True)
                failed_clients.append(client)

        # Remove failed clients
        for client in failed_clients:
            self.clients.remove(client)

    async def register(self, websocket: WebSocket) -> None:
        """Register a new client connection."""
        self.clients.add(websocket)
        self.logger.info(f"Client connected. Total clients: {len(self.clients)}")

    async def unregister(self, websocket: WebSocket) -> None:
        """Unregister a client connection."""
        self.clients.remove(websocket)
        self.logger.info(f"Client disconnected. Total clients: {len(self.clients)}")
