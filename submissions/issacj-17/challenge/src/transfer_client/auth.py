"""JWT Authentication module for banking API."""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)


class AuthManager:
    """Manages JWT authentication tokens with caching."""

    def __init__(self, base_url: str = "http://localhost:8123", timeout: float = 10.0):
        """
        Initialize authentication manager.

        Args:
            base_url: Base URL of the banking API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.timeout = timeout
        self._token_cache: Dict[str, Dict[str, Any]] = {}
        logger.debug(f"AuthManager initialized with base_url={base_url}")

    def get_token(
        self,
        username: str = "alice",
        password: str = "password123",
        scope: str = "transfer",
        force_refresh: bool = False
    ) -> Optional[str]:
        """
        Get JWT token, using cached token if available and not expired.

        Args:
            username: Username for authentication
            password: Password for authentication
            scope: Token scope ('enquiry' or 'transfer')
            force_refresh: Force getting a new token even if cached

        Returns:
            JWT token string if successful, None otherwise
        """
        cache_key = f"{username}:{scope}"

        # Check cache first
        if not force_refresh and cache_key in self._token_cache:
            cached = self._token_cache[cache_key]
            if datetime.now() < cached.get("expires_at", datetime.min):
                logger.debug(f"Using cached token for {username} with scope {scope}")
                return cached["token"]

        # Request new token
        logger.info(f"Requesting new JWT token for {username} with scope {scope}")
        url = f"{self.base_url}/authToken"
        params = {"claim": scope}
        payload = {"username": username, "password": password}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload, params=params)
                resp.raise_for_status()
                result = resp.json()

                token = result.get("token")
                if not token:
                    logger.error("No token in response")
                    return None

                # Cache the token (typically valid for 1 hour, we'll use 50 minutes to be safe)
                expires_at = datetime.now() + timedelta(minutes=50)
                self._token_cache[cache_key] = {
                    "token": token,
                    "expires_at": expires_at,
                    "username": username,
                    "scope": scope
                }

                logger.info(f"Successfully obtained JWT token (expires at {expires_at})")
                logger.debug(f"Token details: {result}")
                return token

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting token: {e.response.status_code}")
            try:
                error_detail = e.response.json()
                logger.error(f"Error details: {error_detail}")
            except:
                logger.error(f"Error text: {e.response.text[:200]}")
        except httpx.RequestError as e:
            logger.error(f"Request error getting token: {e}")

        return None

    def validate_token(self, token: str) -> bool:
        """
        Validate a JWT token.

        Args:
            token: JWT token to validate

        Returns:
            True if token is valid, False otherwise
        """
        url = f"{self.base_url}/auth/validate"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=headers)
                resp.raise_for_status()
                result = resp.json()
                is_valid = result.get("valid", False)
                logger.debug(f"Token validation result: {is_valid}")
                return is_valid
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return False

    def clear_cache(self):
        """Clear all cached tokens."""
        self._token_cache.clear()
        logger.debug("Token cache cleared")
