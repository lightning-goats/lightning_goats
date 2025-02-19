import httpx
import logging
import json
import math
from typing import Optional, Dict, Any, List
from config import config  # Change from relative to absolute import
from tenacity import retry, stop_after_attempt, wait_exponential
from utils.nostr_signing import sign_zap_event, sign_event, build_zap_event
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class ExternalAPIService:
    def __init__(self):
        self.lnbits_url = config['LNBITS_URL']
        self.openhab_url = config['OPENHAB_URL']
        self.auth = (config['OH_AUTH_1'], '')
        self.balance = 0
        self._client = None
        self._initialized = False

    @property
    async def http_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if not self._client or self._client.is_closed:
            self._client = httpx.AsyncClient(http2=True)
            self._initialized = True
        return self._client

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def create_invoice(self, amount: int, memo: str, key: str) -> str:
        """Create a Lightning invoice."""
        try:
            client = await self.http_client
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
            response = await client.post(url, json=data, headers=headers)
            response.raise_for_status()
            return response.json()['payment_request']
        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def pay_invoice(self, payment_request: str, key: str) -> Dict:
        """Pay a Lightning invoice."""
        try:
            client = await self.http_client
            url = f"{self.lnbits_url}/api/v1/payments"
            headers = {
                "X-API-KEY": key,
                "Content-Type": "application/json"
            }
            data = {
                "out": True,
                "bolt11": payment_request
            }
            response = await client.post(url, json=data, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error paying invoice: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_feeder_status(self) -> bool:
        """Check if feeder override is enabled."""
        try:
            client = await self.http_client
            response = await client.get(
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
            if config['DEBUG']:
                logger.debug("DEBUG mode - suppressing feeder trigger")
                return True

            client = await self.http_client
            response = await client.post(
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
            client = await self.http_client
            local_headers = {
                "accept": "application/json",
                "X-API-KEY": key or config['HERD_KEY'],
                "Content-Type": "application/json"
            }
            
            # Scan LNURL
            lnurl_scan_url = f"{self.lnbits_url}/api/v1/lnurlscan/{lud16}"
            logger.info(f"Scanning LNURL: {lnurl_scan_url}")
            lnurl_resp = await client.get(lnurl_scan_url, headers=local_headers)
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
            pay_resp = await client.post(
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
        client = await self.http_client
        response = await client.get(
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
        client = await self.http_client
        url = f'{self.lnbits_url}/splitpayments/api/v1/targets'
        headers = {
            'accept': 'application/json',
            'X-API-KEY': config['CYBERHERD_KEY']
        }
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def reset_cyberherd_targets(self) -> Dict:
        """Reset CyberHerd targets to default."""
        client = await self.http_client
        headers = {
            'accept': 'application/json',
            'X-API-KEY': config['CYBERHERD_KEY']
        }
        url = f"{self.lnbits_url}/splitpayments/api/v1/targets"

        # Delete existing targets
        await client.delete(url, headers=headers)

        # Create default target
        predefined_wallet = {
            'wallet': config['PREDEFINED_WALLET_ADDRESS'],
            'alias': config['PREDEFINED_WALLET_ALIAS'],
            'percent': config['PREDEFINED_WALLET_PERCENT_RESET']
        }
        new_targets = {"targets": [predefined_wallet]}
        
        response = await client.put(
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
            client = await self.http_client
            current_state = await self.get_goat_sats_sum_today()
            new_state = current_state["sum_goat_sats"] + sats_received

            if config['DEBUG']:
                logger.debug(f"DEBUG mode - suppressing OpenHAB update: GoatSats would be set to {new_state}")
                return new_state

            headers = {
                "accept": "application/json",
                "Content-Type": "text/plain"
            }
            put_url = f"{self.openhab_url}/rest/items/GoatSats/state"
            response = await client.put(
                put_url,
                headers=headers,
                auth=self.auth,
                content=str(new_state)
            )
            response.raise_for_status()
            logger.info(f"Updated GoatSats to {new_state}")
            return new_state
        except Exception as e:
            logger.error(f"Error updating goat sats: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def set_goat_sats(self, new_state: int):
        """Set goat sats to specific value in OpenHAB."""
        try:
            client = await self.http_client
            if config['DEBUG']:
                logger.debug(f"DEBUG mode - suppressing OpenHAB update: GoatSats would be set to {new_state}")
                return new_state

            headers = {
                "accept": "application/json",
                "Content-Type": "text/plain"
            }
            put_url = f"{self.openhab_url}/rest/items/GoatSats/state"
            response = await client.put(
                put_url,
                headers=headers,
                auth=self.auth,
                content=str(new_state)
            )
            response.raise_for_status()
            logger.info(f"Set GoatSats to {new_state}")
            return new_state
        except Exception as e:
            logger.error(f"Error setting goat sats: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_goat_sats_sum_today(self) -> Dict[str, int]:
        """Get total goat sats for today."""
        try:
            client = await self.http_client
            if config['DEBUG']:
                logger.debug("Fetching goat sats sum from OpenHAB")

            response = await client.get(
                f'{self.openhab_url}/rest/items/GoatSats/state',
                auth=self.auth,
                timeout=10.0  # Add timeout
            )
            response.raise_for_status()

            try:
                latest_state = int(float(response.text.strip()))
                if config['DEBUG']:
                    logger.debug(f"Got goat sats sum: {latest_state}")
                return {"sum_goat_sats": latest_state}
            except ValueError:
                logger.warning(f"Invalid GoatSats state value: {response.text}")
                return {"sum_goat_sats": 0}

        except httpx.TimeoutError:
            logger.error("Timeout while connecting to OpenHAB")
            raise HTTPException(status_code=504, detail="Gateway Timeout")
        except httpx.RequestError as e:
            logger.error(f"Error connecting to OpenHAB: {e}")
            raise HTTPException(status_code=502, detail="Failed to connect to OpenHAB")
        except Exception as e:
            logger.error(f"Unexpected error getting goat sats sum: {e}")
            raise HTTPException(status_code=500, detail="Internal Server Error")

    async def get_balance(self, force_refresh: bool = False) -> int:
        """Get current wallet balance."""
        try:
            client = await self.http_client
            response = await client.get(
                f'{config["LNBITS_URL"]}/api/v1/wallet',
                headers={'X-Api-Key': config['HERD_KEY']}
            )
            response.raise_for_status()
            balance = response.json()['balance']
            self.balance = math.floor(balance / 1000)
            return balance
        except httpx.HTTPError as e:
            logger.error(f"HTTP error retrieving balance: {e}")
            raise HTTPException(
                status_code=e.response.status_code if e.response else 500,
                detail="Failed to retrieve balance"
            )
        except Exception as e:
            logger.error(f"Error retrieving balance: {e}")
            raise HTTPException(status_code=500, detail="Internal Server Error")

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._initialized = False
