"""
Modern banking transfer client for Julius Baer hackathon challenge.

A comprehensive, production-ready banking client with:
- JWT authentication with token caching
- Retry logic with exponential backoff
- Input validation and sanitization
- Async support with connection pooling
- Configuration management (env vars + files)
- Professional logging
- Interactive CLI
"""

from transfer_client.client import BankingClient
from transfer_client.async_client import AsyncBankingClient
from transfer_client.config import Config
from transfer_client.auth import AuthManager
from transfer_client.validators import validate_account_id, validate_amount, ValidationError

__all__ = [
    "BankingClient",
    "AsyncBankingClient",
    "Config",
    "AuthManager",
    "validate_account_id",
    "validate_amount",
    "ValidationError",
]

__version__ = "0.1.0"
