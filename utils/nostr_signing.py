import time
from typing import Dict, Any, Optional, List, Tuple
import json
import hashlib
from ecdsa import SigningKey, VerifyingKey, SECP256k1
from ecdsa.util import sigdecode_string, sigencode_string_canonize
import logging
from config import DEFAULT_RELAYS

logger = logging.getLogger(__name__)

# Constants
ZAP_EVENT_KIND = 9734

class NostrSigningError(Exception):
    """Base exception for Nostr signing errors"""
    pass

def derive_public_key(private_key_hex: str) -> str:
    """Derive the public key from a private key."""
    try:
        sk = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)
        return sk.get_verifying_key().to_string("compressed").hex()
    except Exception as e:
        raise NostrSigningError(f"Failed to derive public key: {e}")

def verify_key_pair(private_key_hex: str, expected_pubkey: str) -> bool:
    """Verify that a private key corresponds to an expected public key."""
    try:
        derived_pubkey = derive_public_key(private_key_hex)
        return derived_pubkey == expected_pubkey
    except Exception as e:
        logger.error(f"Key pair verification failed: {e}")
        return False

def verify_event_signature(event: dict) -> bool:
    """Verify the signature of a Nostr event."""
    try:
        pubkey = event.get("pubkey")
        sig = event.get("sig")
        if not pubkey or not sig:
            return False

        event_hash = bytes.fromhex(event["id"])
        signature = bytes.fromhex(sig)
        vk = VerifyingKey.from_string(bytes.fromhex(pubkey), curve=SECP256k1)
        
        return vk.verify(signature, event_hash, sigdecode=sigdecode_string)
    except Exception as e:
        logger.error(f"Signature verification failed: {e}")
        return False

##########################
# Basic Nostr Signing API
##########################

def remove_id_and_sig(event: dict) -> dict:
    """
    Remove 'id' and 'sig' from the event so it can be signed from scratch.
    """
    return {k: v for k, v in event.items() if k not in ["id", "sig"]}

def serialize_event(event: dict) -> bytes:
    """
    Serialize a Nostr event for signing:
    [0, pubkey, created_at, kind, tags, content]
    """
    return json.dumps(
        [
            0,
            event["pubkey"],
            event["created_at"],
            event["kind"],
            event.get("tags", []),
            event.get("content", "")
        ],
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

def compute_event_hash(serialized_event: bytes) -> bytes:
    """
    Compute the SHA-256 hash of the serialized event.
    """
    return hashlib.sha256(serialized_event).digest()

# Add alias for backward compatibility
get_event_hash = compute_event_hash

def sign_event_hash(event_hash: bytes, private_key_hex: str) -> str:
    """
    Sign the event hash with a Nostr private key (hex).
    Uses deterministic ECDSA (RFC6979) via ecdsa library.
    """
    try:
        sk = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)
        signature = sk.sign_deterministic(
            event_hash,
            sigencode=sigencode_string_canonize
        )
        return signature.hex()
    except Exception as e:
        raise NostrSigningError(f"Failed to sign event hash: {e}")

def update_event_with_id_and_sig(event: dict, event_hash: bytes, signature_hex: str) -> dict:
    """
    Populate 'id' and 'sig' fields using the computed hash and signature.
    """
    event["id"] = event_hash.hex()
    event["sig"] = signature_hex
    return event

async def sign_event(event: dict, private_key_hex: str) -> dict:
    """
    Sign a Nostr event and verify its signature.
    Raises NostrSigningError if signing or verification fails.
    """
    try:
        unsigned_event = remove_id_and_sig(event)
        serialized = serialize_event(unsigned_event)
        event_hash = compute_event_hash(serialized)
        signature_hex = sign_event_hash(event_hash, private_key_hex)
        signed_event = update_event_with_id_and_sig(event, event_hash, signature_hex)
        
        # Verify the signature
        if not verify_event_signature(signed_event):
            raise NostrSigningError("Event signature verification failed")
            
        return signed_event
    except Exception as e:
        raise NostrSigningError(f"Event signing failed: {e}")

##########################
# LNURL Zap (NIP-57) Logic
##########################

def build_zap_event(
    msat_amount: int,
    zapper_pubkey: str,
    zapped_pubkey: str,
    note_id: Optional[str] = None,
    relays: Optional[List[str]] = None,
    content: str = ""
) -> dict:
    """
    Constructs a NIP-57 Zap Request event (kind 9734).
    
    Validates input parameters and constructs a properly formatted zap request
    according to NIP-57 specification.
    """
    if msat_amount <= 0:
        raise ValueError("Amount must be positive")
    
    if not relays:
        relays = DEFAULT_RELAYS.copy()

    # Required NIP-57 zap request tags in correct order
    tags = [
        ["p", zapped_pubkey],
        ["amount", str(msat_amount)],
        ["relays", *relays]
    ]

    # Optional note reference
    if note_id:
        tags.append(["e", note_id, relays[0], "root"])
    
    # Optional description
    if content:
        tags.append(["description", content])

    return {
        "kind": ZAP_EVENT_KIND,
        "created_at": int(time.time()),
        "content": content,
        "tags": tags,
        "pubkey": zapper_pubkey
    }

async def sign_zap_event(
    msat_amount: int,
    zapper_pubkey: str,
    zapped_pubkey: str,
    private_key_hex: str,
    note_id: Optional[str] = None,
    relays: Optional[List[str]] = None,
    content: str = ""
) -> dict:
    """
    Creates and signs a NIP-57 Zap Request event.
    
    Validates the key pair and creates a properly signed zap request
    that can be used in an LNURL-pay request.
    """
    # Verify the key pair
    if not verify_key_pair(private_key_hex, zapper_pubkey):
        raise NostrSigningError("Private key does not match zapper pubkey")
        
    try:
        # Build unsigned zap request
        unsigned_event = build_zap_event(
            msat_amount=msat_amount,
            zapper_pubkey=zapper_pubkey,
            zapped_pubkey=zapped_pubkey,
            note_id=note_id,
            relays=relays,
            content=content
        )
        
        # Sign the event
        signed = await sign_event(unsigned_event, private_key_hex)
        return signed
    except Exception as e:
        raise NostrSigningError(f"Failed to create zap event: {e}")


