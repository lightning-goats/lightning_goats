import logging
from typing import List, Dict, Optional, Tuple
from .database import DatabaseService
from .external_api import ExternalAPIService
from .notifier import NotifierService
from ..config import config, MAX_HERD_SIZE
from datetime import datetime, timedelta
import asyncio
from ..models import HookData

logger = logging.getLogger(__name__)

class CyberHerdManager:
    def __init__(
        self, 
        database: DatabaseService,
        external_api: ExternalAPIService,
        notifier: NotifierService
    ):
        self.database = database
        self.external_api = external_api
        self.notifier = notifier

    def calculate_payout(self, amount: float) -> float:
        """Calculate payout amount based on input amount."""
        units = (amount + 9) // 10  # Ceiling division for multiples of 10
        payout = units * 0.01  # Each 10 sats = 0.01 payout
        return max(0.3, min(payout, 1.0))

    async def process_new_member(
        self,
        member_data: Dict,
        kinds_int: List[int],
        current_herd_size: int
    ) -> Tuple[bool, Optional[str]]:
        """Process a new CyberHerd member."""
        if current_herd_size >= MAX_HERD_SIZE:
            return False, "Herd is full"

        if 9734 in kinds_int:
            member_data["payouts"] = self.calculate_payout(member_data.get("amount", 0))
        else:
            member_data["payouts"] = 0.0

        try:
            await self.database.add_cyber_herd_member(member_data)
            await self.notifier.send_cyberherd_notification(
                member_data,
                difference=0,  # You might want to calculate this
                spots_remaining=MAX_HERD_SIZE - current_herd_size - 1
            )
            return True, None
        except Exception as e:
            logger.error(f"Error processing new member: {e}")
            return False, str(e)

    async def process_existing_member(
        self,
        member_data: Dict,
        kinds_int: List[int],
        current_kinds: List[int]
    ) -> Tuple[bool, Optional[str]]:
        """Process an existing CyberHerd member."""
        try:
            payout_increment = 0.0
            if 9734 in kinds_int:
                zap_payout = self.calculate_payout(float(member_data.get("amount", 0)))
                payout_increment += zap_payout

            new_special_kinds = [k for k in [6, 7] if k in kinds_int and k not in current_kinds]
            for k in new_special_kinds:
                if k == 7:
                    payout_increment += 0.0
                elif k == 6:
                    payout_increment += 0.2

            if payout_increment > 0:
                update_data = {
                    "payouts": payout_increment,
                    "amount": member_data.get("amount", 0)
                }
                await self.database.update_cyber_herd_member(
                    member_data["pubkey"],
                    update_data
                )

            return True, None
        except Exception as e:
            logger.error(f"Error processing existing member: {e}")
            return False, str(e)

    async def distribute_rewards(self, total_amount: int):
        """Distribute rewards to CyberHerd members."""
        try:
            members = await self.database.get_cyber_herd_members()
            for member in members:
                if member["lud16"] and member["payouts"] > 0:
                    amount = int(member["payouts"] * total_amount)
                    if amount > 0:
                        await self.external_api.make_lnurl_payment(
                            lud16=member["lud16"],
                            msat_amount=amount * 1000,  # Convert to msats
                            description="CyberHerd Reward",
                            key=config['HERD_KEY']
                        )
                        await self.notifier.send_cyberherd_notification(
                            member,
                            difference=0,
                            spots_remaining=MAX_HERD_SIZE - len(members)
                        )
        except Exception as e:
            logger.error(f"Error distributing rewards: {e}")
            raise

    async def schedule_daily_reset(self):
        """Schedule a daily reset of the CyberHerd."""
        while True:
            now = datetime.utcnow()
            next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            sleep_seconds = (next_midnight - now).total_seconds()
            await asyncio.sleep(sleep_seconds)

            status = await self.reset_cyber_herd()
            
            if status['success']:
                await self.send_payment(self.balance)

    async def reset_cyber_herd(self):
        """Reset the CyberHerd and related data."""
        try:
            await self.database.execute("DELETE FROM cyber_herd")
            logger.info("CyberHerd table cleared successfully.")
            await self.external_api.reset_cyberherd_targets()
            return {
                "success": True,
                "message": "CyberHerd reset successfully"
            }
        except Exception as e:
            logger.error(f"Error resetting CyberHerd: {e}")
            return {"success": False, "message": str(e)}

    async def send_payment(self, balance: int):
        """Send a payment to reset the herd wallet."""
        try:
            payment_request = await self.external_api.create_invoice(
                amount=balance,
                memo='Reset Herd Wallet',
                key=config['HERD_KEY']
            )
            payment_status = await self.external_api.pay_invoice(
                payment_request=payment_request,
                key=config['HERD_KEY']
            )
            return {"success": True, "data": payment_status}
        except Exception as e:
            logger.error(f"Failed to send payment: {e}")
            return {"success": False, "message": str(e)}

    async def process_payment_data(self, hook_data: HookData):
        """Process incoming payment data from webhook."""
        try:
            payment_hash = hook_data.payment_hash
            description = hook_data.description
            amount = hook_data.amount

            # Fetch member by payment_hash
            member = await self.database.fetch_one(
                "SELECT * FROM cyber_herd WHERE event_id = :payment_hash",
                {"payment_hash": payment_hash}
            )

            if member:
                # Update notified field
                await self.database.update_notified_field(member["pubkey"], "success")

                # Send notification
                await self.notifier.send_sats_received_notification(
                    sats_received=int(amount),
                    difference=0  # You might want to calculate this
                )
            else:
                logger.warning(f"No CyberHerd member found with payment_hash: {payment_hash}")

        except Exception as e:
            logger.error(f"Error processing payment data: {e}")
            raise
