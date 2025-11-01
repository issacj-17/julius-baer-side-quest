"""Pytest configuration and shared fixtures."""
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta
import httpx

from transfer_client.config import Config
from transfer_client.client import BankingClient
from transfer_client.async_client import AsyncBankingClient
from transfer_client.auth import AuthManager


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return Config(
        base_url="http://localhost:8123",
        username="test_user",
        password="test_pass",
        use_auth=True,
        auth_scope="transfer",
        timeout=10.0,
        max_retries=3,
        retry_backoff_factor=1.0,
        log_level="INFO"
    )


@pytest.fixture
def auth_manager(mock_config):
    """Create an AuthManager instance for testing."""
    return AuthManager(
        base_url=mock_config.base_url,
        timeout=mock_config.timeout
    )


@pytest.fixture
def banking_client(mock_config):
    """Create a BankingClient instance for testing."""
    return BankingClient(mock_config)


@pytest.fixture
def async_banking_client(mock_config):
    """Create an AsyncBankingClient instance for testing."""
    return AsyncBankingClient(mock_config)


@pytest.fixture
def mock_success_response():
    """Mock successful transfer response."""
    return {
        "transactionId": "test-123-456",
        "status": "SUCCESS",
        "message": "Transfer completed successfully",
        "fromAccount": "ACC1000",
        "toAccount": "ACC1001",
        "amount": 100.0,
        "newFromAccountBalance": 900.0,
        "permissionLevel": "TRANSFER",
        "bonusPoints": "✅ JWT with Transfer Permission - Maximum Credit!"
    }


@pytest.fixture
def mock_failed_response():
    """Mock failed transfer response."""
    return {
        "transactionId": "test-123-789",
        "status": "FAILED",
        "message": "Transfer failed - invalid account(s)",
        "fromAccount": "ACC2000",
        "toAccount": "ACC1001",
        "amount": 100.0,
        "fromAccountError": "Invalid or non-existent account"
    }


@pytest.fixture
def mock_token_response():
    """Mock JWT token response."""
    return {
        "token": "eyJhbGciOiJIUzI1NiJ9.test.token",
        "username": "alice",
        "scope": "transfer",
        "permissions": "transfer,enquiry",
        "expiresAt": (datetime.now() + timedelta(hours=1)).isoformat()
    }


@pytest.fixture
def mock_account_validation():
    """Mock account validation response."""
    return {
        "accountId": "ACC1000",
        "isValid": True,
        "status": "ACTIVE",
        "accountType": "VALID_ACCOUNT"
    }


@pytest.fixture
def mock_balance_response():
    """Mock balance inquiry response."""
    return {
        "accountId": "ACC1000",
        "balance": 1000.0,
        "currency": "USD",
        "status": "ACTIVE"
    }


@pytest.fixture
def mock_accounts_list():
    """Mock list of accounts."""
    return [
        {"id": f"ACC{1000+i}", "balance": 1000.0}
        for i in range(10)
    ]


@pytest.fixture
def mock_transaction_history():
    """Mock transaction history response."""
    return {
        "transactions": [
            {
                "transactionId": f"tx-{i}",
                "status": "SUCCESS",
                "amount": 100.0 * i,
                "fromAccount": f"ACC100{i}",
                "toAccount": f"ACC100{i+1}",
                "timestamp": datetime.now().isoformat()
            }
            for i in range(5)
        ],
        "totalReturned": 5,
        "viewLevel": "ALL_TRANSACTIONS"
    }


@pytest.fixture
def mock_httpx_client(mocker):
    """Create a mock httpx.Client."""
    mock_client = Mock(spec=httpx.Client)
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "SUCCESS"}
    mock_client.post.return_value = mock_response
    mock_client.get.return_value = mock_response
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=None)
    return mock_client


@pytest.fixture
def mock_async_httpx_client(mocker):
    """Create a mock httpx.AsyncClient."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "SUCCESS"}
    mock_client.post.return_value = mock_response
    mock_client.get.return_value = mock_response
    mock_client.request.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client
