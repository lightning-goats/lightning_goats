from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Set, Union
from datetime import datetime

class HookData(BaseModel):
    payment_hash: str
    description: Optional[str] = None
    amount: Optional[float] = 0

class CyberHerdData(BaseModel):
    display_name: Optional[str] = 'Anon'
    event_id: str
    note: str
    kinds: List[int] = []
    pubkey: str
    nprofile: str
    lud16: str
    notified: Optional[str] = None
    payouts: float = 0.0
    amount: Optional[int] = 0
    picture: Optional[str] = None

    class Config:
        extra = 'ignore'
        
    @validator('lud16')
    def validate_lud16(cls, v):
        if '@' not in v:
            raise ValueError('Invalid lud16 format')
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
