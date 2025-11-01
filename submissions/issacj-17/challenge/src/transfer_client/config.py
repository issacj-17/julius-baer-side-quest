"""Configuration management for transfer client."""
import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import json

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Configuration for the banking transfer client."""

    # API Settings
    base_url: str = field(default_factory=lambda: os.getenv("BANKING_API_URL", "http://localhost:8123"))
    timeout: float = field(default_factory=lambda: float(os.getenv("BANKING_API_TIMEOUT", "10.0")))

    # Authentication
    username: str = field(default_factory=lambda: os.getenv("BANKING_USERNAME", "alice"))
    password: str = field(default_factory=lambda: os.getenv("BANKING_PASSWORD", "password123"))
    use_auth: bool = field(default_factory=lambda: os.getenv("BANKING_USE_AUTH", "true").lower() == "true")
    auth_scope: str = field(default_factory=lambda: os.getenv("BANKING_AUTH_SCOPE", "transfer"))

    # Retry Settings
    max_retries: int = field(default_factory=lambda: int(os.getenv("BANKING_MAX_RETRIES", "3")))
    retry_backoff_factor: float = field(default_factory=lambda: float(os.getenv("BANKING_RETRY_BACKOFF", "1.0")))
    retry_on_status: list = field(default_factory=lambda: [500, 502, 503, 504])

    # Logging
    log_level: str = field(default_factory=lambda: os.getenv("BANKING_LOG_LEVEL", "INFO"))

    @classmethod
    def from_file(cls, config_path: Path) -> "Config":
        """
        Load configuration from a JSON file.

        Args:
            config_path: Path to the configuration file

        Returns:
            Config instance
        """
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return cls()

        try:
            with open(config_path) as f:
                data = json.load(f)
            logger.info(f"Loaded configuration from {config_path}")
            return cls(**data)
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
            return cls()

    @classmethod
    def from_env_or_file(cls, config_path: Optional[Path] = None) -> "Config":
        """
        Load configuration from environment variables or file.

        Priority: Environment variables > Config file > Defaults

        Args:
            config_path: Optional path to configuration file

        Returns:
            Config instance
        """
        # Start with file config if provided
        if config_path and config_path.exists():
            config = cls.from_file(config_path)
        else:
            config = cls()

        logger.debug(f"Configuration loaded: base_url={config.base_url}, use_auth={config.use_auth}")
        return config

    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "base_url": self.base_url,
            "timeout": self.timeout,
            "username": self.username,
            "password": "***REDACTED***",  # Don't expose password
            "use_auth": self.use_auth,
            "auth_scope": self.auth_scope,
            "max_retries": self.max_retries,
            "retry_backoff_factor": self.retry_backoff_factor,
            "log_level": self.log_level,
        }

    def save_to_file(self, config_path: Path):
        """
        Save configuration to a JSON file.

        Args:
            config_path: Path where to save the configuration
        """
        data = {
            "base_url": self.base_url,
            "timeout": self.timeout,
            "username": self.username,
            "password": self.password,
            "use_auth": self.use_auth,
            "auth_scope": self.auth_scope,
            "max_retries": self.max_retries,
            "retry_backoff_factor": self.retry_backoff_factor,
            "log_level": self.log_level,
        }

        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Configuration saved to {config_path}")
        except Exception as e:
            logger.error(f"Error saving config to {config_path}: {e}")
