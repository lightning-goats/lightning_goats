import logging
from typing import List, Dict, Tuple
from services.database import DatabaseService
from services.notifier import NotifierService
from services.cyberherd_manager import CyberHerdManager
from config import MAX_HERD_SIZE

logger = logging.getLogger(__name__)

class MemberProcessor:
    def __init__(
        self,
        database: DatabaseService,
        notifier: NotifierService,
        cyberherd_manager: CyberHerdManager
    ):
        self.database = database
        self.notifier = notifier
        self.cyberherd_manager = cyberherd_manager

    async def process_members(
        self,
        members_data: List[Dict]
    ) -> Tuple[List[Dict], List[Dict]]:
        """Process new and existing CyberHerd members."""
        members_to_notify = []
        targets_to_update = []

        query = "SELECT COUNT(*) as count FROM cyber_herd"
        result = await self.database.fetch_one(query)
        current_herd_size = result['count']

        if current_herd_size >= MAX_HERD_SIZE:
            logger.info(f"Herd full: {current_herd_size} members")
            return [], []

        for member in members_data:
            try:
                pubkey = member['pubkey']
                check_query = """
                    SELECT COUNT(*) as count, kinds, notified 
                    FROM cyber_herd 
                    WHERE pubkey = :pubkey
                """
                existing = await self.database.fetch_one(
                    check_query, 
                    {"pubkey": pubkey}
                )

                if existing['count'] == 0 and current_herd_size < MAX_HERD_SIZE:
                    await self._process_new_member(
                        member,
                        members_to_notify,
                        targets_to_update
                    )
                    current_herd_size += 1
                elif existing['count'] > 0:
                    await self._process_existing_member(
                        member,
                        existing,
                        members_to_notify,
                        targets_to_update
                    )

            except Exception as e:
                logger.error(f"Error processing member {member.get('pubkey')}: {e}")
                continue

        return members_to_notify, targets_to_update

    async def _process_new_member(
        self,
        member: Dict,
        members_to_notify: List,
        targets_to_update: List
    ):
        """Process a new CyberHerd member."""
        success, msg = await self.cyberherd_manager.process_new_member(
            member_data=member,
            kinds_int=self._parse_kinds(member.get('kinds', [])),
            current_herd_size=0  # This will be calculated in process_new_member
        )
        
        if success:
            members_to_notify.append({
                'pubkey': member['pubkey'],
                'type': 'new_member',
                'data': member
            })
            
            if member.get('lud16'):
                targets_to_update.append({
                    'wallet': member['lud16'],
                    'alias': member['pubkey'],
                    'payouts': member.get('payouts', 0.0)
                })

    async def _process_existing_member(
        self,
        member: Dict,
        existing: Dict,
        members_to_notify: List,
        targets_to_update: List
    ):
        """Process an existing CyberHerd member."""
        success, msg = await self.cyberherd_manager.process_existing_member(
            member_data=member,
            kinds_int=self._parse_kinds(member.get('kinds', [])),
            current_kinds=self._parse_kinds(existing.get('kinds', []))
        )
        
        if success and existing['notified'] is None:
            members_to_notify.append({
                'pubkey': member['pubkey'],
                'type': 'existing_member',
                'data': member
            })

    def _parse_kinds(self, kinds) -> List[int]:
        """Parse kinds from string or list to integer list."""
        if isinstance(kinds, str):
            return [int(k.strip()) for k in kinds.split(',') if k.strip().isdigit()]
        elif isinstance(kinds, list):
            return [int(k) for k in kinds if str(k).isdigit()]
        return []
