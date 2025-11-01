"""Input validation and sanitization utilities."""
import re
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# Account ID pattern: ACC followed by 4 digits
ACCOUNT_ID_PATTERN = re.compile(r"^ACC\d{4}$")

# Valid account ranges
VALID_ACCOUNT_MIN = 1000
VALID_ACCOUNT_MAX = 1099
INVALID_ACCOUNT_MIN = 2000
INVALID_ACCOUNT_MAX = 2049


class ValidationError(Exception):
    """Exception raised for validation errors."""
    pass


def validate_account_id(account_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate account ID format and provide warnings.

    Args:
        account_id: Account ID to validate

    Returns:
        Tuple of (is_valid, warning_message)
    """
    # Check format
    if not ACCOUNT_ID_PATTERN.match(account_id):
        return False, f"Invalid account format: {account_id}. Must be ACC followed by 4 digits (e.g., ACC1000)"

    # Extract account number
    account_num = int(account_id[3:])

    # Check if in invalid range
    if INVALID_ACCOUNT_MIN <= account_num <= INVALID_ACCOUNT_MAX:
        return True, f"Warning: {account_id} is in the invalid account range (ACC2000-ACC2049) - transfer will likely fail"

    # Check if in valid range
    if VALID_ACCOUNT_MIN <= account_num <= VALID_ACCOUNT_MAX:
        return True, None

    # Outside known ranges
    return True, f"Warning: {account_id} is outside known valid range (ACC1000-ACC1099) - transfer may fail"


def validate_amount(amount: float) -> Tuple[bool, Optional[str]]:
    """
    Validate transfer amount.

    Args:
        amount: Amount to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if amount <= 0:
        return False, f"Amount must be greater than 0, got {amount}"

    if amount > 1_000_000:
        return True, f"Warning: Large transfer amount ${amount:,.2f}"

    return True, None


def sanitize_account_id(account_id: str) -> str:
    """
    Sanitize account ID by removing whitespace and converting to uppercase.

    Args:
        account_id: Account ID to sanitize

    Returns:
        Sanitized account ID
    """
    return account_id.strip().upper()


def validate_transfer_request(
    from_account: str,
    to_account: str,
    amount: float,
    strict: bool = False
) -> None:
    """
    Validate a complete transfer request.

    Args:
        from_account: Source account ID
        to_account: Destination account ID
        amount: Transfer amount
        strict: If True, raise exception on warnings; if False, only log warnings

    Raises:
        ValidationError: If validation fails
    """
    # Sanitize inputs
    from_account = sanitize_account_id(from_account)
    to_account = sanitize_account_id(to_account)

    # Validate from account
    valid, message = validate_account_id(from_account)
    if not valid:
        raise ValidationError(message)
    if message and strict:
        raise ValidationError(message)
    if message:
        logger.warning(message)

    # Validate to account
    valid, message = validate_account_id(to_account)
    if not valid:
        raise ValidationError(message)
    if message and strict:
        raise ValidationError(message)
    if message:
        logger.warning(message)

    # Check accounts are different
    if from_account == to_account:
        raise ValidationError("Source and destination accounts cannot be the same")

    # Validate amount
    valid, message = validate_amount(amount)
    if not valid:
        raise ValidationError(message)
    if message and strict:
        raise ValidationError(message)
    if message:
        logger.warning(message)

    logger.debug(f"Transfer request validated: {from_account} -> {to_account}, ${amount:.2f}")
