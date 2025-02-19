from dotenv import load_dotenv
import os
import logging

# Load .env file first to get DEBUG setting
load_dotenv()
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

# Logging Configuration
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_env_vars(required_vars):
    load_dotenv()
    missing_vars = [var for var in required_vars if os.getenv(var) is None]
    if missing_vars:
        raise ValueError(f"Missing environment variables: {', '.join(missing_vars)}")
    return {var: os.getenv(var) for var in required_vars}

# Required environment variables
REQUIRED_ENV_VARS = [
    'OH_AUTH_1', 'HERD_KEY', 'SAT_KEY', 'NOS_SEC', 'HEX_KEY', 
    'CYBERHERD_KEY', 'LNBITS_URL', 'OPENHAB_URL', 'HERD_WEBSOCKET',
    'PREDEFINED_WALLET_ADDRESS', 'PREDEFINED_WALLET_ALIAS'
]

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./lightning_goats.db")

# Constants
MAX_HERD_SIZE = 100
PREDEFINED_WALLET_PERCENT_RESET = 100
TRIGGER_AMOUNT_SATS = 10

# Goat names and profiles configuration
GOAT_NAMES_DICT = {
        "Dexter":  [
            "nostr:nprofile1qqsw4zlzyfx43mc88psnlse8sywpfl45kuap9dy05yzkepkvu6ca5wg7qyak5",
            "ea8be2224d58ef0738613fc327811c14feb4b73a12b48fa1056c86cce6b1da39"
        ],
        "Rowan":   [
            "nostr:nprofile1qqs2w94r0fs29gepzfn5zuaupn969gu3fstj3gq8kvw3cvx9fnxmaugwur22r",
            "a716a37a60a2a32112674173bc0ccba2a3914c1728a007b31d1c30c54ccdbef1"
        ],
        "Nova":    [
            "nostr:nprofile1qqsrzy7clymq5xwcfhh0dfz6zfe7h63k8r0j8yr49mxu6as4yv2084s0vf035",
            "3113d8f9360a19d84deef6a45a1273ebea3638df2390752ecdcd76152314f3d6"
        ],
        "Cosmo":   [
            "nostr:nprofile1qqsq6n8u7dzrnhhy7xy78k2ee7e4wxlgrkm5g2rgjl3napr9q54n4ncvkqcsj",
            "0d4cfcf34439dee4f189e3d959cfb3571be81db744286897e33e8465052b3acf"
        ],
        "Newton":  [
            "nostr:nprofile1qqszdsnpyzwhjcqads3hwfywt5jfmy85jvx8yup06yq0klrh93ldjxc26lmyx",
            "26c261209d79601d6c2377248e5d249d90f4930c72702fd100fb7c772c7ed91b"
        ]
}

# Nostr configuration
DEFAULT_RELAYS = [
    "wss://relay.primal.net",
    "wss://relay.artx.market",
    "wss://relay.nostr.band",
    "wss://relay.damus.io",
    "wss://nos.lol"
]

# Load configuration
try:
    config = load_env_vars(REQUIRED_ENV_VARS)
except ValueError as e:
    logger.error(f"Configuration error: {e}")
    raise

config.update({
    'DATABASE_URL': DATABASE_URL,
    'OH_AUTH_1': os.getenv('OH_AUTH_1'),
    'HERD_WALLET': os.getenv('HERD_WALLET'),
    'HERD_KEY': os.getenv('HERD_KEY'),
    'SAT_KEY': os.getenv('SAT_KEY'),
    'CYBERHERD_KEY': os.getenv('CYBERHERD_KEY'),
    'NOS_SEC': os.getenv('NOS_SEC'),
    'HEX_KEY': os.getenv('HEX_KEY'),
    'LNBITS_URL': os.getenv('LNBITS_URL'),
    'OPENHAB_URL': os.getenv('OPENHAB_URL'),
    'HERD_WEBSOCKET': os.getenv('HERD_WEBSOCKET'),
    'PREDEFINED_WALLET_ADDRESS': os.getenv('PREDEFINED_WALLET_ADDRESS'),
    'PREDEFINED_WALLET_ALIAS': os.getenv('PREDEFINED_WALLET_ALIAS'),
    'MAX_CONCURRENT_SUBPROCESSES': int(os.getenv('MAX_CONCURRENT_SUBPROCESSES', 10)),
    'MAX_CONCURRENT_HTTP_REQUESTS': int(os.getenv('MAX_CONCURRENT_HTTP_REQUESTS', 20)),
    'NIP05_VERIFICATION': os.getenv('NIP05_VERIFICATION', 'true').lower() == 'true',
    'DEBUG': DEBUG
})

if DEBUG:
    logger.debug("Running in DEBUG mode - debug logging enabled")
    logger.debug("nak commands and websocket messages are disabled in debug mode")
