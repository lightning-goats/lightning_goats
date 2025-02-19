import logging
from typing import Set, Optional
from fastapi.websockets import WebSocket
import json
from config import config
from services.messaging_service import MessagingService

logger = logging.getLogger(__name__)

class NotifierService:
    def __init__(self):
        self.connected_clients: Set[WebSocket] = set()
        self.messaging = MessagingService()

    async def broadcast(self, message: str):
        """Send a message to all connected clients."""
        if not message:
            logger.warning("Attempted to send an empty message. Skipping.")
            return

        if config['DEBUG']:
            logger.debug(f"DEBUG mode - suppressing broadcast: {message}")
            return

        if self.connected_clients:
            logger.info(f"Broadcasting message to {len(self.connected_clients)} clients: {message}")
            failed_clients = []
            for client in self.connected_clients.copy():
                try:
                    await client.send_text(message)
                except Exception as e:
                    logger.warning(f"Failed to send message to client: {e}")
                    failed_clients.append(client)

            # Remove failed clients
            for client in failed_clients:
                self.connected_clients.remove(client)
        else:
            logger.debug("No connected clients to send messages to.")

    async def send_cyberherd_notification(self, member_data: dict, difference: int, spots_remaining: int):
        """Send a notification about CyberHerd activity."""
        try:
            message, raw_command_output = await self.messaging.make_messages(
                config['NOS_SEC'],
                member_data.get('amount', 0),
                difference,
                "cyber_herd",
                member_data,
                spots_remaining
            )
            await self.broadcast(message)
            return raw_command_output
        except Exception as e:
            logger.error(f"Error sending CyberHerd notification: {e}")
            raise

    async def send_feeder_notification(self, sats_received: int):
        """Send a notification about feeder activation."""
        try:
            message, _ = await self.messaging.make_messages(
                config['NOS_SEC'],
                sats_received,
                0,
                "feeder_triggered"
            )
            await self.broadcast(message)
        except Exception as e:
            logger.error(f"Error sending feeder notification: {e}")
            raise

    async def send_sats_received_notification(self, sats_received: int, difference: int):
        """Send a notification about received sats."""
        try:
            message, _ = await self.messaging.make_messages(
                config['NOS_SEC'],
                sats_received,
                difference,
                "sats_received"
            )
            await self.broadcast(message)
        except Exception as e:
            logger.error(f"Error sending sats received notification: {e}")
            raise
