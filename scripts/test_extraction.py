#!/usr/bin/env python3
"""
Test script to verify the data extraction works correctly by simulating the upload process.
"""
import os
import sys
import argparse
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.creiq.services.extraction_service import ExtractionService
from src.creiq.utils.logger import logger


def main():
    """Main function for test extraction."""
    parser = argparse.ArgumentParser(description="Test CREIQ data extraction")
    parser.add_argument(
        "roll_number",
        nargs="?",
        default="38-29-300-012-10400-0000",
        help="Roll number to test (default: 38-29-300-012-10400-0000)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode"
    )
    
    args = parser.parse_args()
    
    logger.info(f"Testing extraction for roll number: {args.roll_number}")
    
    # Create extraction service
    service = ExtractionService()
    
    # Run extraction in test mode
    results = service.extract_single_roll_number(args.roll_number, test_mode=True)
    
    # Print results
    if results["successful"] > 0:
        logger.info("Extraction test completed successfully!")
        logger.info(f"Results saved in: {results['output_directory']}")
    else:
        logger.error("Extraction test failed!")
        if results["errors"]:
            for error in results["errors"]:
                logger.error(f"Error: {error}")


if __name__ == "__main__":
    main() 