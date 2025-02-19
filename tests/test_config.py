import os

TEST_CONFIG = {
    'LNBITS_URL': 'http://localhost:3002',
    'OPENHAB_URL': 'http://localhost:8080',
    'HERD_WEBSOCKET': 'ws://localhost:3002/api/v1/ws/test',
    'OH_AUTH_1': 'test_auth',
    'HERD_KEY': 'test_herd_key',
    'SAT_KEY': 'test_sat_key',
    'NOS_SEC': 'test_nos_sec',
    'HEX_KEY': 'test_hex_key',
    'CYBERHERD_KEY': 'test_cyberherd_key',
    'PREDEFINED_WALLET_ADDRESS': 'test@strike.me',
    'PREDEFINED_WALLET_ALIAS': 'TestWallet',
    'DEBUG': 'true'
}

def setup_test_env():
    """Set up test environment variables."""
    for key, value in TEST_CONFIG.items():
        os.environ[key] = value
