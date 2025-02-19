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
            logger.info("------------------------")
            logger.info("Processing new payment:")
            logger.info("------------------------")

        try:
            payment = payment_data.get('payment', {})
            payment_amount = payment.get('amount', 0)
            sats_received = payment_amount // 1000
            wallet_balance = payment_data.get('wallet_balance', 0)
            
            # Update balance
            self.balance = math.floor(wallet_balance / 1000)
            
            logger.info(f"Payment received: {sats_received} sats")
            logger.info(f"Current wallet balance: {self.balance} sats")

            if sats_received > 0:
                await self._handle_received_payment(sats_received, payment)

        except Exception as e:
            logger.error(f"Error processing payment data: {e}", exc_info=True)
            raise

    async def _handle_received_payment(self, sats_received: int, payment: Dict):
        """Handle payment processing and notifications."""
        try:
            logger.info(f"\n{'='*50}")
            logger.info(f"Processing payment of {sats_received} sats")
            logger.info(f"Current balance: {self.balance} sats")
            logger.info(f"Trigger amount: {TRIGGER_AMOUNT_SATS} sats")
            
            # Update goat sats counter
            await self.external_api.update_goat_sats(sats_received)
            
            # Check feeder status
            feeder_status = await self.external_api.get_feeder_status()
            if feeder_status:
                logger.info("Feeder override is ON - skipping feeder trigger")
                return

            # Check if we can trigger feeder
            if self.balance >= TRIGGER_AMOUNT_SATS:
                logger.info("\n🔔 TRIGGERING FEEDER 🔔")
                if config['DEBUG']:
                    logger.info("DEBUG MODE: Feeder would be triggered (but not in debug mode)")
                    logger.info(f"Would reset balance of {self.balance} sats")
                else:
                    await self._trigger_feeder_and_notify(sats_received)
            else:
                remaining = TRIGGER_AMOUNT_SATS - self.balance
                logger.info(f"Need {remaining} more sats to trigger feeder")

            logger.info(f"{'='*50}\n")

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
