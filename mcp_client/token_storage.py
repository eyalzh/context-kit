import json
import logging
import os
import stat
from pathlib import Path
from typing import Any

import keyring
from mcp.client.auth import TokenStorage
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

logger = logging.getLogger(__name__)

KEYCHAIN_STORAGE_VERSION = 2


class KeychainTokenStorageWithFallback(TokenStorage):
    """
    Dual storage strategy for OAuth tokens:
    1. Primary: System keychain (macOS Keychain, Windows Credential Manager, Linux Secret Service)
    2. Fallback: Secured file storage if keychain unavailable
    """

    def __init__(self, state, server_name: str):
        """Initialize with state object containing configuration."""
        self.state = state
        self.server_name = server_name
        self.service_name = f"contextkit_{KEYCHAIN_STORAGE_VERSION}"
        self.username = f"secrets_{server_name}"
        self.keychain_enabled = True

        # Determine fallback storage location
        self.fallback_dir = self._get_fallback_dir()
        self.fallback_file = self.fallback_dir / f"secrets_{server_name}.json"

        # Test keychain availability on init
        self._test_keychain_availability()

    def _get_fallback_dir(self) -> Path:
        """Get platform-specific application data directory."""

        if os.name == "nt":  # Windows
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        elif os.name == "posix":
            if os.environ.get("XDG_CONFIG_HOME"):
                base = Path(os.environ["XDG_CONFIG_HOME"])
            else:
                base = Path.home() / ".config"
        else:
            base = Path.home() / ".config"

        return base / "contextkit"

    def _test_keychain_availability(self):
        """Test if keychain is available and working."""
        try:
            # Try a simple operation to test keychain availability
            keyring.get_password(self.service_name, "test")
            logger.debug("Keychain access is available")
        except Exception as e:
            logger.warning(f"Keychain access failed, will use file fallback: {e}")
            self.keychain_enabled = False

    async def get_tokens(self) -> OAuthToken | None:
        """Get stored tokens from keychain or fallback storage."""
        # Try keychain first
        if self.keychain_enabled:
            try:
                token_data = keyring.get_password(self.service_name, f"{self.username}_tokens")
                if token_data:
                    token_dict = json.loads(token_data)
                    return OAuthToken(**token_dict)
            except Exception as e:
                logger.warning(f"Failed to get tokens from keychain: {e}")
                self.keychain_enabled = False

        # Fallback to file storage
        return await self._get_tokens_from_file()

    async def set_tokens(self, tokens: OAuthToken) -> None:
        """Store tokens in keychain or fallback storage."""
        token_data = json.dumps(tokens.model_dump())

        # Try keychain first
        if self.keychain_enabled:
            try:
                keyring.set_password(self.service_name, f"{self.username}_tokens", token_data)
                logger.debug("Tokens stored in keychain")
                return
            except Exception as e:
                logger.warning(f"Failed to store tokens in keychain: {e}")
                self.keychain_enabled = False

        # Fallback to file storage
        await self._set_tokens_to_file(tokens)

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        """Get stored client information from keychain or fallback storage."""
        # Try keychain first
        if self.keychain_enabled:
            try:
                client_data = keyring.get_password(self.service_name, f"{self.username}_client_info")
                if client_data:
                    client_dict = json.loads(client_data)
                    return OAuthClientInformationFull(**client_dict)
            except Exception as e:
                logger.warning(f"Failed to get client info from keychain: {e}")
                self.keychain_enabled = False

        # Fallback to file storage
        return await self._get_client_info_from_file()

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        """Store client information in keychain or fallback storage."""
        client_data = json.dumps(client_info.model_dump(mode="json"))

        # Try keychain first
        if self.keychain_enabled:
            try:
                keyring.set_password(self.service_name, f"{self.username}_client_info", client_data)
                logger.debug("Client info stored in keychain")
                return
            except Exception as e:
                logger.warning(f"Failed to store client info in keychain: {e}")
                self.keychain_enabled = False

        # Fallback to file storage
        await self._set_client_info_to_file(client_info)

    async def _get_tokens_from_file(self) -> OAuthToken | None:
        """Get tokens from fallback file storage."""
        try:
            if not self.fallback_file.exists():
                return None

            with open(self.fallback_file) as f:
                data = json.load(f)
                token_data = data.get("tokens")
                if token_data:
                    return OAuthToken(**token_data)
        except Exception as e:
            logger.error(f"Failed to read tokens from file: {e}")

        return None

    async def _set_tokens_to_file(self, tokens: OAuthToken) -> None:
        """Store tokens in fallback file storage."""
        await self._update_file_data({"tokens": tokens.model_dump()})

    async def _get_client_info_from_file(self) -> OAuthClientInformationFull | None:
        """Get client info from fallback file storage."""
        try:
            if not self.fallback_file.exists():
                return None

            with open(self.fallback_file) as f:
                data = json.load(f)
                client_data = data.get("client_info")
                if client_data:
                    return OAuthClientInformationFull(**client_data)
        except Exception as e:
            logger.error(f"Failed to read client info from file: {e}")

        return None

    async def _set_client_info_to_file(self, client_info: OAuthClientInformationFull) -> None:
        """Store client info in fallback file storage."""
        await self._update_file_data({"client_info": client_info.model_dump(mode="json")})

    async def _update_file_data(self, update_data: dict[str, Any]) -> None:
        """Update the fallback file with new data."""
        try:
            # Ensure directory exists
            self.fallback_dir.mkdir(parents=True, exist_ok=True)

            # Read existing data
            existing_data = {}
            if self.fallback_file.exists():
                with open(self.fallback_file) as f:
                    existing_data = json.load(f)

            # Update with new data
            existing_data.update(update_data)

            # Write back to file with restricted permissions from creation
            fd = os.open(self.fallback_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, stat.S_IRUSR | stat.S_IWUSR)
            with os.fdopen(fd, "w") as f:
                json.dump(existing_data, f, indent=2)
            logger.debug(f"Data stored in fallback file: {self.fallback_file}")

        except Exception as e:
            logger.error(f"Failed to update fallback file: {e}")
            raise
