"""Unit tests for validators module."""
import pytest
from transfer_client.validators import (
    validate_account_id,
    validate_amount,
    sanitize_account_id,
    validate_transfer_request,
    ValidationError
)


@pytest.mark.unit
class TestValidateAccountId:
    """Test account ID validation."""

    def test_valid_account_format(self):
        """Test valid account ID format."""
        valid, message = validate_account_id("ACC1000")
        assert valid is True
        assert message is None

    def test_valid_account_in_valid_range(self):
        """Test account in valid range (ACC1000-ACC1099)."""
        for i in range(1000, 1100):
            valid, message = validate_account_id(f"ACC{i}")
            assert valid is True

    def test_invalid_account_format_missing_acc(self):
        """Test invalid format - missing ACC prefix."""
        valid, message = validate_account_id("1000")
        assert valid is False
        assert "Invalid account format" in message

    def test_invalid_account_format_wrong_length(self):
        """Test invalid format - wrong number of digits."""
        valid, message = validate_account_id("ACC100")
        assert valid is False
        assert "Invalid account format" in message

    def test_invalid_account_range(self):
        """Test account in invalid range (ACC2000-ACC2049)."""
        valid, message = validate_account_id("ACC2000")
        assert valid is True
        assert "invalid account range" in message

    def test_account_outside_known_ranges(self):
        """Test account outside known ranges."""
        valid, message = validate_account_id("ACC5000")
        assert valid is True
        assert "outside known valid range" in message


@pytest.mark.unit
class TestValidateAmount:
    """Test amount validation."""

    def test_valid_amount(self):
        """Test valid positive amount."""
        valid, message = validate_amount(100.0)
        assert valid is True
        assert message is None

    def test_zero_amount(self):
        """Test zero amount (invalid)."""
        valid, message = validate_amount(0.0)
        assert valid is False
        assert "must be greater than 0" in message

    def test_negative_amount(self):
        """Test negative amount (invalid)."""
        valid, message = validate_amount(-50.0)
        assert valid is False
        assert "must be greater than 0" in message

    def test_large_amount_warning(self):
        """Test very large amount generates warning."""
        valid, message = validate_amount(2_000_000.0)
        assert valid is True
        assert "Warning" in message
        assert "Large transfer" in message


@pytest.mark.unit
class TestSanitizeAccountId:
    """Test account ID sanitization."""

    def test_sanitize_lowercase(self):
        """Test sanitization converts to uppercase."""
        result = sanitize_account_id("acc1000")
        assert result == "ACC1000"

    def test_sanitize_whitespace(self):
        """Test sanitization removes whitespace."""
        result = sanitize_account_id("  ACC1000  ")
        assert result == "ACC1000"

    def test_sanitize_mixed(self):
        """Test sanitization handles mixed case and whitespace."""
        result = sanitize_account_id("  acc1000  ")
        assert result == "ACC1000"


@pytest.mark.unit
class TestValidateTransferRequest:
    """Test complete transfer request validation."""

    def test_valid_transfer(self):
        """Test valid transfer request."""
        # Should not raise exception
        validate_transfer_request("ACC1000", "ACC1001", 100.0)

    def test_invalid_from_account_format(self):
        """Test invalid from account format."""
        with pytest.raises(ValidationError, match="Invalid account format"):
            validate_transfer_request("INVALID", "ACC1001", 100.0)

    def test_invalid_to_account_format(self):
        """Test invalid to account format."""
        with pytest.raises(ValidationError, match="Invalid account format"):
            validate_transfer_request("ACC1000", "INVALID", 100.0)

    def test_same_account_transfer(self):
        """Test transfer to same account (invalid)."""
        with pytest.raises(ValidationError, match="cannot be the same"):
            validate_transfer_request("ACC1000", "ACC1000", 100.0)

    def test_invalid_amount(self):
        """Test invalid amount."""
        with pytest.raises(ValidationError, match="must be greater than 0"):
            validate_transfer_request("ACC1000", "ACC1001", -50.0)

    def test_sanitization_applied(self):
        """Test that sanitization is applied during validation."""
        # Should not raise exception despite lowercase
        validate_transfer_request("acc1000", "acc1001", 100.0)

    def test_strict_mode_with_warnings(self):
        """Test strict mode fails on warnings."""
        with pytest.raises(ValidationError):
            validate_transfer_request(
                "ACC2000",  # Invalid range
                "ACC1001",
                100.0,
                strict=True
            )

    def test_non_strict_mode_with_warnings(self):
        """Test non-strict mode allows warnings."""
        # Should not raise exception
        validate_transfer_request(
            "ACC2000",  # Invalid range
            "ACC1001",
            100.0,
            strict=False
        )
