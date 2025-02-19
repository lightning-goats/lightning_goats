from pydantic import BaseModel, validator
from typing import List, Optional

class CyberHerdData(BaseModel):
    """CyberHerd member data model."""
    pubkey: str
    display_name: Optional[str] = "Anon"
    event_id: str
    note: str
    kinds: str
    nprofile: str
    lud16: str
    notified: Optional[str] = None
    payouts: float = 0.0
    amount: Optional[int] = 0
    picture: Optional[str] = None

    @validator('lud16')
    def validate_lud16(cls, v):
        """Validate lightning address format."""
        if not '@' in v:
            raise ValueError('Lightning address must be in format username@domain')
        return v

    @validator('payouts')
    def validate_payouts(cls, v):
        """Validate payout value."""
        if not 0 <= v <= 1.0:
            raise ValueError('Payouts must be between 0 and 1.0')
        return v

class CyberHerdTreats(BaseModel):
    pubkey: str
    amount: int

class SetGoatSatsData(BaseModel):
    new_amount: int

class PaymentRequest(BaseModel):
    balance: int

class AppState:
    def __init__(self):
        self.balance: int = 0
        self.lock = asyncio.Lock()

# Additional models can be added here
