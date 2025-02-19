import logging
import json
import math
from typing import Dict, Optional
from config import config, TRIGGER_AMOUNT_SATS
from services.external_api import ExternalAPIService
from services.notifier import NotifierService
from services.database import DatabaseService
from services.messaging_service import MessagingService

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
        self.messaging = MessagingService()

    async def process_payment(self, payment_data: Dict):
        """Process incoming payment data from websocket."""
        if config['DEBUG']:
            logger.debug(f"Processing payment data: {payment_data}")

        try:
            payment = payment_data.get('payment', {})
            payment_amount = payment.get('amount', 0)
            sats_received = payment_amount // 1000
            wallet_balance = payment_data.get('wallet_balance', 0)
            
            # Update balance
            self.balance = math.floor(wallet_balance / 1000)
            
            if config['DEBUG']:
                logger.debug(f"Payment amount: {payment_amount}, Sats received: {sats_received}")
                logger.debug(f"Wallet balance: {wallet_balance}, Updated balance: {self.balance}")

            if sats_received > 0:
                # Only handle payment logic, don't broadcast raw payment data
                await self._handle_received_payment(sats_received, payment)

        except Exception as e:
            logger.error(f"Error processing payment data: {e}", exc_info=True)
            raise

    async def _handle_received_payment(self, sats_received: int, payment: Dict):
        """Handle payment processing and notifications."""
        try:
            # Update goat sats counter
            await self.external_api.update_goat_sats(sats_received)
            
            # Calculate difference for notification
            difference = TRIGGER_AMOUNT_SATS - self.balance
            
            if not await self.external_api.get_feeder_status():
                if self.balance >= TRIGGER_AMOUNT_SATS:
                    await self._trigger_feeder_and_notify(sats_received)
                elif sats_received >= 10:
                    # Send formatted notification for regular payment
                    message, _ = await self.messaging.make_messages(
                        config['NOS_SEC'],
                        sats_received,
                        difference,
                        "sats_received"
                    )
                    await self.notifier.broadcast(message)
            else:
                logger.info("Feeder override is ON")

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
