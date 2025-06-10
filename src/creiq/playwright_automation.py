import os
import time
import re
import json
import datetime
import logging
import threading
import traceback # Ensure traceback is imported
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

# Configure logger for automation (use Uvicorn error logger)
logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.INFO)

# Define custom exception for graceful shutdown
class GracefulShutdownException(Exception):
    """Custom exception to signal graceful shutdown."""
    pass

class PlaywrightAutomation:
    """
    A base class for automating interactions with the ARB website using Playwright.
    """
    
    def __init__(self, headless: bool = False, shutdown_signal: Optional[threading.Event] = None): # Modified
        """
        Initialize the Playwright automation with browser settings.
        
        Args:
            headless (bool): Whether to run the browser in headless mode (default: False)
            shutdown_signal (threading.Event, optional): Event to signal shutdown.
        """
        # Load environment variables
        load_dotenv()
        
        # Get the URL from environment variables
        self.base_url = os.getenv('URL')
        if not self.base_url:
            raise ValueError("URL not found in environment variables. Make sure .env file exists with URL key.")
        
        # Initialize playwright objects as None
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        # Browser configuration
        self.headless = headless
        self.shutdown_signal = shutdown_signal # Added
    
    def _check_shutdown(self): # Added
        """Checks if shutdown is signaled and raises exception if it is."""
        if self.shutdown_signal and self.shutdown_signal.is_set():
            logger.info("Shutdown signal received, initiating graceful shutdown of Playwright.")
            # self.close() # Calling close() here can lead to recursion if close() also calls _check_shutdown() or if called from within close().
            # It's better to let the finally block in the main processing task handle the full cleanup.
            raise GracefulShutdownException("Playwright automation shutting down gracefully.")

    def start_browser(self) -> None:
        """
        Start the browser session.
        """
        try:
            self._check_shutdown() 
            logger.info("Starting Playwright...")
            self.playwright = sync_playwright().start()
            
            self._check_shutdown() 
            logger.info("Launching browser...")
            launch_args = [
                '--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu', 
                '--disable-web-security', '--disable-features=VizDisplayCompositor',
                '--ignore-certificate-errors', '--ignore-ssl-errors', 
                '--ignore-certificate-errors-spki-list', '--ignore-ssl-errors-types'
            ]
            self.browser = self.playwright.firefox.launch(headless=self.headless, args=launch_args) # Added launch_args
            
            self._check_shutdown() 
            logger.info("Creating browser context...")
            self.context = self.browser.new_context(
                viewport={"width": 1600, "height": 900},
                ignore_https_errors=True
            )
            
            self._check_shutdown() 
            logger.info("Creating new page...")
            self.page = self.context.new_page()
            logger.info("Browser started successfully!")
            
        except GracefulShutdownException: 
            raise
        except Exception as e:
            logger.error(f"Error starting browser: {e}")
            self.close() 
            raise
    
    def navigate_to_site(self) -> None:
        """
        Navigate to the base URL from environment variables.
        """
        self._check_shutdown() 
        if not self.page:
            if self.shutdown_signal and self.shutdown_signal.is_set(): # Check before raising runtime error
                 raise GracefulShutdownException("Shutdown before page initialization.")
            raise RuntimeError("Browser not started or page not initialized. Call start_browser() first.")
        
        try:
            logger.info(f"Navigating to: {self.base_url}")
            self.page.goto(self.base_url, timeout=60000) # Increased timeout
            self._check_shutdown() 
            logger.info("Page loaded, waiting for network to be idle...")
            self.page.wait_for_load_state("networkidle", timeout=60000) # Increased timeout
            self._check_shutdown() 
            logger.info("Network idle state reached")
            
            title = self.page.title()
            logger.info(f"Page title: '{title}'")
            if not any(keyword in title for keyword in ["E-Status", "ARB", "Appeals"]):
                logger.warning(f"Page title '{title}' may not be correct; expected 'ARB', 'E-Status', or 'Appeals'.")
            else:
                logger.info("Successfully navigated to ARB website!")
                
        except GracefulShutdownException: 
            raise
        except Exception as e:
            logger.error(f"Error during navigation: {e}")
            try:
                content = self.page.content()
                logger.info(f"Page content length: {len(content)} characters. Preview: {content[:200]}...")
            except: # pylint: disable=bare-except
                logger.warning("Could not retrieve page content during navigation error handling.")
            # self.close() # Avoid calling close here if it's part of a larger operation that has its own finally block
            raise
    
    def enter_roll_number(self, roll_number: str) -> None:
        """
        Enter a roll number into the website's multiple input fields.
        """
        self._check_shutdown()
        if not self.page:
            if self.shutdown_signal and self.shutdown_signal.is_set():
                 raise GracefulShutdownException("Shutdown before page initialization for entering roll number.")
            raise RuntimeError("Browser not started. Call start_browser() first.")
        
        digits_only = re.sub(r'\\D', '', roll_number)
        if len(digits_only) != 19:
            logger.warning(f"Roll number '{roll_number}' (parsed as '{digits_only}') does not have 19 digits. Got {len(digits_only)}. Adjusting...")
            digits_only = digits_only.ljust(19, '0')[:19] # Pad or truncate to 19 digits
        
        try:
            self.page.wait_for_selector('#MainContent_txtRollNo1', state='visible', timeout=10000)
            segments = [digits_only[0:2], digits_only[2:4], digits_only[4:7], 
                        digits_only[7:10], digits_only[10:15], digits_only[15:19]]
            selectors = ['#MainContent_txtRollNo1', '#MainContent_txtRollNo2', '#MainContent_txtRollNo3',
                         '#MainContent_txtRollNo4', '#MainContent_txtRollNo5', '#MainContent_txtRollNo6']
            
            for i, sel in enumerate(selectors):
                self._check_shutdown() # Check before each fill operation
                self.page.fill(sel, segments[i])
            
            logger.info(f"Successfully entered roll number: {roll_number}")
        except GracefulShutdownException:
            raise
        except Exception as e:
            logger.error(f"Error entering roll number {roll_number}: {e}")
            raise # Re-raise to be handled by the caller
    
    def submit_search(self) -> bool: # Renamed from click_search_button if that was the intent
        """
        Submit the roll number search form.
        """
        self._check_shutdown()
        if not self.page:
            raise RuntimeError("Browser not started. Call start_browser() first.")
        
        try:
            self.page.wait_for_selector('#MainContent_btnSubmit', state='visible', timeout=10000)
            self.page.click('#MainContent_btnSubmit')
            logger.info("Successfully submitted search")
            self.page.wait_for_load_state("networkidle", timeout=30000) # Wait for results/error
            self._check_shutdown()

            # It's better to check for specific result indicators or error messages
            # than to assume success based on no immediate JS error.
            # The "No records found" check is in process_roll_numbers.
            return True 
        except GracefulShutdownException:
            raise
        except Exception as e:
            logger.error(f"Error submitting search: {e}")
            # raise # Re-raise to allow process_roll_numbers to handle it
            return False # Or return False if that's the expected behavior for this method

    def save_html_content(self, file_path: str) -> None:
        """
        Save the current page's HTML content to a file.
        """
        self._check_shutdown()
        if not self.page:
            raise RuntimeError("Browser not started. Call start_browser() first.")
        try:
            html_content = self.page.content()
            self._check_shutdown()
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"HTML content saved to {file_path}")
        except GracefulShutdownException:
            raise
        except Exception as e:
            logger.error(f"Error saving HTML content to {file_path}: {e}")
            # Do not raise here if this is an auxiliary function and failure is not critical for the main flow
    
    def extract_data_to_json(self, roll_number: str) -> Dict[str, Any]: # Renamed from extract_appeals_data
        """
        Extract data from the current page and return it as a dictionary.
        """
        self._check_shutdown()
        if not self.page:
            raise RuntimeError("Browser not started. Call start_browser() first.")
        
        data: Dict[str, Any] = {
            "roll_number": roll_number,
            "extracted_timestamp": datetime.datetime.now().isoformat(),
            "page_title": "", "property_info": {}, "appeal_info": [], "raw_tables": []
        }
        
        try:
            data["page_title"] = self.page.title()
            self._check_shutdown()

            # Example: Extract property address (adjust selectors as per actual page structure)
            # This part is highly dependent on the website's structure.
            # The selectors used in the original file might need review.
            # For instance:
            # property_address_loc = self.page.locator('td:has-text("Property Address:") + td').first
            # if property_address_loc.is_visible(timeout=500): # Check visibility
            #    data["property_info"]["address"] = property_address_loc.text_content().strip()
            
            # Placeholder for actual data extraction logic
            logger.info(f"Extracting data for {roll_number} (actual extraction logic needs to be robust)...")
            # This is where you'd populate data["property_info"], data["appeal_info"], data["raw_tables"]
            # For now, it returns a partially filled structure.

            return data
        except GracefulShutdownException:
            raise
        except Exception as e:
            logger.error(f"Error extracting data to JSON for {roll_number}: {e}")
            return data # Return partially filled data or an error structure

    def save_json_data(self, data: Dict[str, Any], file_path: str) -> None:
        """
        Save the extracted data to a JSON file.
        """
        self._check_shutdown() # Good for consistency, though local I/O is usually fast
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True) # Ensure directory exists
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"JSON data saved to {file_path}")
        except GracefulShutdownException: # Should not happen here unless shutdown is extremely fast
            raise
        except Exception as e:
            logger.error(f"Error saving JSON data to {file_path}: {e}")

    def process_roll_numbers(self, roll_numbers: List[str], results_base_dir: str) -> None:
        """
        Process a list of roll numbers: enter each, extract data, and save.
        """
        if not self.page:
            logger.error("Page not initialized. Cannot process roll numbers.")
            if self.shutdown_signal and self.shutdown_signal.is_set():
                 raise GracefulShutdownException("Shutdown before page initialization for processing roll numbers.")
            raise RuntimeError("Browser not started or page not initialized.")

        total_roll_numbers = len(roll_numbers)
        logger.info(f"Starting to process {total_roll_numbers} roll numbers.")

        for i, roll_number in enumerate(roll_numbers):
            self._check_shutdown() 
            
            logger.info(f"Processing roll number {i+1}/{total_roll_numbers}: {roll_number}")
            safe_roll_number_dir = re.sub(r'[^a-zA-Z0-9_\\-]', '_', roll_number)
            roll_number_results_dir = os.path.join(results_base_dir, safe_roll_number_dir)
            os.makedirs(roll_number_results_dir, exist_ok=True)
            
            try:
                # It's often good to navigate to a clean state (e.g., search page) before each item
                # self.navigate_to_site() # Or a more specific "go to search form" action
                # self._check_shutdown()

                self.enter_roll_number(roll_number)
                self._check_shutdown() 

                if not self.submit_search(): # Corrected method name and check return
                    logger.warning(f"Search submission failed or indicated an error for {roll_number}. Skipping.")
                    # Optionally save an error note here
                    self.navigate_to_site() # Try to reset for next roll number
                    continue 
                self._check_shutdown() 

                # Wait for results to load or error message
                # Using a general selector that appears on result/error pages
                self.page.wait_for_selector("#MainContent_lblErr, #some_results_table_id", timeout=30000) 
                self._check_shutdown() 

                error_message_element = self.page.query_selector("#MainContent_lblErr")
                if error_message_element and error_message_element.is_visible():
                    error_message = error_message_element.text_content()
                    if error_message and "No records found" in error_message: # Make this check more robust
                        logger.info(f"No records found for roll number: {roll_number}")
                        no_records_file = os.path.join(roll_number_results_dir, "no_records_found.txt")
                        with open(no_records_file, 'w', encoding='utf-8') as f:
                            f.write(f"No records found for roll number: {roll_number} at {datetime.datetime.now()}")
                        self.navigate_to_site() # Reset for next
                        continue
                
                self._check_shutdown() 
                # Corrected method name and variable name
                extracted_data = self.extract_data_to_json(roll_number) 
                self._check_shutdown() 
                
                data_file = os.path.join(roll_number_results_dir, "extracted_data.json") # Generic name
                self.save_json_data(extracted_data, data_file) # Use the new save method
                logger.info(f"Saved extracted data for {roll_number} to {data_file}")

                # The method extract_all_appeal_details was not found.
                # If this step is necessary, the method needs to be implemented.
                # logger.info("Skipping extract_all_appeal_details as it's not implemented.")
                # self._check_shutdown() 
                # all_details = self.extract_all_appeal_details(extracted_data, roll_number_results_dir)
                # self._check_shutdown() 
                # all_details_file = os.path.join(roll_number_results_dir, "all_appeal_details.json")
                # self.save_json_data(all_details, all_details_file)
                # logger.info(f"Saved all appeal details for {roll_number} to {all_details_file}")

                logger.info(f"Successfully processed {roll_number}. Navigating back/resetting for next one.")
                self.navigate_to_site() # Reset state for the next roll number
            
            except GracefulShutdownException: 
                logger.warning(f"Graceful shutdown triggered during processing of roll number: {roll_number}")
                raise 
            except Exception as e:
                logger.error(f"Error processing roll number {roll_number}: {e}", exc_info=True)
                error_file = os.path.join(roll_number_results_dir, "error_log.txt")
                with open(error_file, 'w', encoding='utf-8') as f:
                    f.write(f"Error processing {roll_number} at {datetime.datetime.now()}:\\n{str(e)}\\nTraceback: {traceback.format_exc()}")
                try:
                    logger.info("Attempting to recover by navigating to the main site...")
                    self.navigate_to_site()
                except Exception as nav_e:
                    logger.error(f"Failed to recover by navigating to main site: {nav_e}")
                    # If recovery fails, re-raise the original error to stop processing if critical
                    # or break the loop if individual errors should not stop the batch.
                    # For now, we let it continue to the next roll number if possible.
            finally:
                # Final check in loop iteration, though _check_shutdown should handle most cases
                if self.shutdown_signal and self.shutdown_signal.is_set():
                    logger.info(f"Shutdown signal confirmed in finally block for roll number {roll_number}.")
                    # Do not raise here; let the main _check_shutdown at loop start or within methods handle it.
        
        logger.info("Finished processing all roll numbers.")
    
    def take_screenshot(self, file_path: str) -> None:
        """
        Take a screenshot of the current page state.
        """
        self._check_shutdown()
        if not self.page:
            raise RuntimeError("Browser not started. Call start_browser() first.")
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True) # Ensure directory exists
            self.page.screenshot(path=file_path)
            logger.info(f"Screenshot saved to {file_path}")
        except GracefulShutdownException:
            raise
        except Exception as e:
            logger.error(f"Error taking screenshot to {file_path}: {e}")

    def close(self) -> None:
        """
        Close the browser and release Playwright resources.
        This method should be safe to call multiple times or on partially initialized components.
        """
        # No _check_shutdown() here to avoid recursion if called from _check_shutdown itself.
        # Also, this is the cleanup method, so it should try to run as much as possible.
        logger.info("Attempting to close Playwright resources...")
        
        # Page
        if self.page:
            try:
                self.page.close()
                logger.info("Page closed.")
            except Exception as e:
                logger.warning(f"Error closing page: {e} (Page might already be closed or invalid)")
            finally:
                self.page = None # Ensure it's None even if close fails
        
        # Context
        if self.context:
            try:
                self.context.close()
                logger.info("Browser context closed.")
            except Exception as e:
                logger.warning(f"Error closing context: {e} (Context might already be closed or invalid)")
            finally:
                self.context = None
            
        # Browser
        if self.browser:
            try:
                self.browser.close()
                logger.info("Browser closed.")
            except Exception as e:
                logger.warning(f"Error closing browser: {e} (Browser might already be closed or invalid)")
            finally:
                self.browser = None
            
        # Playwright
        if self.playwright:
            try:
                self.playwright.stop() # For sync_playwright, stop() is called on the object returned by sync_playwright()
                logger.info("Playwright stopped.")
            except Exception as e:
                logger.warning(f"Error stopping Playwright: {e}")
            finally:
                self.playwright = None
        logger.info("Playwright resources cleanup attempt finished.")

# Example usage (for testing purposes, typically called from api.py)
# if __name__ == '__main__':
#     import traceback # Added for process_roll_numbers error logging
#     # Setup a dummy shutdown signal for testing
#     test_shutdown_signal = threading.Event()
#     # Example: test_shutdown_signal.set() # To test shutdown
    
#     # Create an instance of the automation class
#     # Pass the dummy signal for testing
#     automation = PlaywrightAutomation(headless=False, shutdown_signal=test_shutdown_signal)
#     try:
#         automation.start_browser()
#         automation.navigate_to_site()
        
#         # Test with a sample roll number
#         sample_roll_numbers = ["1908072215005000000"] # Use a valid format
#         results_dir = "../../data/test_results" # Adjust path as needed
#         os.makedirs(results_dir, exist_ok=True)
        
#         automation.process_roll_numbers(sample_roll_numbers, results_dir)
        
#         # Example of taking a screenshot
#         # automation.take_screenshot(os.path.join(results_dir, "final_page.png"))
        
#     except GracefulShutdownException:
#         logger.info("Main test script caught GracefulShutdownException.")
#     except Exception as e:
#         logger.error(f"An error occurred during the test run: {e}", exc_info=True)
#     finally:
#         logger.info("Closing browser in main test script finally block.")
#         automation.close()
#     logger.info("Test run finished.")