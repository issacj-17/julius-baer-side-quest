"""Unit tests for auth module."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import httpx

from transfer_client.auth import AuthManager


@pytest.mark.unit
class TestAuthManager:
    """Test AuthManager class."""

    def test_init(self):
        """Test AuthManager initialization."""
        auth = AuthManager(base_url="http://test.com", timeout=5.0)
        assert auth.base_url == "http://test.com"
        assert auth.timeout == 5.0
        assert auth._token_cache == {}

    def test_get_token_success(self, mocker, mock_token_response):
        """Test successful token retrieval."""
        # Mock httpx.Client
        mock_response = Mock()
        mock_response.json.return_value = mock_token_response
        mock_response.status_code = 200

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)

        mocker.patch('httpx.Client', return_value=mock_client)

        auth = AuthManager()
        token = auth.get_token(username="alice", password="pass", scope="transfer")

        assert token is not None
        assert token == mock_token_response["token"]
        mock_client.post.assert_called_once()

    def test_get_token_caching(self, mocker, mock_token_response):
        """Test that tokens are cached."""
        mock_response = Mock()
        mock_response.json.return_value = mock_token_response

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)

        mocker.patch('httpx.Client', return_value=mock_client)

        auth = AuthManager()

        # First call
        token1 = auth.get_token(username="alice", scope="transfer")
        assert token1 is not None

        # Second call should use cache
        token2 = auth.get_token(username="alice", scope="transfer")
        assert token2 == token1

        # Should only have called the API once
        assert mock_client.post.call_count == 1

    def test_get_token_force_refresh(self, mocker, mock_token_response):
        """Test force refresh bypasses cache."""
        mock_response = Mock()
        mock_response.json.return_value = mock_token_response

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)

        mocker.patch('httpx.Client', return_value=mock_client)

        auth = AuthManager()

        # First call
        token1 = auth.get_token(username="alice", scope="transfer")

        # Force refresh
        token2 = auth.get_token(username="alice", scope="transfer", force_refresh=True)

        # Should have called API twice
        assert mock_client.post.call_count == 2

    def test_get_token_different_scopes(self, mocker, mock_token_response):
        """Test different scopes are cached separately."""
        mock_response = Mock()
        mock_response.json.return_value = mock_token_response

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)

        mocker.patch('httpx.Client', return_value=mock_client)

        auth = AuthManager()

        # Get token with transfer scope
        token1 = auth.get_token(username="alice", scope="transfer")

        # Get token with enquiry scope
        token2 = auth.get_token(username="alice", scope="enquiry")

        # Should have called API twice (different scopes)
        assert mock_client.post.call_count == 2

    def test_get_token_http_error(self, mocker):
        """Test handling of HTTP errors."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Unauthorized"}

        mock_client = Mock()
        mock_client.post.side_effect = httpx.HTTPStatusError(
            "Unauthorized",
            request=Mock(),
            response=mock_response
        )
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)

        mocker.patch('httpx.Client', return_value=mock_client)

        auth = AuthManager()
        token = auth.get_token(username="alice", password="wrong")

        assert token is None

    def test_get_token_network_error(self, mocker):
        """Test handling of network errors."""
        mock_client = Mock()
        mock_client.post.side_effect = httpx.RequestError("Connection failed")
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)

        mocker.patch('httpx.Client', return_value=mock_client)

        auth = AuthManager()
        token = auth.get_token(username="alice")

        assert token is None

    def test_get_token_no_token_in_response(self, mocker):
        """Test handling when response has no token."""
        mock_response = Mock()
        mock_response.json.return_value = {"error": "No token"}

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)

        mocker.patch('httpx.Client', return_value=mock_client)

        auth = AuthManager()
        token = auth.get_token(username="alice")

        assert token is None

    def test_clear_cache(self, mocker, mock_token_response):
        """Test clearing token cache."""
        mock_response = Mock()
        mock_response.json.return_value = mock_token_response

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)

        mocker.patch('httpx.Client', return_value=mock_client)

        auth = AuthManager()

        # Get and cache token
        auth.get_token(username="alice", scope="transfer")
        assert len(auth._token_cache) > 0

        # Clear cache
        auth.clear_cache()
        assert len(auth._token_cache) == 0

    def test_token_expiration(self, mocker, mock_token_response):
        """Test that expired tokens are not used from cache."""
        mock_response = Mock()
        mock_response.json.return_value = mock_token_response

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)

        mocker.patch('httpx.Client', return_value=mock_client)

        auth = AuthManager()

        # Get token
        token1 = auth.get_token(username="alice", scope="transfer")

        # Manually expire the token
        cache_key = "alice:transfer"
        auth._token_cache[cache_key]["expires_at"] = datetime.now() - timedelta(minutes=1)

        # Get token again - should fetch new one
        token2 = auth.get_token(username="alice", scope="transfer")

        # Should have called API twice
        assert mock_client.post.call_count == 2
