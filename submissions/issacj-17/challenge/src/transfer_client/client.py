"""Modern banking client with retry logic, authentication, and comprehensive features."""
import logging
import time
from typing import Optional, Dict, Any, List
import httpx

from transfer_client.auth import AuthManager
from transfer_client.config import Config
from transfer_client.validators import validate_transfer_request, sanitize_account_id, ValidationError

logger = logging.getLogger(__name__)


class BankingClient:
    """Modern banking client with JWT auth, retry logic, and comprehensive features."""

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize banking client.

        Args:
            config: Configuration object (uses defaults if not provided)
        """
        self.config = config or Config()
        self.auth_manager = AuthManager(
            base_url=self.config.base_url,
            timeout=self.config.timeout
        )
        self._token: Optional[str] = None
        logger.info(f"BankingClient initialized with base_url={self.config.base_url}")

    def _get_headers(self, use_auth: Optional[bool] = None) -> Dict[str, str]:
        """
        Get HTTP headers with optional authentication.

        Args:
            use_auth: Override config.use_auth if provided

        Returns:
            Dictionary of HTTP headers
        """
        headers = {"Content-Type": "application/json"}

        should_use_auth = use_auth if use_auth is not None else self.config.use_auth

        if should_use_auth:
            if not self._token:
                logger.debug("No cached token, obtaining new token")
                self._token = self.auth_manager.get_token(
                    username=self.config.username,
                    password=self.config.password,
                    scope=self.config.auth_scope
                )

            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"
                logger.debug("Added Authorization header with JWT token")
            else:
                logger.warning("Failed to obtain JWT token, proceeding without auth")

        return headers

    def _retry_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with retry logic and exponential backoff.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional arguments passed to httpx

        Returns:
            HTTP response

        Raises:
            httpx.HTTPStatusError: If request fails after all retries
            httpx.RequestError: If network error occurs
        """
        last_exception = None

        for attempt in range(self.config.max_retries):
            try:
                with httpx.Client(timeout=self.config.timeout) as client:
                    response = client.request(method, url, **kwargs)

                    # Check if we should retry based on status code
                    if response.status_code in self.config.retry_on_status:
                        if attempt < self.config.max_retries - 1:
                            wait_time = self.config.retry_backoff_factor * (2 ** attempt)
                            logger.warning(
                                f"Request failed with status {response.status_code}, "
                                f"retrying in {wait_time:.1f}s (attempt {attempt + 1}/{self.config.max_retries})"
                            )
                            time.sleep(wait_time)
                            continue

                    response.raise_for_status()
                    return response

            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code not in self.config.retry_on_status:
                    # Don't retry on 4xx errors
                    raise

                if attempt < self.config.max_retries - 1:
                    wait_time = self.config.retry_backoff_factor * (2 ** attempt)
                    logger.warning(
                        f"HTTP error {e.response.status_code}, "
                        f"retrying in {wait_time:.1f}s (attempt {attempt + 1}/{self.config.max_retries})"
                    )
                    time.sleep(wait_time)
                else:
                    raise

            except httpx.RequestError as e:
                last_exception = e
                if attempt < self.config.max_retries - 1:
                    wait_time = self.config.retry_backoff_factor * (2 ** attempt)
                    logger.warning(
                        f"Request error: {e}, "
                        f"retrying in {wait_time:.1f}s (attempt {attempt + 1}/{self.config.max_retries})"
                    )
                    time.sleep(wait_time)
                else:
                    raise

        if last_exception:
            raise last_exception

    def transfer(
        self,
        from_account: str,
        to_account: str,
        amount: float,
        use_auth: Optional[bool] = None,
        validate: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Transfer funds between accounts.

        Args:
            from_account: Source account ID
            to_account: Destination account ID
            amount: Amount to transfer
            use_auth: Override config.use_auth if provided
            validate: Whether to validate inputs before transfer

        Returns:
            Dictionary with transfer result if successful, None otherwise
        """
        # Sanitize inputs
        from_account = sanitize_account_id(from_account)
        to_account = sanitize_account_id(to_account)

        # Validate inputs
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
        headers = self._get_headers(use_auth)

        logger.info(f"Initiating transfer: {from_account} -> {to_account}, ${amount:.2f}")

        try:
            response = self._retry_request("POST", url, json=payload, headers=headers)
            result = response.json()

            status = result.get("status", "UNKNOWN")
            if status == "SUCCESS":
                logger.info(f"Transfer successful: {result.get('transactionId')}")
            else:
                logger.warning(f"Transfer failed: {result.get('message')}")

            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code}")
            try:
                error_detail = e.response.json()
                logger.error(f"Error details: {error_detail}")
            except:
                logger.error(f"Error text: {e.response.text[:200]}")
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")

        return None

    def validate_account(self, account_id: str, use_auth: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        """
        Validate if an account exists and is active.

        Args:
            account_id: Account ID to validate
            use_auth: Override config.use_auth if provided

        Returns:
            Validation result dictionary if successful, None otherwise
        """
        account_id = sanitize_account_id(account_id)
        url = f"{self.config.base_url}/accounts/validate/{account_id}"
        headers = self._get_headers(use_auth)

        logger.info(f"Validating account: {account_id}")

        try:
            response = self._retry_request("GET", url, headers=headers)
            result = response.json()
            logger.debug(f"Account validation result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error validating account: {e}")
            return None

    def get_balance(self, account_id: str, use_auth: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        """
        Get account balance.

        Args:
            account_id: Account ID
            use_auth: Override config.use_auth if provided

        Returns:
            Balance information if successful, None otherwise
        """
        account_id = sanitize_account_id(account_id)
        url = f"{self.config.base_url}/accounts/balance/{account_id}"
        headers = self._get_headers(use_auth)

        logger.info(f"Getting balance for account: {account_id}")

        try:
            response = self._retry_request("GET", url, headers=headers)
            result = response.json()
            logger.debug(f"Balance result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return None

    def get_all_accounts(self, use_auth: Optional[bool] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Get all accounts.

        Args:
            use_auth: Override config.use_auth if provided

        Returns:
            List of accounts if successful, None otherwise
        """
        url = f"{self.config.base_url}/accounts"
        headers = self._get_headers(use_auth)

        logger.info("Fetching all accounts")

        try:
            response = self._retry_request("GET", url, headers=headers)
            result = response.json()
            logger.info(f"Retrieved {len(result)} accounts")
            return result
        except Exception as e:
            logger.error(f"Error getting accounts: {e}")
            return None

    def get_transaction_history(
        self,
        limit: int = 10,
        use_auth: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get transaction history (requires JWT authentication).

        Args:
            limit: Number of transactions to retrieve (max 20)
            use_auth: Override config.use_auth if provided (defaults to True for this endpoint)

        Returns:
            Transaction history if successful, None otherwise
        """
        # This endpoint requires authentication
        if use_auth is None:
            use_auth = True

        url = f"{self.config.base_url}/transactions/history"
        params = {"limit": min(limit, 20)}
        headers = self._get_headers(use_auth)

        logger.info(f"Fetching transaction history (limit={limit})")

        try:
            response = self._retry_request("GET", url, params=params, headers=headers)
            result = response.json()
            logger.info("Transaction history retrieved successfully")
            return result
        except Exception as e:
            logger.error(f"Error getting transaction history: {e}")
            return None

    def refresh_token(self):
        """Force refresh the authentication token."""
        logger.info("Refreshing authentication token")
        self._token = self.auth_manager.get_token(
            username=self.config.username,
            password=self.config.password,
            scope=self.config.auth_scope,
            force_refresh=True
        )
        return self._token is not None
