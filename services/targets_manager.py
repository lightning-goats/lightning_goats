import logging
import math
from typing import List, Dict
from config import config

logger = logging.getLogger(__name__)

class TargetsManager:
    def __init__(self):
        self.predefined_wallet = {
            'wallet': config['PREDEFINED_WALLET_ADDRESS'],
            'alias': config['PREDEFINED_WALLET_ALIAS'],
            'percent': 90
        }
        self.max_allocation = 10

    async def calculate_targets(self, new_targets_data: List[Dict]) -> Dict:
        """Calculate target allocations for CyberHerd members."""
        try:
            non_predefined = [
                item for item in new_targets_data 
                if item['wallet'] != config['PREDEFINED_WALLET_ADDRESS']
            ]
            
            combined_wallets = []
            for item in new_targets_data:
                if item['wallet'] != config['PREDEFINED_WALLET_ADDRESS']:
                    combined_wallets.append({
                        'wallet': item['wallet'],
                        'alias': item.get('alias', 'Unknown'),
                        'payouts': item.get('payouts', 1.0)
                    })

            total_payouts = sum(w['payouts'] for w in combined_wallets) or 1
            min_percent_per_wallet = 1
            max_wallets_allowed = math.floor(self.max_allocation / min_percent_per_wallet)

            if len(combined_wallets) > max_wallets_allowed:
                combined_wallets = sorted(
                    combined_wallets,
                    key=lambda x: x['payouts'],
                    reverse=True
                )[:max_wallets_allowed]
                total_payouts = sum(w['payouts'] for w in combined_wallets) or 1

            # Initialize with minimum percentages
            for wallet in combined_wallets:
                wallet['percent'] = min_percent_per_wallet
            allocated = min_percent_per_wallet * len(combined_wallets)
            remaining_allocation = self.max_allocation - allocated

            # Calculate proportional allocations
            additional_allocations = []
            for wallet in combined_wallets:
                prop = wallet['payouts'] / total_payouts
                additional = prop * remaining_allocation
                additional_allocations.append((wallet, additional))

            # Apply floor of additional allocations
            for wallet, additional in additional_allocations:
                add_percent = math.floor(additional)
                wallet['percent'] += add_percent

            # Handle leftover percentage points
            allocated_percent = sum(w['percent'] for w in combined_wallets)
            leftover = self.max_allocation - allocated_percent

            if leftover > 0:
                remainders = [
                    (additional - math.floor(additional), wallet)
                    for wallet, additional in additional_allocations
                ]
                remainders.sort(reverse=True, key=lambda x: x[0])
                
                num_wallets = len(remainders)
                if num_wallets > 0:
                    for i in range(int(leftover)):
                        index = i % num_wallets
                        remainders[index][1]['percent'] += 1

            # Finalize targets list
            targets_list = combined_wallets
            self.predefined_wallet['percent'] = 100 - sum(w['percent'] for w in targets_list)
            targets_list.insert(0, self.predefined_wallet)

            return {"targets": targets_list}

        except Exception as e:
            logger.error(f"Error calculating targets: {e}")
            raise
