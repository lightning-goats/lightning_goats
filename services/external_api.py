import httpx
import logging
import json
from typing import Optional, Dict, Any, List
from config import config  # Change from relative to absolute import
from tenacity import retry, stop_after_attempt, wait_exponential
from utils.nostr_signing import sign_zap_event, sign_event, build_zap_event

logger = logging.getLogger(__name__)

class ExternalAPIService:
    def __init__(self):
        self.http_client = httpx.AsyncClient(http2=True)
        self.lnbits_url = config['LNBITS_URL']
        self.openhab_url = config['OPENHAB_URL']
        self.auth = (config['OH_AUTH_1'], '')

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def create_invoice(self, amount: int, memo: str, key: str) -> str:
        """Create a Lightning invoice."""
        try:
            url = f"{self.lnbits_url}/api/v1/payments"
            headers = {
                "X-API-KEY": key,
                "Content-Type": "application/json"
            }
            data = {
                "out": False,
                "amount": amount,
                "memo": memo,
            }
            response = await self.http_client.post(url, json=data, headers=headers)
            response.raise_for_status()
            return response.json()['payment_request']
        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def pay_invoice(self, payment_request: str, key: str) -> Dict:
        """Pay a Lightning invoice."""
        try:
            url = f"{self.lnbits_url}/api/v1/payments"
            headers = {
                "X-API-KEY": key,
                "Content-Type": "application/json"
            }
            data = {
                "out": True,
                "bolt11": payment_request
            }
            response = await self.http_client.post(url, json=data, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error paying invoice: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_feeder_status(self) -> bool:
        """Check if feeder override is enabled."""
        try:
            response = await self.http_client.get(
                f'{self.openhab_url}/rest/items/FeederOverride/state',
                auth=self.auth
            )
            response.raise_for_status()
            return response.text.strip() == 'ON'
        except Exception as e:
            logger.error(f"Error checking feeder status: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def trigger_feeder(self) -> bool:
        """Trigger the feeder."""
        try:
            response = await self.http_client.post(
                f'{self.openhab_url}/rest/rules/88bd9ec4de/runnow',
                auth=self.auth
            )
            response.raise_for_status()
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error triggering feeder: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def make_lnurl_payment(
        self,
        lud16: str,
        msat_amount: int,
        description: str = "LNURL Payment",
        key: str = None
    ) -> Optional[dict]:
        """Make an LNURL payment."""
        try:
            local_headers = {
                "accept": "application/json",
                "X-API-KEY": key or config['HERD_KEY'],
                "Content-Type": "application/json"
            }
            
            # Scan LNURL
            lnurl_scan_url = f"{self.lnbits_url}/api/v1/lnurlscan/{lud16}"
            logger.info(f"Scanning LNURL: {lnurl_scan_url}")
            lnurl_resp = await self.http_client.get(lnurl_scan_url, headers=local_headers)
            lnurl_resp.raise_for_status()
            lnurl_data = lnurl_resp.json()

            # Validate amount constraints
            if not (lnurl_data["minSendable"] <= msat_amount <= lnurl_data["maxSendable"]):
                logger.error(
                    f"{lud16}: {msat_amount} msat is out of bounds "
                    f"(min: {lnurl_data['minSendable']}, max: {lnurl_data['maxSendable']})"
                )
                return None

            # Prepare payment payload
            payment_payload = {
                "description_hash": lnurl_data["description_hash"],
                "callback": lnurl_data["callback"],
                "amount": msat_amount,
                "memo": description,
                "description": description
            }

            # Handle optional comment
            comment_allowed = lnurl_data.get("commentAllowed", 0)
            if comment_allowed > 0:
                payment_payload["comment"] = description

            # Handle Nostr zaps if allowed
            if lnurl_data.get("allowsNostr") and lnurl_data.get("nostrPubkey"):
                zapped_pubkey = lnurl_data["nostrPubkey"]
                zapper_pubkey = config['HEX_KEY']
                signed_event = await sign_zap_event(
                    msat_amount=msat_amount,
                    zapper_pubkey=zapper_pubkey,
                    zapped_pubkey=zapped_pubkey,
                    private_key_hex=config['NOS_SEC'],
                    content=description
                )
                payment_payload["nostr"] = json.dumps(signed_event)

            # Make payment
            payment_url = f"{self.lnbits_url}/api/v1/payments/lnurl"
            pay_resp = await self.http_client.post(
                payment_url,
                headers=local_headers,
                json=payment_payload
            )
            pay_resp.raise_for_status()
            return pay_resp.json()

        except Exception as e:
            logger.error(f"Error making LNURL payment: {e}")
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def fetch_btc_price(self) -> float:
        """Fetch current BTC price from OpenHAB."""
        response = await self.http_client.get(
            f'{self.openhab_url}/rest/items/BTC_Price_Output/state',
            auth=self.auth
        )
        response.raise_for_status()
        return float(response.text)

    async def convert_to_sats(self, usd_amount: float) -> int:
        """Convert USD amount to satoshis."""
        btc_price = await self.fetch_btc_price()
        return int(round((usd_amount / btc_price) * 100_000_000))

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def fetch_cyberherd_targets(self) -> List[Dict]:
        """Fetch current CyberHerd targets from LNbits."""
        url = f'{self.lnbits_url}/splitpayments/api/v1/targets'
        headers = {
            'accept': 'application/json',
            'X-API-KEY': config['CYBERHERD_KEY']
        }
        response = await self.http_client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def reset_cyberherd_targets(self) -> Dict:
        """Reset CyberHerd targets to default."""
        headers = {
            'accept': 'application/json',
            'X-API-KEY': config['CYBERHERD_KEY']
        }
        url = f"{self.lnbits_url}/splitpayments/api/v1/targets"

        # Delete existing targets
        await self.http_client.delete(url, headers=headers)

        # Create default target
        predefined_wallet = {
            'wallet': config['PREDEFINED_WALLET_ADDRESS'],
            'alias': config['PREDEFINED_WALLET_ALIAS'],
            'percent': config['PREDEFINED_WALLET_PERCENT_RESET']
        }
        new_targets = {"targets": [predefined_wallet]}
        
        response = await self.http_client.put(
            url,
            headers={**headers, 'Content-Type': 'application/json'},
            content=json.dumps(new_targets)
        )
        response.raise_for_status()
        return response.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def update_goat_sats(self, sats_received: int):
        """Update goat sats counter in OpenHAB."""
        try:
            current_state = await self.get_goat_sats_sum_today()
            new_state = current_state["sum_goat_sats"] + sats_received
            headers = {
                "accept": "application/json",
                "Content-Type": "text/plain"
            }
            put_url = f"{self.openhab_url}/rest/items/GoatSats/state"
            response = await self.http_client.put(
                put_url,
                headers=headers,
                auth=self.auth,
                content=str(new_state)
            )
            response.raise_for_status()
            return new_state
        except Exception as e:
            logger.error(f"Error updating goat sats: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_goat_sats_sum_today(self) -> Dict[str, int]:
        """Get total goat sats for today."""
        response = await self.http_client.get(
            f'{self.openhab_url}/rest/items/GoatSats/state',
            auth=self.auth
        )
        response.raise_for_status()
        try:
            latest_state = int(float(response.text.strip()))
        except ValueError:
            latest_state = 0
        return {"sum_goat_sats": latest_state}

    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()
