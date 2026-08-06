"""PyInstaller entry point for the bundled local Market Pulse API."""

import os

import uvicorn

from api.scheduler import start_background_scheduler


if __name__ == "__main__":
    scheduler = start_background_scheduler()
    try:
        uvicorn.run(
            "api.main:app",
            host=os.getenv("MARKET_PULSE_API_HOST", "127.0.0.1"),
            port=int(os.getenv("MARKET_PULSE_API_PORT", "8765")),
            log_level=os.getenv("MARKET_PULSE_LOG_LEVEL", "warning"),
        )
    finally:
        scheduler.shutdown(wait=False)
