#!/usr/bin/env python3
"""
CREIQ Data Extraction Service - Main Entry Point

This application extracts appeal data from the ARB website.
"""
import sys
import asyncio

# Fix for Windows asyncio issues - must be done before any other asyncio operations
if sys.platform == 'win32':
    # Set Windows ProactorEventLoop to prevent NotImplementedError
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from src.creiq.config.settings import API_HOST, API_PORT, API_RELOAD
from src.creiq.utils.logger import logger


def main():
    """Run the CREIQ API server."""
    logger.info("Starting CREIQ Data Extraction Service...")
    logger.info(f"API will be available at http://{API_HOST}:{API_PORT}")
    logger.info("Documentation available at http://{API_HOST}:{API_PORT}/docs")
    
    try:
        uvicorn.run(
            "src.creiq.api:app",
            host=API_HOST,
            port=API_PORT,
            reload=API_RELOAD,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("Shutting down CREIQ service...")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()