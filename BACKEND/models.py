"""
models.py — Simple Python dataclasses for the three core entities.
These are used to pass structured data around in application code;
they are NOT ORM models — SQLite rows are mapped to these manually.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    user_id: int
    username: str
    password_hash: str


@dataclass
class Account:
    account_id: int
    user_id: int
    balance: float


@dataclass
class Transaction:
    transaction_id: int
    account_id: int
    type: str        # "deposit" or "withdrawal"
    amount: float
    timestamp: Optional[datetime] = None
