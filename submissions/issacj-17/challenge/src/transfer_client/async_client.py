"""Async banking client with connection pooling for high performance."""
import asyncio
import logging
from typing import Optional, Dict, Any, List
import httpx

from transfer_client.config import Config
from transfer_client.validators import validate_transfer_request, sanitize_account_id, ValidationError

logger = logging.getLogger(__name__)


class AsyncBankingClient:
    """Async banking client with connection pooling for concurrent operations."""

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize async banking client.

        Args:
            config: Configuration object (uses defaults if not provided)
        """
        self.config = config or Config()
        self._token: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None
        logger.info(f"AsyncBankingClient initialized with base_url={self.config.base_url}")

    async def __aenter__(self):
        """Context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()

    async def connect(self):
        """Initialize the async HTTP client with connection pooling."""
        if self._client is None:
            limits = httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
                keepalive_expiry=30.0
            )
            self._client = httpx.AsyncClient(
                timeout=self.config.timeout,
                limits=limits,
                follow_redirects=True
            )
            logger.debug("Async HTTP client initialized with connection pooling")

    async def close(self):
        """Close the async HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug("Async HTTP client closed")

    async def _get_token(self) -> Optional[str]:
        """Get JWT token asynchronously."""
        if self._token:
            return self._token

        url = f"{self.config.base_url}/authToken"
        params = {"claim": self.config.auth_scope}
        payload = {"username": self.config.username, "password": self.config.password}

        try:
            if not self._client:
                await self.connect()

            response = await self._client.post(url, json=payload, params=params)
            response.raise_for_status()
            result = response.json()
            self._token = result.get("token")
            logger.info("JWT token obtained successfully")
            return self._token
        except Exception as e:
            logger.error(f"Error getting token: {e}")
            return None

    async def _get_headers(self, use_auth: Optional[bool] = None) -> Dict[str, str]:
        """Get HTTP headers with optional authentication."""
        headers = {"Content-Type": "application/json"}

        should_use_auth = use_auth if use_auth is not None else self.config.use_auth

        if should_use_auth:
            token = await self._get_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
                logger.debug("Added Authorization header")

        return headers

    async def _retry_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with async retry logic."""
        if not self._client:
            await self.connect()

        last_exception = None

        for attempt in range(self.config.max_retries):
            try:
                response = await self._client.request(method, url, **kwargs)

                if response.status_code in self.config.retry_on_status:
                    if attempt < self.config.max_retries - 1:
                        wait_time = self.config.retry_backoff_factor * (2 ** attempt)
                        logger.warning(
                            f"Request failed with status {response.status_code}, "
                            f"retrying in {wait_time:.1f}s (attempt {attempt + 1}/{self.config.max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                        continue

                response.raise_for_status()
                return response

            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code not in self.config.retry_on_status:
                    raise

                if attempt < self.config.max_retries - 1:
                    wait_time = self.config.retry_backoff_factor * (2 ** attempt)
                    logger.warning(f"HTTP error, retrying in {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise

            except httpx.RequestError as e:
                last_exception = e
                if attempt < self.config.max_retries - 1:
                    wait_time = self.config.retry_backoff_factor * (2 ** attempt)
                    logger.warning(f"Request error, retrying in {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise

        if last_exception:
            raise last_exception

    async def transfer(
        self,
        from_account: str,
        to_account: str,
        amount: float,
        use_auth: Optional[bool] = None,
        validate: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Async transfer funds between accounts."""
        from_account = sanitize_account_id(from_account)
        to_account = sanitize_account_id(to_account)

        if validate:
            try:
                validate_transfer_request(from_account, to_account, amount)
            except ValidationError as e:
                logger.error(f"Validation failed: {e}")
                return None

        url = f"{self.config.base_url}/transfer"
        payload = {
            "fromAccount": from_account,
            "toAccount": to_account,
            "amount": amount
        }
        headers = await self._get_headers(use_auth)

        logger.info(f"Initiating async transfer: {from_account} -> {to_account}, ${amount:.2f}")

        try:
            response = await self._retry_request("POST", url, json=payload, headers=headers)
            result = response.json()

            status = result.get("status", "UNKNOWN")
            if status == "SUCCESS":
                logger.info(f"Transfer successful: {result.get('transactionId')}")
            else:
                logger.warning(f"Transfer failed: {result.get('message')}")

            return result

        except Exception as e:
            logger.error(f"Error during transfer: {e}")
            return None

    async def transfer_batch(
        self,
        transfers: List[tuple],
        use_auth: Optional[bool] = None
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Execute multiple transfers concurrently.

        Args:
            transfers: List of (from_account, to_account, amount) tuples
            use_auth: Override config.use_auth if provided

        Returns:
            List of transfer results
        """
        logger.info(f"Executing batch of {len(transfers)} transfers")

        tasks = [
            self.transfer(from_acc, to_acc, amount, use_auth)
            for from_acc, to_acc, amount in transfers
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to None
        return [r if not isinstance(r, Exception) else None for r in results]

    async def validate_account(
        self,
        account_id: str,
        use_auth: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """Async validate account."""
        account_id = sanitize_account_id(account_id)
        url = f"{self.config.base_url}/accounts/validate/{account_id}"
        headers = await self._get_headers(use_auth)

        try:
            response = await self._retry_request("GET", url, headers=headers)
            return response.json()
        except Exception as e:
            logger.error(f"Error validating account: {e}")
            return None

    async def get_balance(
        self,
        account_id: str,
        use_auth: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """Async get account balance."""
        account_id = sanitize_account_id(account_id)
        url = f"{self.config.base_url}/accounts/balance/{account_id}"
        headers = await self._get_headers(use_auth)

        try:
            response = await self._retry_request("GET", url, headers=headers)
            return response.json()
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return None

    async def get_all_accounts(
        self,
        use_auth: Optional[bool] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Async get all accounts."""
        url = f"{self.config.base_url}/accounts"
        headers = await self._get_headers(use_auth)

        try:
            response = await self._retry_request("GET", url, headers=headers)
            return response.json()
        except Exception as e:
            logger.error(f"Error getting accounts: {e}")
            return None

    async def get_transaction_history(
        self,
        limit: int = 10,
        use_auth: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """Async get transaction history."""
        if use_auth is None:
            use_auth = True

        url = f"{self.config.base_url}/transactions/history"
        params = {"limit": min(limit, 20)}
        headers = await self._get_headers(use_auth)

        try:
            response = await self._retry_request("GET", url, params=params, headers=headers)
            return response.json()
        except Exception as e:
            logger.error(f"Error getting transaction history: {e}")
            return None
