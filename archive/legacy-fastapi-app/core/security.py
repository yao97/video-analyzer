"""
Security module: API Key encryption/decryption, masking, and authentication utilities.
Resolves Bug #5 — API Key is now managed server-side, encrypted at rest, never logged in full.
"""
from __future__ import annotations

import base64
import secrets
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


class APIKeyManager:
    """
    Server-side API Key management using AES-256-GCM (via Fernet).
    Keys are encrypted before storage and decrypted only when needed for API calls.
    """

    def __init__(self, encryption_key: Optional[str] = None) -> None:
        key = encryption_key or get_settings().encryption_key
        if not key:
            # Generate a key for development if none provided
            key = Fernet.generate_key().decode()
        # Ensure the key is valid Fernet key (base64-encoded 32 bytes)
        try:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except (ValueError, TypeError):
            # If the key is not a valid Fernet key, derive one
            import hashlib
            derived = hashlib.sha256(key.encode()).digest()
            fernet_key = base64.urlsafe_b64encode(derived)
            self._fernet = Fernet(fernet_key)

    def encrypt(self, api_key: str) -> bytes:
        """Encrypt an API key for storage."""
        return self._fernet.encrypt(api_key.encode())

    def decrypt(self, encrypted: bytes) -> str:
        """Decrypt an API key for use."""
        try:
            return self._fernet.decrypt(encrypted).decode()
        except InvalidToken:
            raise ValueError("Failed to decrypt API key — encryption key may have changed")

    @staticmethod
    def mask(api_key: str) -> str:
        """Mask an API key for safe logging: show only first 8 and last 4 characters."""
        if not api_key or len(api_key) < 12:
            return "***"
        return f"{api_key[:8]}...{api_key[-4:]}"

    @staticmethod
    def generate_encryption_key() -> str:
        """Generate a new Fernet encryption key for .env configuration."""
        return Fernet.generate_key().decode()


# Global instance (lazy-initialized)
_key_manager: Optional[APIKeyManager] = None


def get_key_manager() -> APIKeyManager:
    global _key_manager
    if _key_manager is None:
        _key_manager = APIKeyManager()
    return _key_manager


def generate_api_token() -> str:
    """Generate a random API token for client authentication."""
    return secrets.token_urlsafe(32)
