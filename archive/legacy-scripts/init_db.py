"""
Database initialization script.
Creates all tables and optionally seeds initial data.
Usage: python scripts/init_db.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.db.session import init_db, engine
from app.core.logging import configure_logging, get_logger


async def main() -> None:
    """Initialize the database."""
    settings = get_settings()
    configure_logging(debug=settings.debug)
    log = get_logger("init_db")

    log.info("initializing_database", url=settings.database_url)

    await init_db()
    log.info("database_initialized_successfully")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
