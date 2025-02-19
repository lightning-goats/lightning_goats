import json
import logging
import asyncio
from typing import List, Dict, Optional
import httpx

from config import config, DEFAULT_RELAYS
from utils.nostr_signing import sign_event, compute_event_hash  # Changed from get_event_hash
from utils.relay_manager import RelayManager

logger = logging.getLogger(__name__)

# Utility Functions
async def run_subprocess(command: list, timeout: int = 30) -> asyncio.subprocess.Process:
    """
    Run a subprocess asynchronously with a timeout.
    """
    proc = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return type('ProcessResult', (), {
            'args': command,
            'returncode': proc.returncode,
            'stdout': stdout,
            'stderr': stderr
        })
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise TimeoutError(f"Command timed out after {timeout} seconds: {' '.join(command)}")

class MetadataFetcher:
    def __init__(self):
        pass

    async def lookup_metadata(self, pubkey: str) -> Optional[Dict]:
        """Lookup metadata for a given pubkey using nak command."""
        metadata_command = [
            "/usr/local/bin/nak",
            "req",
            "-k", "0",
            "-a", pubkey,
            *DEFAULT_RELAYS
        ]

        try:
            result = await run_subprocess(metadata_command, timeout=15)
            if result.returncode != 0:
                raise Exception(f"nak command failed: {result.stderr.decode()}")

            metadata_list = []
            for line in result.stdout.decode().splitlines():
                try:
                    data = json.loads(line)
                    if data.get("kind") == 0:
                        content = json.loads(data.get("content", "{}"))
                        created_at = data.get("created_at", 0)
                        metadata_list.append((created_at, content))
                except json.JSONDecodeError:
                    continue

            if not metadata_list:
                return None

            metadata_list.sort(key=lambda x: x[0], reverse=True)
            latest_metadata = metadata_list[0][1]
            return {
                'nip05': latest_metadata.get('nip05'),
                'lud16': latest_metadata.get('lud16'),
                'display_name': latest_metadata.get('display_name') or latest_metadata.get('name', 'Anon'),
                'picture': latest_metadata.get('picture')
            }

        except Exception as e:
            logger.error(f"Error fetching metadata for {pubkey}: {e}")
            return None

class Verifier:
    @staticmethod
    async def verify_lud16(lud16: str) -> bool:
        """Verify if a lud16 address is valid."""
        if not lud16 or '@' not in lud16:
            return False
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{config['LNBITS_URL']}/api/v1/lnurlscan/{lud16}"
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Error verifying lud16 {lud16}: {e}")
            return False

async def generate_nprofile(pubkey: str) -> Optional[str]:
    """Generate an nprofile using the nak command."""
    if not pubkey:
        return None

    nprofile_command = ['/usr/local/bin/nak', 'encode', 'nprofile', pubkey]
    try:
        result = await run_subprocess(nprofile_command, timeout=10)
        if result.returncode != 0:
            return None
        return result.stdout.decode().strip()
    except Exception as e:
        logger.error(f"Error generating nprofile: {e}")
        return None

async def check_cyberherd_tag(event_id: str) -> bool:
    """Check if an event has a CyberHerd tag using nak command."""
    nak_command = [
        "/usr/local/bin/nak",
        "req",
        "-i", event_id,
        *DEFAULT_RELAYS[:1]  # Use first relay for simple queries
    ]
    try:
        result = await run_subprocess(nak_command)
        if result.returncode != 0:
            return False

        event_data = json.loads(result.stdout.decode())
        tags = event_data.get('tags', [])
        return any(
            tag[0] == 't' and tag[1].lower() == 'cyberherd'
            for tag in tags
            if isinstance(tag, list) and len(tag) >= 2
        )
    except Exception as e:
        logger.error(f"Error checking CyberHerd tag: {e}")
        return False
