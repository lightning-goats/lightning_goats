import logging
import json
import math
from typing import Dict, Optional
from config import config, TRIGGER_AMOUNT_SATS
from services.external_api import ExternalAPIService
from services.notifier import NotifierService
from services.database import DatabaseService
from services.messaging_service import MessagingService
from asyncio import Lock

logger = logging.getLogger(__name__)

class PaymentProcessor:
    def __init__(
        self,
        external_api: ExternalAPIService,
        notifier: NotifierService,
        database: DatabaseService
    ):
        self.external_api = external_api
        self.notifier = notifier
        self.database = database
        self.balance = 0
        self.lock = Lock()
        self.messaging = MessagingService()

    async def process_payment(self, payment_data: Dict):
        """Process incoming payment data from websocket."""
        try:
            payment = payment_data.get('payment', {})
            payment_amount_msats = payment.get('amount', 0)
            sats_received = payment_amount_msats // 1000
            
            # Update balance - wallet_balance is already in sats
            async with self.lock:
                self.balance = payment_data.get('wallet_balance', 0)
            
            logger.info("\n=== Payment Received ===")
            logger.info(f"Amount: {sats_received} sats")
            logger.info(f"Balance: {self.balance} sats")
            logger.info("=====================\n")

            if sats_received > 0:
                await self._handle_received_payment(sats_received, payment)

        except Exception as e:
            logger.error(f"Error processing payment data: {e}", exc_info=True)
            raise

    async def _handle_received_payment(self, sats_received: int, payment: Dict):
        """Handle payment processing and notifications."""
        try:
            # Update goat sats counter
            await self.external_api.update_goat_sats(sats_received)
            
            # Calculate remaining sats needed for feeder trigger
            async with self.lock:
                difference = TRIGGER_AMOUNT_SATS - self.balance
                
                if not await self.external_api.get_feeder_status():
                    if self.balance >= TRIGGER_AMOUNT_SATS:
                        logger.info("\n🔔 TRIGGERING FEEDER 🔔")
                        if config['DEBUG']:
                            logger.info(f"Would trigger feeder and reset balance of {self.balance} sats")
                        else:
                            await self._trigger_feeder_and_notify(sats_received)
                    elif sats_received >= 10:
                        logger.info(f"Need {difference} more sats to trigger feeder")
                        message, _ = await self.messaging.make_messages(
                            config['NOS_SEC'],
                            sats_received,
                            difference,
                            "sats_received"
                        )
                        await self.notifier.broadcast(message)
                else:
                    logger.info("Feeder override is ON - skipping feeder trigger")

        except Exception as e:
            logger.error(f"Error handling payment: {e}", exc_info=True)
            raise

    def _extract_nostr_data(self, payment: Dict) -> Optional[Dict]:
        """Extract and validate Nostr data from payment."""
        try:
            nostr_data_raw = payment.get('extra', {}).get('nostr')
            if nostr_data_raw:
                return json.loads(nostr_data_raw)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in Nostr data")
        except Exception as e:
            logger.error(f"Error extracting Nostr data: {e}")
        return None

    async def _trigger_feeder_and_notify(self, sats_received: int) -> bool:
        """Trigger feeder and send notifications."""
        if await self.external_api.trigger_feeder():
            logger.info("Feeder triggered successfully")
            
            message, _ = await self.messaging.make_messages(
                config['NOS_SEC'],
                sats_received,
                0,
                "feeder_triggered"
            )
            await self.notifier.broadcast(message)
            
            # Reset wallet
            await self._reset_wallet()
            return True
            
        return False

    async def _reset_wallet(self):
        """Reset the wallet by creating and paying an invoice."""
        try:
            payment_request = await self.external_api.create_invoice(
                amount=self.balance,
                memo='Reset Herd Wallet',
                key=config['HERD_KEY']
            )
            await self.external_api.pay_invoice(
                payment_request=payment_request,
                key=config['HERD_KEY']
            )
            logger.info(f"Wallet reset successful. Amount: {self.balance}")
        except Exception as e:
            logger.error(f"Error resetting wallet: {e}")
