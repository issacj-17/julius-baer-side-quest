"""Unit tests for config module."""
import pytest
import os
import json
from pathlib import Path
from transfer_client.config import Config


@pytest.mark.unit
class TestConfig:
    """Test Config class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = Config()
        assert config.base_url == "http://localhost:8123"
        assert config.timeout == 10.0
        assert config.username == "alice"
        assert config.use_auth is True
        assert config.max_retries == 3

    def test_custom_config(self):
        """Test custom configuration values."""
        config = Config(
            base_url="http://example.com",
            timeout=20.0,
            username="bob",
            max_retries=5
        )
        assert config.base_url == "http://example.com"
        assert config.timeout == 20.0
        assert config.username == "bob"
        assert config.max_retries == 5

    def test_config_from_env(self, monkeypatch):
        """Test configuration from environment variables."""
        monkeypatch.setenv("BANKING_API_URL", "http://env-test.com")
        monkeypatch.setenv("BANKING_USERNAME", "env_user")
        monkeypatch.setenv("BANKING_MAX_RETRIES", "7")
        monkeypatch.setenv("BANKING_USE_AUTH", "false")

        config = Config()
        assert config.base_url == "http://env-test.com"
        assert config.username == "env_user"
        assert config.max_retries == 7
        assert config.use_auth is False

    def test_config_to_dict_redacts_password(self):
        """Test that password is redacted in dict representation."""
        config = Config(password="secret123")
        config_dict = config.to_dict()
        assert config_dict["password"] == "***REDACTED***"
        assert config.password == "secret123"  # Original unchanged

    def test_config_from_file(self, tmp_path):
        """Test loading configuration from file."""
        config_file = tmp_path / "config.json"
        config_data = {
            "base_url": "http://file-test.com",
            "username": "file_user",
            "max_retries": 10
        }
        config_file.write_text(json.dumps(config_data))

        config = Config.from_file(config_file)
        assert config.base_url == "http://file-test.com"
        assert config.username == "file_user"
        assert config.max_retries == 10

    def test_config_from_nonexistent_file(self, tmp_path):
        """Test loading from non-existent file returns defaults."""
        config_file = tmp_path / "nonexistent.json"
        config = Config.from_file(config_file)
        # Should return default config
        assert config.base_url == "http://localhost:8123"

    def test_config_save_to_file(self, tmp_path):
        """Test saving configuration to file."""
        config = Config(
            base_url="http://save-test.com",
            username="save_user",
            password="save_pass"
        )
        config_file = tmp_path / "saved_config.json"
        config.save_to_file(config_file)

        # Verify file was created
        assert config_file.exists()

        # Verify contents
        saved_data = json.loads(config_file.read_text())
        assert saved_data["base_url"] == "http://save-test.com"
        assert saved_data["username"] == "save_user"
        assert saved_data["password"] == "save_pass"  # Not redacted in file

    def test_config_from_env_or_file_prefers_file(self, tmp_path, monkeypatch):
        """Test that file config takes precedence."""
        # Set env var
        monkeypatch.setenv("BANKING_API_URL", "http://env.com")

        # Create config file
        config_file = tmp_path / "config.json"
        config_data = {"base_url": "http://file.com"}
        config_file.write_text(json.dumps(config_data))

        config = Config.from_env_or_file(config_file)
        # File should be loaded, but env vars still override dataclass defaults
        # Since we're loading from file first, we get file values
        assert config.base_url == "http://file.com"

    def test_config_types(self):
        """Test configuration type conversions."""
        config = Config(
            timeout=15.5,
            max_retries=3,
            retry_backoff_factor=2.0
        )
        assert isinstance(config.timeout, float)
        assert isinstance(config.max_retries, int)
        assert isinstance(config.retry_backoff_factor, float)
