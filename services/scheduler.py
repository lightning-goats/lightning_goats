import asyncio
import logging
from datetime import datetime, timedelta
from services.database import DatabaseService
from services.external_api import ExternalAPIService
from config import config

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self, database: DatabaseService, external_api: ExternalAPIService):
        self.database = database
        self.external_api = external_api
        self.balance = 0

    async def schedule_daily_reset(self):
        """Schedule and handle daily reset tasks."""
        while True:
            now = datetime.utcnow()
            next_midnight = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            sleep_seconds = (next_midnight - now).total_seconds()
            await asyncio.sleep(sleep_seconds)

            try:
                # Reset cyber herd
                await self.database.execute("DELETE FROM cyber_herd")
                logger.info("CyberHerd table cleared successfully")

                # Reset targets
                await self.external_api.reset_cyberherd_targets()
                logger.info("CyberHerd targets reset successfully")

                # Get and process current balance
                balance = await self.external_api.get_balance(force_refresh=True)
                if balance > 0:
                    payment_request = await self.external_api.create_invoice(
                        amount=balance,
                        memo='Daily Reset - Herd Wallet',
                        key=config['HERD_KEY']
                    )
                    await self.external_api.pay_invoice(
                        payment_request=payment_request,
                        key=config['HERD_KEY']
                    )
                    logger.info(f"Daily reset payment completed: {balance} sats")

            except Exception as e:
                logger.error(f"Error in daily reset: {e}")
