#!/usr/bin/env python3
"""
Main entry point for CREIQ Data Extraction Service.
"""
import sys
import uvicorn
from src.creiq.utils.logger import logger
from src.creiq.config.settings import API_HOST, API_PORT

def main():
    """Run the CREIQ web application."""
    logger.info("Starting CREIQ Data Extraction Service...")
    logger.info(f"Dashboard will be available at http://{API_HOST}:{API_PORT}")
    
    try:
        # Run the web dashboard
        uvicorn.run(
            "src.creiq.web_app:app",
            host=API_HOST,
            port=API_PORT,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()