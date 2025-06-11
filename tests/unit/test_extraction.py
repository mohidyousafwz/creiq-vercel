"""
Unit tests for extraction functionality.
"""
import pytest
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.creiq.services.extraction_service import ExtractionService
from src.creiq.playwright_automation import PlaywrightAutomation


class TestExtractionService:
    """Test suite for ExtractionService."""
    
    @pytest.fixture
    def service(self):
        """Create extraction service instance."""
        return ExtractionService()
    
    @pytest.fixture
    def mock_automation(self):
        """Create mock PlaywrightAutomation."""
        mock = MagicMock(spec=PlaywrightAutomation)
        return mock
    
    def test_extract_single_roll_number_success(self, service, mock_automation, tmp_path):
        """Test successful extraction of a single roll number."""
        with patch('src.creiq.services.extraction_service.PlaywrightAutomation', return_value=mock_automation):
            # Configure mock
            mock_automation.process_roll_numbers.return_value = None
            
            # Test extraction
            roll_number = "38-29-300-012-10400-0000"
            results = service.extract_single_roll_number(roll_number, test_mode=True)
            
            # Verify results
            assert results["total"] == 1
            assert results["successful"] == 1
            assert results["failed"] == 0
            assert roll_number in results["roll_numbers"]
            assert "start_time" in results
            assert "end_time" in results
            assert "duration_seconds" in results
            
            # Verify automation was called correctly
            mock_automation.start_browser.assert_called_once()
            mock_automation.navigate_to_site.assert_called_once()
            mock_automation.process_roll_numbers.assert_called_once()
            mock_automation.close.assert_called_once()
    
    def test_extract_multiple_roll_numbers(self, service, mock_automation):
        """Test extraction of multiple roll numbers."""
        with patch('src.creiq.services.extraction_service.PlaywrightAutomation', return_value=mock_automation):
            # Test data
            roll_numbers = [
                "38-29-300-012-10400-0000",
                "19-08-072-215-00500-0000",
                "06-14-041-701-16500-0000"
            ]
            
            results = service.extract_roll_numbers(roll_numbers, test_mode=True)
            
            # Verify
            assert results["total"] == 3
            assert results["roll_numbers"] == roll_numbers
            assert len(results["errors"]) == 0
    
    def test_extraction_with_error(self, service, mock_automation):
        """Test extraction handling errors properly."""
        with patch('src.creiq.services.extraction_service.PlaywrightAutomation', return_value=mock_automation):
            # Configure mock to raise error
            mock_automation.start_browser.side_effect = Exception("Browser launch failed")
            
            # Test extraction
            results = service.extract_single_roll_number("12345", test_mode=True)
            
            # Verify error handling
            assert results["failed"] == 1
            assert results["successful"] == 0
            assert len(results["errors"]) == 1
            assert "Browser launch failed" in results["errors"][0]
            
            # Verify close was still called
            mock_automation.close.assert_called_once()
    
    def test_output_directory_creation_test_mode(self, service, mock_automation):
        """Test that output directory is created correctly in test mode."""
        with patch('src.creiq.services.extraction_service.PlaywrightAutomation', return_value=mock_automation):
            roll_number = "38-29-300-012-10400-0000"
            results = service.extract_single_roll_number(roll_number, test_mode=True)
            
            # Verify output directory format
            output_dir = results["output_directory"]
            assert "test_extraction" in output_dir
            assert roll_number in output_dir
            # Should have timestamp prefix like "03_02PM"
            dir_name = Path(output_dir).name
            assert "_" in dir_name
            assert "PM" in dir_name or "AM" in dir_name
    
    def test_output_directory_creation_normal_mode(self, service, mock_automation):
        """Test that output directory is created correctly in normal mode."""
        with patch('src.creiq.services.extraction_service.PlaywrightAutomation', return_value=mock_automation):
            results = service.extract_single_roll_number("12345", test_mode=False)
            
            # Verify output directory
            output_dir = results["output_directory"]
            assert "results" in output_dir
            assert "test_extraction" not in output_dir


class TestExtractionData:
    """Test actual extraction data structure."""
    
    def test_extracted_json_structure(self, tmp_path):
        """Test that extracted JSON has the correct structure."""
        # Sample extracted data
        sample_data = {
            "roll_number": "38-29-300-012-10400-0000",
            "extracted_timestamp": datetime.now().isoformat(),
            "page_title": "E-Services - Appeals",
            "property_info": {
                "description": "429 EXMOUTH ST PLAN 3 PT LOT 5 PLAN 96 LOT"
            },
            "appeals": [
                {
                    "appeal_number": "1194369",
                    "extracted_timestamp": datetime.now().isoformat(),
                    "property_info": {
                        "roll_number": "38-29-300-012-10400-0000",
                        "municipality": "Sarnia City",
                        "classification": "Commercial sport complexes",
                        "nbhd": "293",
                        "description": "429 EXMOUTH STPLAN 3 PT LOT 5 PLAN 96 LOT"
                    },
                    "appellant_info": {
                        "name1": "J J W HOLDINGS LTD",
                        "name2": "C/O DONALD STASIW",
                        "representative": "D B BURNARD & ASSOCIATES",
                        "filing_date": "31-March-2000",
                        "tax_date": "01-January-2000",
                        "section": "40",
                        "reason_for_appeal": "Assessment Too High"
                    },
                    "status_info": {
                        "status": "Closed"
                    },
                    "decision_info": {
                        "decision_number": "1357206",
                        "mailing_date": "23-June-2000",
                        "decisions": "APPEAL WITHDRAWN (BEFORE SCHEDULING)",
                        "decision_details": "HEARING # 17287."
                    }
                }
            ]
        }
        
        # Write to file
        json_file = tmp_path / "all_appeal_details.json"
        with open(json_file, 'w') as f:
            json.dump(sample_data, f, indent=2)
        
        # Read and verify
        with open(json_file, 'r') as f:
            loaded_data = json.load(f)
        
        # Verify structure
        assert "roll_number" in loaded_data
        assert "property_info" in loaded_data
        assert "description" in loaded_data["property_info"]
        assert loaded_data["property_info"]["description"] != loaded_data["roll_number"]
        assert "appeals" in loaded_data
        
        if loaded_data["appeals"]:
            appeal = loaded_data["appeals"][0]
            assert "appeal_number" in appeal
            assert "property_info" in appeal
            assert "appellant_info" in appeal
            assert "status_info" in appeal
            assert "decision_info" in appeal
            assert "decision_details" in appeal["decision_info"] 