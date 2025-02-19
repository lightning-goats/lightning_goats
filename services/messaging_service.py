import asyncio
import random
import logging
import json
from typing import Tuple, Dict, Any, Optional, List
from config import config, GOAT_NAMES_DICT, DEFAULT_RELAYS
from utils.cyberherd_module import run_subprocess
from services.message_templates import (
    sats_received_dict,
    feeder_trigger_dict,
    variations,
    thank_you_variations,
    cyber_herd_dict,
    cyber_herd_info_dict,
    cyber_herd_treats_dict,
    interface_info_dict
)
from utils.nostr_signing import sign_event

logger = logging.getLogger(__name__)

class MessagingService:
    MESSAGE_TYPES = {
        "sats_received": sats_received_dict,
        "feeder_triggered": feeder_trigger_dict,
        "cyber_herd": cyber_herd_dict,
        "cyber_herd_info": cyber_herd_info_dict,
        "cyber_herd_treats": cyber_herd_treats_dict,
        "interface_info": interface_info_dict,
    }

    def __init__(self):
        self.notified = {}
        self.goat_names = GOAT_NAMES_DICT

    def _get_thanks_part(self, amount: int) -> str:
        """Get a random thank you message."""
        if amount <= 0:
            return ""
        thanks_template = random.choice(thank_you_variations)
        return thanks_template.format(new_amount=amount)

    def _get_spots_info(self, spots_remaining: int) -> str:
        """Get spots remaining message."""
        if spots_remaining <= 0:
            return "The CyberHerd is full for today."
        elif spots_remaining == 1:
            return f"Only {spots_remaining} spot left in today's CyberHerd!"
        else:
            return f"{spots_remaining} spots left in today's CyberHerd!"

    def _get_difference_message(self, difference: int) -> str:
        """Get a random difference message."""
        if difference <= 0:
            return ""
        template = random.choice(list(variations.values()))
        return template.format(difference=difference)

    def get_random_goat_names(self, goat_names_dict: Dict) -> List[Tuple]:
        """Get random selection of goat names and their info."""
        keys = list(goat_names_dict.keys())
        selected_keys = random.sample(keys, random.randint(1, len(keys)))
        return [(key, goat_names_dict[key][0], goat_names_dict[key][1]) 
                for key in selected_keys]

    def join_with_and(self, items: List[str]) -> str:
        """Join items with commas and 'and'."""
        if len(items) > 2:
            return ', '.join(items[:-1]) + ', and ' + items[-1]
        elif len(items) == 2:
            return ' and '.join(items)
        elif len(items) == 1:
            return items[0]
        return ''

    async def _execute_command(self, command: str) -> Optional[str]:
        """Execute a shell command and return the output."""
        if not command:
            return None

        if config['DEBUG_NOSTR']:
            if 'nak event' in command:  # Only log nak commands
                logger.info(f"DEBUG_NOSTR mode - suppressed: {command}")
            return None

        logger.info(f"Executing command: {command}")
        result = await run_subprocess(command.split())
        
        if result.returncode != 0:
            logger.error(f"Command failed: {result.stderr.decode()}")
            return result.stderr.decode()
        
        logger.info(f"Command succeeded: {result.stdout.decode()}")
        return result.stdout.decode()

    async def make_messages(
        self,
        nos_sec: str,
        new_amount: float,
        difference: float,
        event_type: str,
        cyber_herd_item: Dict = None,
        spots_remaining: int = 0,
    ) -> Tuple[str, Optional[str]]:
        """Generate messages based on event type."""
        message = await self._generate_user_message(
            event_type, new_amount, difference, cyber_herd_item, spots_remaining
        )
        
        command_output = None
        if not config['DEBUG_NOSTR']:
            command_output = await self._generate_nostr_command(
                event_type, message, new_amount, nos_sec, cyber_herd_item
            )
        elif event_type != "interface_info":
            logger.info("💬 [Nostr Disabled] Message would be sent to Nostr")

        # Log message details based on event type
        if event_type == "sats_received":
            logger.info("\n💌 User Message Generated")
            logger.info(f"Type: Payment Received")
            logger.info(f"Message: {message}")
            logger.info("=" * 40)
        elif event_type == "feeder_triggered":
            logger.info("\n🎉 Feeder Message Generated")
            logger.info(f"Message: {message}")
            logger.info("=" * 40)
        elif event_type == "cyber_herd":
            logger.info("\n🐐 CyberHerd Message Generated")
            logger.info(f"Message: {message}")
            logger.info("=" * 40)

        return message, command_output

    async def _generate_user_message(
        self,
        event_type: str,
        new_amount: int,
        difference: int,
        cyber_herd_item: Optional[Dict] = None,
        spots_remaining: int = 0
    ) -> str:
        """Generate user-friendly message."""
        message_templates = self.MESSAGE_TYPES.get(event_type)
        if not message_templates:
            logger.error(f"Event type '{event_type}' not recognized.")
            return "Event type not recognized."

        template = random.choice(list(message_templates.values()))
        
        handlers = {
            "cyber_herd": self._handle_cyber_herd_message,
            "cyber_herd_treats": self._handle_treats_message,
        }

        if event_type in ["sats_received", "feeder_triggered"]:
            return await self._handle_regular_message(
                template,
                new_amount,
                difference,
                cyber_herd_item,
                spots_remaining
            )
        elif event_type in handlers:
            return await handlers[event_type](
                template=template,
                cyber_herd_item=cyber_herd_item,
                new_amount=new_amount,
                difference=difference,
                spots_remaining=spots_remaining
            )
        else:
            return template.format(new_amount=0, goat_name="", difference_message="")

    async def _generate_nostr_command(self, event_type: str, message: str, *args, **kwargs) -> Optional[str]:
        """Generate Nostr command."""
        if event_type in ["sats_received", "feeder_triggered"]:
            return await self._generate_regular_nostr_command(message, *args, **kwargs)
        elif event_type == "cyber_herd":
            return await self._generate_cyber_herd_nostr_command(message, *args, **kwargs)
        elif event_type == "cyber_herd_treats":
            return await self._generate_treats_nostr_command(message, *args, **kwargs)
        return None

    async def _handle_regular_message(
        self,
        template: str,
        new_amount: int,
        difference: int,
        cyber_herd_item: Optional[Dict] = None,
        spots_remaining: int = 0
    ) -> str:
        """Handle regular message generation (sats received, feeder triggered)."""
        selected_goats = self.get_random_goat_names(self.goat_names)
        goat_names = [name for name, _, _ in selected_goats]
        goat_name = self.join_with_and(goat_names)
        
        # Use first goat's info for nostr command
        _, nprofile, pubkey = selected_goats[0]
        difference_message = self._get_difference_message(difference)

        message = template.format(
            new_amount=new_amount,
            difference_message=difference_message,
            goat_name=goat_name
        )

        if nprofile and nprofile in message:
            message = message.replace(nprofile, goat_names[0])

        return message

    async def _generate_regular_nostr_command(
        self,
        message: str,
        new_amount: int,
        nos_sec: str,
        *args, **kwargs
    ) -> Optional[str]:
        """Generate Nostr command for regular messages."""
        selected_goats = self.get_random_goat_names(self.goat_names)
        _, _, pubkey = selected_goats[0]

        command = None
        if pubkey:
            command = (
                f'/usr/local/bin/nak event --sec {config["NOS_SEC"]} -c "{message}" '
                f'-p {pubkey} '
                f'{" ".join(DEFAULT_RELAYS)}'
            )

        return command

    async def _handle_cyber_herd_message(
        self, 
        template: str, 
        cyber_herd_item: Dict,
        difference: float,
        spots_remaining: int
    ) -> str:
        """Handle CyberHerd specific message generation."""
        display_name = cyber_herd_item.get("display_name", "anon")
        event_id = cyber_herd_item.get("event_id", "")
        pub_key = cyber_herd_item.get("pubkey", "")
        nprofile = cyber_herd_item.get("nprofile", "")
        amount = cyber_herd_item.get("amount", 0)

        thanks_part = self._get_thanks_part(amount)
        name = nprofile if nprofile and nprofile.startswith("nostr:") else display_name
        spots_info = self._get_spots_info(spots_remaining)

        message = template.format(
            thanks_part=thanks_part,
            name=name,
            difference=difference,
            new_amount=amount,
            event_id=event_id
        )
        message = f"{message} {spots_info}".strip()

        if nprofile and nprofile in message:
            message = message.replace(nprofile, display_name)

        return message

    async def _generate_cyber_herd_nostr_command(
        self,
        message: str,
        new_amount: int,
        nos_sec: str,
        cyber_herd_item: Dict,
        *args, **kwargs
    ) -> Optional[str]:
        """Generate Nostr command for CyberHerd messages."""
        event_id = cyber_herd_item.get("event_id", "")
        pub_key = cyber_herd_item.get("pubkey", "")

        command = (
            f'/usr/local/bin/nak event --sec {config["NOS_SEC"]} -c "{message}" '
            f'--tag e="{event_id};{DEFAULT_RELAYS[0]};root" '
            f'-p {pub_key} '
            f'{" ".join(DEFAULT_RELAYS)}'
        )

        return command

    async def _handle_treats_message(
        self,
        template: str,
        cyber_herd_item: Dict,
        new_amount: int,
        difference: int
    ) -> str:
        """Handle CyberHerd treats message generation."""
        display_name = cyber_herd_item.get("display_name", "anon")
        pub_key = cyber_herd_item.get("pubkey", "")
        nprofile = cyber_herd_item.get("nprofile", "")
        event_id = cyber_herd_item.get("event_id", "")

        name = nprofile if nprofile and nprofile.startswith("nostr:") else display_name
        message = template.format(
            name=name,
            new_amount=new_amount,
            difference=difference
        )

        if nprofile and nprofile in message:
            message = message.replace(nprofile, display_name)

        return message

    async def _generate_treats_nostr_command(
        self,
        message: str,
        new_amount: int,
        nos_sec: str,
        cyber_herd_item: Dict,
        *args, **kwargs
    ) -> Optional[str]:
        """Generate Nostr command for CyberHerd treats messages."""
        event_id = cyber_herd_item.get("event_id", "")
        pub_key = cyber_herd_item.get("pubkey", "")

        command = self._build_nostr_command(message, pub_key, event_id)

        return command

    async def initialize_messages(self):
        """Initialize any message-related resources."""
        # This can be expanded if we need to load resources or set up connections
        self.notified = {}
        logger.info("Message service initialized")

    async def cleanup_messages(self):
        """Cleanup message-related resources."""
        # This can be expanded if we need to clean up resources
        self.notified = {}
        logger.info("Message service cleaned up")

    @classmethod
    async def make_messages_compat(cls, *args, **kwargs) -> Tuple[str, Optional[str]]:
        """Compatibility method for old messaging.py make_messages function."""
        instance = cls()
        return await instance.make_messages(*args, **kwargs)

async def make_messages(
    private_key: str,
    amount: int,
    difference: int,
    message_type: str,
    member_data: Optional[Dict] = None,
    spots_remaining: Optional[int] = None
) -> Tuple[str, Optional[str]]:
    """Generate notification messages based on type."""
    
    message_content = {
        "type": message_type,
        "amount": amount,
        "difference": difference
    }

    if message_type == "cyber_herd" and member_data:
        message_content.update({
            "member": member_data,
            "spots_remaining": spots_remaining
        })

    # Convert to JSON string
    message = json.dumps(message_content)

    # Sign the event if we have a private key
    if private_key:
        try:
            signed_event = await sign_event(
                {
                    "content": message,
                    "kind": 1,
                    "created_at": int(time.time()),
                    "tags": [],
                    "pubkey": ""  # Will be derived from private key
                },
                private_key
            )
            raw_command_output = json.dumps(signed_event)
            return message, raw_command_output
        except Exception as e:
            logger.error(f"Error signing event: {e}")
            return message, None

    return message, None
