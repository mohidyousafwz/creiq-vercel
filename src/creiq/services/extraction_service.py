"""
Extraction service for managing roll number data extraction.
"""
import os
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from src.creiq.playwright_automation import PlaywrightAutomation
from src.creiq.utils.logger import logger
from src.creiq.config.settings import RESULTS_DIR, TEST_EXTRACTION_DIR, BROWSER_HEADLESS


class ExtractionService:
    """Service for managing data extraction operations."""
    
    def __init__(self, shutdown_signal: Optional[threading.Event] = None):
        """
        Initialize the extraction service.
        
        Args:
            shutdown_signal: Optional shutdown signal for graceful shutdown
        """
        self.shutdown_signal = shutdown_signal
        self.automation: Optional[PlaywrightAutomation] = None
    
    def extract_roll_numbers(self, roll_numbers: List[str], test_mode: bool = False) -> Dict[str, Any]:
        """
        Extract data for a list of roll numbers.
        
        Args:
            roll_numbers: List of roll numbers to process
            test_mode: If True, save results in test_extraction folder with timestamp
            
        Returns:
            Dictionary with extraction results and statistics
        """
        start_time = datetime.now()
        
        # Determine output directory
        if test_mode:
            timestamp = datetime.now().strftime("%I_%M%p")
            first_roll = roll_numbers[0] if roll_numbers else "test"
            output_dir = TEST_EXTRACTION_DIR / f"{timestamp}-{first_roll}"
        else:
            output_dir = RESULTS_DIR
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize results
        results = {
            "start_time": start_time.isoformat(),
            "roll_numbers": roll_numbers,
            "total": len(roll_numbers),
            "successful": 0,
            "failed": 0,
            "errors": [],
            "output_directory": str(output_dir)
        }
        
        try:
            # Initialize automation
            self.automation = PlaywrightAutomation(
                headless=BROWSER_HEADLESS,
                shutdown_signal=self.shutdown_signal
            )
            
            logger.info(f"Starting extraction for {len(roll_numbers)} roll numbers")
            self.automation.start_browser()
            self.automation.navigate_to_site()
            
            # Process roll numbers
            self.automation.process_roll_numbers(roll_numbers, str(output_dir))
            
            # Update success count (basic implementation for now)
            results["successful"] = len(roll_numbers)
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            results["errors"].append(str(e))
            results["failed"] = len(roll_numbers)
        finally:
            if self.automation:
                self.automation.close()
            
            # Calculate duration
            end_time = datetime.now()
            results["end_time"] = end_time.isoformat()
            results["duration_seconds"] = (end_time - start_time).total_seconds()
        
        return results
    
    def extract_single_roll_number(self, roll_number: str, test_mode: bool = False) -> Dict[str, Any]:
        """
        Extract data for a single roll number.
        
        Args:
            roll_number: Roll number to process
            test_mode: If True, save results in test_extraction folder
            
        Returns:
            Dictionary with extraction results
        """
        return self.extract_roll_numbers([roll_number], test_mode=test_mode) 