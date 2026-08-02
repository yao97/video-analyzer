"""
Encryption key generator.
Generates a Fernet-compatible encryption key for API Key encryption.
Usage: python scripts/generate_key.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.security import APIKeyManager, generate_api_token


def main() -> None:
    """Generate and display encryption keys."""
    print("=" * 60)
    print("Video Content Analyzer — Key Generator")
    print("=" * 60)

    # Generate Fernet encryption key
    encryption_key = APIKeyManager.generate_encryption_key()
    print(f"\nEncryption Key (for ENCRYPTION_KEY in .env):")
    print(f"  {encryption_key}")

    # Generate an API token (for client authentication)
    api_token = generate_api_token()
    print(f"\nAPI Token (for client authentication):")
    print(f"  {api_token}")

    print("\n" + "=" * 60)
    print("Add the encryption key to your .env file:")
    print(f"  ENCRYPTION_KEY={encryption_key}")
    print("=" * 60)


if __name__ == "__main__":
    main()
