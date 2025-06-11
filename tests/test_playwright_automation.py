import os
import json
import pytest
import threading
import tempfile
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime

# Import the class to test
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from creiq.playwright_automation import PlaywrightAutomation, GracefulShutdownException


class TestPlaywrightAutomation:
    """Test suite for PlaywrightAutomation class"""
    
    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Mock environment variables"""
        monkeypatch.setenv("URL", "https://test.arb.website.com")
        
    @pytest.fixture
    def shutdown_signal(self):
        """Create a shutdown signal for testing"""
        return threading.Event()
    
    @pytest.fixture
    def automation(self, mock_env, shutdown_signal):
        """Create PlaywrightAutomation instance with mocked environment"""
        return PlaywrightAutomation(headless=True, shutdown_signal=shutdown_signal)
    
    @pytest.fixture
    def mock_playwright(self):
        """Create mock playwright objects"""
        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_browser = MagicMock()
        mock_playwright_instance = MagicMock()
        
        # Setup the mock chain
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        mock_playwright_instance.firefox.launch.return_value = mock_browser
        
        return {
            'playwright': mock_playwright_instance,
            'browser': mock_browser,
            'context': mock_context,
            'page': mock_page
        }
    
    # ===== Unit Tests =====
    
    def test_initialization(self, automation):
        """Test proper initialization of PlaywrightAutomation"""
        assert automation.base_url == "https://test.arb.website.com"
        assert automation.headless is True
        assert automation.playwright is None
        assert automation.browser is None
        assert automation.context is None
        assert automation.page is None
        
    def test_initialization_no_url(self, shutdown_signal, monkeypatch):
        """Test initialization fails without URL in environment"""
        # Remove URL from environment and ensure dotenv doesn't load it
        monkeypatch.delenv("URL", raising=False)
        # Temporarily prevent dotenv from loading
        monkeypatch.setattr("creiq.playwright_automation.load_dotenv", lambda: None)
        
        with pytest.raises(ValueError, match="URL not found in environment variables"):
            PlaywrightAutomation(shutdown_signal=shutdown_signal)
    
    @patch('creiq.playwright_automation.sync_playwright')
    def test_start_browser_success(self, mock_sync_playwright, automation, mock_playwright):
        """Test successful browser startup"""
        mock_sync_playwright.return_value.start.return_value = mock_playwright['playwright']
        
        automation.start_browser()
        
        assert automation.playwright == mock_playwright['playwright']
        assert automation.browser == mock_playwright['browser']
        assert automation.context == mock_playwright['context']
        assert automation.page == mock_playwright['page']
        
        # Verify browser launch args
        launch_call = mock_playwright['playwright'].firefox.launch.call_args
        assert launch_call[1]['headless'] is True
        assert '--no-sandbox' in launch_call[1]['args']
        assert '--ignore-ssl-errors' in launch_call[1]['args']
    
    @patch('creiq.playwright_automation.sync_playwright')
    def test_start_browser_with_shutdown_signal(self, mock_sync_playwright, automation, mock_playwright):
        """Test browser startup interrupted by shutdown signal"""
        mock_sync_playwright.return_value.start.return_value = mock_playwright['playwright']
        automation.shutdown_signal.set()
        
        with pytest.raises(GracefulShutdownException):
            automation.start_browser()
    
    def test_navigate_to_site_no_browser(self, automation):
        """Test navigation fails when browser not started"""
        with pytest.raises(RuntimeError, match="Browser not started"):
            automation.navigate_to_site()
    
    def test_navigate_to_site_success(self, automation, mock_playwright):
        """Test successful navigation to site"""
        automation.page = mock_playwright['page']
        mock_playwright['page'].title.return_value = "ARB E-Status Appeals"
        
        automation.navigate_to_site()
        
        mock_playwright['page'].goto.assert_called_with(
            "https://test.arb.website.com", 
            timeout=60000
        )
        mock_playwright['page'].wait_for_load_state.assert_called_with(
            "networkidle", 
            timeout=60000
        )
    
    def test_enter_roll_number_success(self, automation, mock_playwright):
        """Test entering roll number into multiple fields"""
        automation.page = mock_playwright['page']
        roll_number = "1908072215005000000"
        
        automation.enter_roll_number(roll_number)
        
        # Verify each segment is filled correctly
        expected_calls = [
            call('#MainContent_txtRollNo1', '19'),
            call('#MainContent_txtRollNo2', '08'),
            call('#MainContent_txtRollNo3', '072'),
            call('#MainContent_txtRollNo4', '215'),
            call('#MainContent_txtRollNo5', '00500'),
            call('#MainContent_txtRollNo6', '0000')
        ]
        
        mock_playwright['page'].fill.assert_has_calls(expected_calls)
    
    def test_enter_roll_number_with_dashes(self, automation, mock_playwright):
        """Test entering roll number with non-digit characters"""
        automation.page = mock_playwright['page']
        roll_number = "19-08-072-215-00500-0000"
        
        automation.enter_roll_number(roll_number)
        
        # Should strip non-digits and still work
        assert mock_playwright['page'].fill.call_count == 6
    
    def test_enter_roll_number_too_short(self, automation, mock_playwright):
        """Test entering roll number that's too short (pads with zeros)"""
        automation.page = mock_playwright['page']
        roll_number = "123456789"  # Only 9 digits
        
        automation.enter_roll_number(roll_number)
        
        # Should pad to 19 digits
        # "123456789" -> "1234567890000000000"
        expected_calls = [
            call('#MainContent_txtRollNo1', '12'),
            call('#MainContent_txtRollNo2', '34'),
            call('#MainContent_txtRollNo3', '567'),
            call('#MainContent_txtRollNo4', '890'),
            call('#MainContent_txtRollNo5', '00000'),
            call('#MainContent_txtRollNo6', '0000')
        ]
        
        mock_playwright['page'].fill.assert_has_calls(expected_calls)
    
    def test_submit_search_success(self, automation, mock_playwright):
        """Test successful search submission"""
        automation.page = mock_playwright['page']
        
        result = automation.submit_search()
        
        assert result is True
        mock_playwright['page'].click.assert_called_with('#MainContent_btnSubmit')
        mock_playwright['page'].wait_for_load_state.assert_called_with(
            "networkidle", 
            timeout=30000
        )
    
    def test_submit_search_failure(self, automation, mock_playwright):
        """Test search submission failure"""
        automation.page = mock_playwright['page']
        mock_playwright['page'].click.side_effect = Exception("Click failed")
        
        result = automation.submit_search()
        
        assert result is False
    
    def test_save_html_content(self, automation, mock_playwright):
        """Test saving HTML content to file"""
        automation.page = mock_playwright['page']
        mock_playwright['page'].content.return_value = "<html><body>Test content</body></html>"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_file = f.name
        
        try:
            automation.save_html_content(temp_file)
            
            with open(temp_file, 'r') as f:
                content = f.read()
            
            assert content == "<html><body>Test content</body></html>"
        finally:
            os.unlink(temp_file)
    
    def test_extract_data_to_json(self, automation, mock_playwright):
        """Test data extraction (with current placeholder implementation)"""
        automation.page = mock_playwright['page']
        mock_playwright['page'].title.return_value = "Test Page Title"
        roll_number = "1908072215005000000"
        
        data = automation.extract_data_to_json(roll_number)
        
        assert data['roll_number'] == roll_number
        assert data['page_title'] == "Test Page Title"
        assert 'extracted_timestamp' in data
        assert isinstance(data['property_info'], dict)
        assert isinstance(data['appeal_info'], list)
        assert isinstance(data['raw_tables'], list)
    
    def test_save_json_data(self, automation):
        """Test saving JSON data to file"""
        test_data = {
            "roll_number": "1908072215005000000",
            "page_title": "Test",
            "property_info": {"address": "123 Test St"}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name
        
        try:
            automation.save_json_data(test_data, temp_file)
            
            with open(temp_file, 'r') as f:
                loaded_data = json.load(f)
            
            assert loaded_data == test_data
        finally:
            os.unlink(temp_file)
    
    def test_take_screenshot(self, automation, mock_playwright):
        """Test taking screenshot"""
        automation.page = mock_playwright['page']
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as f:
            temp_file = f.name
        
        try:
            automation.take_screenshot(temp_file)
            mock_playwright['page'].screenshot.assert_called_with(path=temp_file)
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_close_resources(self, automation, mock_playwright):
        """Test closing browser resources"""
        # Setup mocked resources
        automation.playwright = mock_playwright['playwright']
        automation.browser = mock_playwright['browser']
        automation.context = mock_playwright['context']
        automation.page = mock_playwright['page']
        
        automation.close()
        
        # Verify all resources were closed
        mock_playwright['page'].close.assert_called_once()
        mock_playwright['context'].close.assert_called_once()
        mock_playwright['browser'].close.assert_called_once()
        mock_playwright['playwright'].stop.assert_called_once()
        
        # Verify resources are set to None
        assert automation.page is None
        assert automation.context is None
        assert automation.browser is None
        assert automation.playwright is None
    
    def test_close_partial_resources(self, automation, mock_playwright):
        """Test closing when only some resources are initialized"""
        # Only browser and playwright initialized
        automation.playwright = mock_playwright['playwright']
        automation.browser = mock_playwright['browser']
        
        automation.close()
        
        # Should not raise errors
        mock_playwright['browser'].close.assert_called_once()
        mock_playwright['playwright'].stop.assert_called_once()
    
    def test_close_with_errors(self, automation, mock_playwright):
        """Test close continues even if individual closes fail"""
        automation.playwright = mock_playwright['playwright']
        automation.browser = mock_playwright['browser']
        automation.context = mock_playwright['context']
        automation.page = mock_playwright['page']
        
        # Make page.close() raise an error
        mock_playwright['page'].close.side_effect = Exception("Page close failed")
        
        # Should not raise, just log warning
        automation.close()
        
        # Other resources should still be closed
        mock_playwright['context'].close.assert_called_once()
        mock_playwright['browser'].close.assert_called_once()
        mock_playwright['playwright'].stop.assert_called_once()
    
    # ===== Integration Tests =====
    
    @patch('creiq.playwright_automation.sync_playwright')
    def test_process_single_roll_number(self, mock_sync_playwright, automation, mock_playwright):
        """Test processing a single roll number end-to-end"""
        # Setup
        mock_sync_playwright.return_value.start.return_value = mock_playwright['playwright']
        automation.start_browser()
        
        # Mock page behaviors
        mock_playwright['page'].query_selector.return_value = None  # No error message
        mock_playwright['page'].title.return_value = "Results Page"
        mock_playwright['page'].content.return_value = "<html>Results</html>"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            roll_numbers = ["1908072215005000000"]
            automation.process_roll_numbers(roll_numbers, temp_dir)
            
            # Verify output files were created
            roll_dir = os.path.join(temp_dir, "1908072215005000000")
            assert os.path.exists(roll_dir)
            
            json_file = os.path.join(roll_dir, "extracted_data.json")
            assert os.path.exists(json_file)
            
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            assert data['roll_number'] == "1908072215005000000"
    
    @patch('creiq.playwright_automation.sync_playwright')
    def test_process_roll_number_no_records(self, mock_sync_playwright, automation, mock_playwright):
        """Test processing when no records are found"""
        # Setup
        mock_sync_playwright.return_value.start.return_value = mock_playwright['playwright']
        automation.start_browser()
        
        # Mock "No records found" scenario
        error_element = MagicMock()
        error_element.is_visible.return_value = True
        error_element.text_content.return_value = "No records found"
        mock_playwright['page'].query_selector.return_value = error_element
        
        with tempfile.TemporaryDirectory() as temp_dir:
            roll_numbers = ["0000000000000000000"]
            automation.process_roll_numbers(roll_numbers, temp_dir)
            
            # Verify no_records_found.txt was created
            roll_dir = os.path.join(temp_dir, "0000000000000000000")
            no_records_file = os.path.join(roll_dir, "no_records_found.txt")
            assert os.path.exists(no_records_file)
    
    @patch('creiq.playwright_automation.sync_playwright')
    def test_process_multiple_roll_numbers_with_error(self, mock_sync_playwright, automation, mock_playwright):
        """Test processing multiple roll numbers with one error"""
        # Setup
        mock_sync_playwright.return_value.start.return_value = mock_playwright['playwright']
        automation.start_browser()
        
        # First roll number succeeds, second fails
        mock_playwright['page'].fill.side_effect = [
            None, None, None, None, None, None,  # First roll number fills succeed
            Exception("Fill failed"),  # Second roll number first fill fails
            None, None, None, None, None  # Remaining fills
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            roll_numbers = ["1908072215005000000", "1908072215005000001"]
            automation.process_roll_numbers(roll_numbers, temp_dir)
            
            # First should have data, second should have error log
            first_dir = os.path.join(temp_dir, "1908072215005000000")
            second_dir = os.path.join(temp_dir, "1908072215005000001")
            
            assert os.path.exists(os.path.join(first_dir, "extracted_data.json"))
            assert os.path.exists(os.path.join(second_dir, "error_log.txt"))
    
    def test_shutdown_during_process(self, automation, mock_playwright):
        """Test graceful shutdown during processing"""
        automation.page = mock_playwright['page']
        
        def set_shutdown_on_second_call(*args):
            if mock_playwright['page'].fill.call_count == 2:
                automation.shutdown_signal.set()
        
        mock_playwright['page'].fill.side_effect = set_shutdown_on_second_call
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(GracefulShutdownException):
                automation.process_roll_numbers(["1908072215005000000"], temp_dir)
    
    # ===== Edge Case Tests =====
    
    def test_check_shutdown_when_not_set(self, automation):
        """Test _check_shutdown when signal is not set"""
        # Should not raise
        automation._check_shutdown()
    
    def test_check_shutdown_when_set(self, automation):
        """Test _check_shutdown when signal is set"""
        automation.shutdown_signal.set()
        
        with pytest.raises(GracefulShutdownException):
            automation._check_shutdown()
    
    def test_process_empty_roll_numbers_list(self, automation, mock_playwright):
        """Test processing empty list of roll numbers"""
        automation.page = mock_playwright['page']
        
        with tempfile.TemporaryDirectory() as temp_dir:
            automation.process_roll_numbers([], temp_dir)
            # Should complete without error
    
    def test_special_characters_in_roll_number(self, automation, mock_playwright):
        """Test roll number with special characters in directory name"""
        automation.page = mock_playwright['page']
        mock_playwright['page'].query_selector.return_value = None
        
        with tempfile.TemporaryDirectory() as temp_dir:
            roll_numbers = ["19/08*072?215:00500|0000"]
            automation.process_roll_numbers(roll_numbers, temp_dir)
            
            # Directory should be created with sanitized name
            sanitized_dir = os.path.join(temp_dir, "19_08_072_215_00500_0000")
            assert os.path.exists(sanitized_dir)
    
    @pytest.mark.parametrize("roll_number,expected_segments", [
        ("1908072215005000000", ["19", "08", "072", "215", "00500", "0000"]),
        ("123", ["12", "30", "000", "000", "00000", "0000"]),  # Too short
        ("12345678901234567890123", ["12", "34", "567", "890", "12345", "6789"]),  # Too long
        ("", ["00", "00", "000", "000", "00000", "0000"]),  # Empty
    ])
    def test_roll_number_parsing_edge_cases(self, automation, mock_playwright, roll_number, expected_segments):
        """Test various edge cases in roll number parsing"""
        automation.page = mock_playwright['page']
        
        automation.enter_roll_number(roll_number)
        
        # Verify the expected segments were filled
        for i, segment in enumerate(expected_segments):
            selector = f'#MainContent_txtRollNo{i+1}'
            assert mock_playwright['page'].fill.call_args_list[i] == call(selector, segment) 