"""Unit tests for BankingClient."""
import pytest
from unittest.mock import Mock, patch
import httpx
from transfer_client.client import BankingClient
from transfer_client.validators import ValidationError


@pytest.mark.unit
class TestBankingClient:
    """Test BankingClient class."""

    def test_init(self, mock_config):
        """Test client initialization."""
        client = BankingClient(mock_config)
        assert client.config == mock_config
        assert client._token is None

    def test_transfer_success(self, banking_client, mocker, mock_success_response, mock_token_response):
        """Test successful transfer."""
        # Mock token request
        mock_token_resp = Mock()
        mock_token_resp.json.return_value = mock_token_response
        mock_token_resp.status_code = 200

        # Mock transfer request
        mock_transfer_resp = Mock()
        mock_transfer_resp.json.return_value = mock_success_response
        mock_transfer_resp.status_code = 200

        mock_client = Mock()
        mock_client.post.side_effect = [mock_token_resp, mock_transfer_resp]
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)

        mocker.patch('httpx.Client', return_value=mock_client)

        result = banking_client.transfer("ACC1000", "ACC1001", 100.0)

        assert result is not None
        assert result["status"] == "SUCCESS"
        assert result["transactionId"] == "test-123-456"

    def test_transfer_validation_error(self, banking_client):
        """Test transfer with validation error."""
        result = banking_client.transfer("INVALID", "ACC1001", 100.0)
        assert result is None

    def test_transfer_without_auth(self, banking_client, mocker, mock_success_response):
        """Test transfer without authentication."""
        mock_resp = Mock()
        mock_resp.json.return_value = mock_success_response
        mock_resp.status_code = 200

        mock_client = Mock()
        mock_client.post.return_value = mock_resp
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)

        mocker.patch('httpx.Client', return_value=mock_client)

        result = banking_client.transfer("ACC1000", "ACC1001", 100.0, use_auth=False)

        assert result is not None
        # Should only call transfer endpoint, not auth
        assert mock_client.post.call_count == 1

    def test_validate_account(self, banking_client, mocker, mock_account_validation, mock_token_response):
        """Test account validation."""
        mock_token_resp = Mock()
        mock_token_resp.json.return_value = mock_token_response

        mock_validate_resp = Mock()
        mock_validate_resp.json.return_value = mock_account_validation
        mock_validate_resp.status_code = 200

        mock_client = Mock()
        mock_client.post.return_value = mock_token_resp
        mock_client.get.return_value = mock_validate_resp
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)

        mocker.patch('httpx.Client', return_value=mock_client)

        result = banking_client.validate_account("ACC1000")

        assert result is not None
        assert result["isValid"] is True

    def test_get_balance(self, banking_client, mocker, mock_balance_response, mock_token_response):
        """Test getting account balance."""
        mock_token_resp = Mock()
        mock_token_resp.json.return_value = mock_token_response

        mock_balance_resp = Mock()
        mock_balance_resp.json.return_value = mock_balance_response
        mock_balance_resp.status_code = 200

        mock_client = Mock()
        mock_client.post.return_value = mock_token_resp
        mock_client.get.return_value = mock_balance_resp
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)

        mocker.patch('httpx.Client', return_value=mock_client)

        result = banking_client.get_balance("ACC1000")

        assert result is not None
        assert result["balance"] == 1000.0


@pytest.mark.unit
class TestBankingClientRetry:
    """Test retry logic in BankingClient."""

    def test_retry_on_500_error(self, banking_client, mocker):
        """Test retry on server error."""
        # First two attempts fail, third succeeds
        mock_resp_fail = Mock()
        mock_resp_fail.status_code = 500
        mock_resp_fail.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=Mock(), response=mock_resp_fail
        )

        mock_resp_success = Mock()
        mock_resp_success.status_code = 200
        mock_resp_success.json.return_value = {"status": "SUCCESS"}

        mock_client = Mock()
        mock_client.request.side_effect = [
            mock_resp_fail,
            mock_resp_fail,
            mock_resp_success
        ]
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)

        mocker.patch('httpx.Client', return_value=mock_client)
        mocker.patch('time.sleep')  # Speed up test

        response = banking_client._retry_request("GET", "http://test.com")

        assert response.status_code == 200
        assert mock_client.request.call_count == 3

    def test_no_retry_on_400_error(self, banking_client, mocker):
        """Test no retry on client error."""
        mock_resp = Mock()
        mock_resp.status_code = 400
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=Mock(), response=mock_resp
        )

        mock_client = Mock()
        mock_client.request.return_value = mock_resp
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)

        mocker.patch('httpx.Client', return_value=mock_client)

        with pytest.raises(httpx.HTTPStatusError):
            banking_client._retry_request("GET", "http://test.com")

        # Should only try once (no retry on 4xx)
        assert mock_client.request.call_count == 1
