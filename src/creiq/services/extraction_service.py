"""
Extraction service for managing roll number data extraction.
"""
import os
import json
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from sqlalchemy.orm import Session

from src.creiq.playwright_automation import PlaywrightAutomation
from src.creiq.utils.logger import logger
from src.creiq.config.settings import RESULTS_DIR, TEST_EXTRACTION_DIR, BROWSER_HEADLESS
from src.creiq.database.database import SessionLocal
from src.creiq.database.service import DatabaseService


class ExtractionService:
    """Service for managing data extraction operations."""
    
    def __init__(self, shutdown_signal: Optional[threading.Event] = None, save_to_db: bool = True):
        """
        Initialize the extraction service.
        
        Args:
            shutdown_signal: Optional shutdown signal for graceful shutdown
            save_to_db: Whether to save results to database (default: True)
        """
        self.shutdown_signal = shutdown_signal
        self.automation: Optional[PlaywrightAutomation] = None
        self.save_to_db = save_to_db
        self.db_session: Optional[Session] = None
        self.db_service: Optional[DatabaseService] = None
        
        # Initialize database session if saving to DB
        if self.save_to_db:
            self.db_session = SessionLocal()
            self.db_service = DatabaseService(self.db_session)
    
    def __del__(self):
        """Clean up database session."""
        if self.db_session:
            self.db_session.close()
    
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
            
            # Save results to database if enabled
            if self.save_to_db:
                self._save_results_to_database(roll_numbers, str(output_dir))
            
            # Update success count
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
    
    def _save_results_to_database(self, roll_numbers: List[str], output_dir: str) -> None:
        """Save extraction results to database."""
        for roll_number in roll_numbers:
            try:
                # Construct paths to result files
                roll_dir = Path(output_dir) / roll_number.replace('/', '_').replace('\\', '_').replace(':', '_')
                summary_json_path = roll_dir / "appeal_summary.json"
                detail_json_path = roll_dir / "appeal_details.json"
                
                # Read summary data
                summary_data = {}
                if summary_json_path.exists():
                    with open(summary_json_path, 'r', encoding='utf-8') as f:
                        summary_data = json.load(f)
                
                # Read detail data
                detail_data = {}
                if detail_json_path.exists():
                    with open(detail_json_path, 'r', encoding='utf-8') as f:
                        detail_data = json.load(f)
                
                # Save to database
                if self.db_service and summary_data:
                    self.db_service.save_extraction_results(roll_number, summary_data, detail_data)
                    
            except Exception as e:
                logger.error(f"Error saving {roll_number} to database: {e}")
                continue
    
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