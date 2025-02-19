import logging
import json
import math
from typing import Dict, Optional
from config import config, TRIGGER_AMOUNT_SATS
from services.external_api import ExternalAPIService
from services.notifier import NotifierService
from services.database import DatabaseService

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
                await self.handle_payment_received(sats_received, payment)

        except Exception as e:
            logger.error(f"Error processing payment data: {e}", exc_info=True)
            raise

    async def handle_payment_received(self, sats_received: int, payment: Dict):
        """Handle received payment and its side effects."""
        try:
            # Update goat sats counter
            await self.external_api.update_goat_sats(sats_received)
            
            nostr_data = self.extract_nostr_data(payment)
            feeder_triggered = False
            
            if nostr_data and sats_received >= 10:
                await self.handle_nostr_payment(nostr_data, sats_received)

            if sats_received > 0 and not await self.external_api.get_feeder_status():
                if self.balance >= TRIGGER_AMOUNT_SATS:
                    feeder_triggered = await self.trigger_feeder_and_reset(sats_received)

                if not feeder_triggered:
                    difference = TRIGGER_AMOUNT_SATS - self.balance
                    if sats_received >= 10:
                        await self.notifier.send_sats_received_notification(
                            sats_received=sats_received,
                            difference=difference
                        )
            else:
                logger.info("Feeder override is ON or payment amount is non-positive")

        except Exception as e:
            logger.error(f"Error handling payment: {e}", exc_info=True)
            raise

    def extract_nostr_data(self, payment: Dict) -> Optional[Dict]:
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

    async def trigger_feeder_and_reset(self, sats_received: int) -> bool:
        """Trigger feeder and reset wallet if successful."""
        if await self.external_api.trigger_feeder():
            logger.info("Feeder triggered successfully")
            
            await self.notifier.send_feeder_notification(sats_received)
            
            # Reset wallet
            status = await self.external_api.pay_invoice(
                await self.external_api.create_invoice(
                    amount=self.balance,
                    memo='Reset Herd Wallet',
                    key=config['HERD_KEY']
                ),
                key=config['HERD_KEY']
            )
            
            return True
            
        return False
