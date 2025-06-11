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

# Fix for Windows asyncio issues
import sys
import asyncio
if sys.platform == 'win32':
    # Set Windows ProactorEventLoop to prevent NotImplementedError
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

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
    
    def __init__(self, headless: bool = False, shutdown_signal: Optional[threading.Event] = None):
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
        self.shutdown_signal = shutdown_signal
    
    def _check_shutdown(self):
        """Checks if shutdown is signaled and raises exception if it is."""
        if self.shutdown_signal and self.shutdown_signal.is_set():
            logger.info("Shutdown signal received, initiating graceful shutdown of Playwright.")
            raise GracefulShutdownException("Playwright automation shutting down gracefully.")
    
    def start_browser(self):
        """Start the browser and create a new page."""
        self._check_shutdown()
        
        try:
            logger.info("Starting Playwright...")
            self.playwright = sync_playwright().start()
            
            logger.info("Launching browser...")
            launch_args = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--ignore-certificate-errors',
                '--ignore-ssl-errors'
            ]
            
            try:
                self.browser = self.playwright.chromium.launch(
                    headless=self.headless,
                    args=launch_args,
                    timeout=60000  # 60 second timeout
                )
                logger.info("Browser launched successfully")
            except Exception as browser_error:
                logger.error(f"Failed to launch Chromium: {browser_error}")
                # Try Firefox as fallback
                logger.info("Attempting to launch Firefox as fallback...")
                try:
                    self.browser = self.playwright.firefox.launch(
                        headless=self.headless,
                        timeout=60000
                    )
                    logger.info("Firefox launched successfully")
                except Exception as firefox_error:
                    logger.error(f"Failed to launch Firefox: {firefox_error}")
                    # Try WebKit as last resort
                    logger.info("Attempting to launch WebKit as last resort...")
                    try:
                        self.browser = self.playwright.webkit.launch(
                            headless=self.headless,
                            timeout=60000
                        )
                        logger.info("WebKit launched successfully")
                    except Exception as webkit_error:
                        logger.error(f"Failed to launch WebKit: {webkit_error}")
                        raise RuntimeError("Failed to launch any browser. Please ensure browsers are installed with 'playwright install'")
            
            logger.info("Creating browser context...")
            self.context = self.browser.new_context(
                viewport={"width": 1600, "height": 900},
                ignore_https_errors=True
            )
            
            logger.info("Creating new page...")
            self.page = self.context.new_page()
            logger.info("Browser started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.close()
            raise
    
    def navigate_to_site(self):
        """Navigate to the ARB website."""
        self._check_shutdown()
        
        if not self.page:
            raise RuntimeError("Browser not started. Call start_browser() first.")
        
        try:
            self.page.goto(self.base_url)
            logger.info(f"Navigated to {self.base_url}")
        except Exception as e:
            logger.error(f"Failed to navigate to site: {e}")
            raise
    
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
            # Preserve the original roll number format for directory naming
            safe_roll_number_dir = roll_number.replace('/', '_').replace('\\', '_').replace(':', '_')
            roll_number_results_dir = os.path.join(results_base_dir, safe_roll_number_dir)
            os.makedirs(roll_number_results_dir, exist_ok=True)
            
            try:
                # Process each roll number with frequent shutdown checks
                self._process_single_roll_number(roll_number, roll_number_results_dir)
                
                # Check shutdown after each roll number
                self._check_shutdown()
                
            except GracefulShutdownException:
                logger.info(f"Shutdown requested while processing roll number {roll_number}")
                raise
            except Exception as e:
                logger.error(f"Error processing roll number {roll_number}: {e}")
                # Continue with next roll number
                continue
        
        logger.info("Finished processing all roll numbers.")
    
    def _process_single_roll_number(self, roll_number: str, results_dir: str):
        """Process a single roll number with frequent shutdown checks."""
        self._check_shutdown()
        
        # Enter roll number
        self.enter_roll_number(roll_number)
        self._check_shutdown()
        
        # Submit the search
        if not self.submit_search():
            logger.error(f"Failed to submit search for roll number {roll_number}")
            return
        self._check_shutdown()
        
        # Extract data from the page
        data = self.extract_data_to_json(roll_number)
        self._check_shutdown()
        
        # Save HTML content
        html_path = os.path.join(results_dir, "appeal_summary.html")
        self.save_html_content(html_path)
        self._check_shutdown()
        
        # Save JSON data
        json_path = os.path.join(results_dir, "appeal_summary.json")
        self.save_json_data(data, json_path)
        self._check_shutdown()
        
        # Extract detailed appeal information if appeals exist
        if data.get("appeal_info"):
            detailed_data = self.extract_all_appeal_details(data, results_dir)
            detailed_json_path = os.path.join(results_dir, "appeal_details.json")
            self.save_json_data(detailed_data, detailed_json_path)
            self._check_shutdown()
    
    def close(self):
        """Close the browser and cleanup resources."""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            logger.info("Browser closed successfully")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
        finally:
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None

    def enter_roll_number(self, roll_number: str) -> None:
        """
        Enter a roll number into the website's multiple input fields.
        """
        self._check_shutdown()
        if not self.page:
            if self.shutdown_signal and self.shutdown_signal.is_set():
                 raise GracefulShutdownException("Shutdown before page initialization for entering roll number.")
            raise RuntimeError("Browser not started. Call start_browser() first.")
        
        # Remove all non-digit characters (including dashes)
        digits_only = re.sub(r'\D', '', roll_number)
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
    
    def extract_data_to_json(self, roll_number: str) -> Dict[str, Any]:
        """
        Extract data from the current page and return it as a dictionary.
        """
        self._check_shutdown()
        if not self.page:
            raise RuntimeError("Browser not started. Call start_browser() first.")
        
        data: Dict[str, Any] = {
            "roll_number": roll_number,
            "extracted_timestamp": datetime.datetime.now().isoformat(),
            "page_title": "", 
            "property_info": {},
            "appeal_info": []
        }
        
        try:
            data["page_title"] = self.page.title()
            self._check_shutdown()

            # Extract property description - look for the text after "Location & Property Description:"
            try:
                # Try multiple selectors to find the property description
                selectors = [
                    # Find the label div, then get its next sibling
                    'div.col-md-3:has(strong:has-text("Location & Property Description:")) + div.col-md-3',
                    # Alternative with has-text on the div itself
                    'div.col-md-3:has-text("Location & Property Description:") + div.col-md-3',
                    # Try with partial text match using strong tag
                    'div.col-md-3:has(strong:has-text("Location")) + div.col-md-3',
                    # Try xpath-based approach for sibling (fallback)
                    'xpath=//div[contains(@class, "col-md-3") and contains(., "Location") and contains(., "Property Description:")]/following-sibling::div[contains(@class, "col-md-3")]'
                ]
                
                desc_element = None
                for selector in selectors:
                    try:
                        desc_element = self.page.query_selector(selector)
                        if desc_element:
                            # Make sure we're not getting the label itself
                            text = desc_element.text_content().strip()
                            if text and "Location" not in text and "Property Description" not in text:
                                data["property_info"]["description"] = text
                                logger.info(f"Found property description: {data['property_info']['description']}")
                                break
                    except:
                        continue
                        
                if not desc_element or not data["property_info"].get("description"):
                    logger.warning("Could not extract property description with any selector")
            except Exception as e:
                logger.warning(f"Could not extract property description: {e}")
            
            # Extract appeal information from the main table
            try:
                # Look for the main appeals table
                table = self.page.query_selector('#MainContent_GridView1')
                if table:
                    # Get all rows except header
                    rows = table.query_selector_all('tr')[1:]  # Skip header row
                    logger.info(f"Found {len(rows)} appeal rows in the table")
                    
                    for row in rows:
                        try:
                            cells = row.query_selector_all('td')
                            if len(cells) >= 9:  # Ensure we have all expected columns
                                appeal_dict = {
                                    "appealnumber": "",
                                    "appellant": "",
                                    "representative": "",
                                    "section": "",
                                    "tax_date": "",
                                    "hearing_number": "",
                                    "hearing_date": "",
                                    "status": "",
                                    "board_order_number": ""
                                }
                                
                                # Extract appeal number from link
                                appeal_link = cells[0].query_selector('a')
                                if appeal_link:
                                    appeal_dict["appealnumber"] = appeal_link.text_content().strip()
                                
                                # Extract other fields
                                appeal_dict["appellant"] = cells[1].text_content().strip()
                                appeal_dict["representative"] = cells[2].text_content().strip()
                                appeal_dict["section"] = cells[3].text_content().strip()
                                appeal_dict["tax_date"] = cells[4].text_content().strip()
                                
                                # Hearing number might be in a link or just text
                                hearing_link = cells[5].query_selector('a')
                                if hearing_link:
                                    appeal_dict["hearing_number"] = hearing_link.text_content().strip()
                                else:
                                    appeal_dict["hearing_number"] = cells[5].text_content().strip()
                                
                                appeal_dict["hearing_date"] = cells[6].text_content().strip()
                                appeal_dict["status"] = cells[7].text_content().strip()
                                appeal_dict["board_order_number"] = cells[8].text_content().strip()
                                
                                # Clean up empty fields (replace &nbsp; or empty strings)
                                for key in appeal_dict:
                                    if appeal_dict[key] == '\u00a0' or appeal_dict[key] == ' ':
                                        appeal_dict[key] = ""
                                
                                data["appeal_info"].append(appeal_dict)
                                
                        except Exception as e:
                            logger.warning(f"Error processing appeal row: {e}")
                            continue
                
                else:
                    logger.warning("Could not find appeals table #MainContent_GridView1")
                    
            except Exception as e:
                logger.error(f"Error extracting appeal table data: {e}")
            
            logger.info(f"Extracted {len(data['appeal_info'])} appeals from the page")
            
            return data
            
        except GracefulShutdownException:
            raise
        except Exception as e:
            logger.error(f"Error extracting data to JSON for {roll_number}: {e}")
            return data # Return partially filled data

    def extract_all_appeal_details(self, appeals_data: Dict[str, Any], output_dir: str) -> Dict[str, Any]:
        """
        Extract detailed information for each appeal by navigating to individual appeal pages.
        """
        all_appeals_details = {
            "roll_number": appeals_data.get("roll_number", ""),
            "extracted_timestamp": appeals_data.get("extracted_timestamp", datetime.datetime.now().isoformat()),
            "page_title": appeals_data.get("page_title", ""),
            "property_info": appeals_data.get("property_info", {}),
            "appeals": []
        }
        
        if not self.page:
            logger.error("Page not initialized for extracting appeal details")
            return all_appeals_details
        
        # Process each appeal from the appeals_data
        appeals = appeals_data.get("appeal_info", [])
        logger.info(f"Processing {len(appeals)} appeals for detailed extraction")
        
        for idx, appeal in enumerate(appeals):
            self._check_shutdown()
            
            try:
                appeal_number = appeal.get("appealnumber", "")
                if not appeal_number:
                    logger.warning(f"No appeal number found for appeal {idx}")
                    continue
                    
                logger.info(f"Processing appeal {idx+1}/{len(appeals)}: {appeal_number}")
                
                # Click on the appeal link to navigate to detail page
                try:
                    # Use the specific appeal link format
                    appeal_link_selector = f'a[href*="ComplaintDetail.aspx?AppealNo={appeal_number}"]'
                    self.page.click(appeal_link_selector)
                    self._check_shutdown()
                    
                    # Wait for the detail page to load
                    self.page.wait_for_load_state("networkidle", timeout=20000)
                    
                except Exception as e:
                    logger.error(f"Could not navigate to appeal {appeal_number}: {e}")
                    continue
                
                # Extract detailed appeal information
                appeal_detail = {
                    "appeal_number": appeal_number,
                    "extracted_timestamp": datetime.datetime.now().isoformat(),
                    "property_info": {},
                    "appellant_info": {},
                    "status_info": {},
                    "decision_info": {}
                }
                
                # Extract property information using the specific row structure
                property_mappings = [
                    ('roll_number', 'Property Roll Number:'),
                    ('municipality', 'Municipality:'),
                    ('classification', 'Property Classification:'),
                    ('nbhd', 'NBHD:')
                ]
                
                # Handle description separately due to HTML entity issues
                for field_name, label_text in property_mappings:
                    try:
                        # Look for the row containing the label, then get the value from the next column
                        selector = f'div.row:has(div:has-text("{label_text}")) div.col-md-4:nth-child(2)'
                        element = self.page.query_selector(selector)
                        if element:
                            value = element.text_content().strip()
                            # For roll number, extract from link if present
                            if field_name == 'roll_number':
                                link = element.query_selector('a')
                                if link:
                                    value = link.text_content().strip()
                            appeal_detail["property_info"][field_name] = value
                    except Exception as e:
                        logger.debug(f"Could not extract {field_name}: {e}")
                
                # Extract property description with special handling
                try:
                    desc_selectors = [
                        # Find the label div, then get its next sibling (for col-md-4 structure on detail pages)
                        'div.col-md-4:has(strong:has-text("Location & Property Description:")) + div.col-md-4',
                        'div.col-md-4:has-text("Location & Property Description:") + div.col-md-4',
                        'div.col-md-4:has(strong:has-text("Location")) + div.col-md-4',
                        # Fallback to row-based selectors if the sibling approach doesn't work
                        'div.row:has(div:has-text("Location & Property Description:")) div.col-md-4:last-child',
                        'div.row:has(div:has-text("Location") :has-text("Property Description:")) div.col-md-4:last-child'
                    ]
                    
                    for selector in desc_selectors:
                        try:
                            desc_element = self.page.query_selector(selector)
                            if desc_element:
                                text = desc_element.text_content().strip()
                                if text and "Location" not in text and "Property Description" not in text:
                                    appeal_detail["property_info"]["description"] = text
                                    break
                        except:
                            continue
                except Exception as e:
                    logger.debug(f"Could not extract property description: {e}")
                
                # Extract appellant information
                appellant_mappings = [
                    ('name1', 'Name1:'),
                    ('name2', 'Name2:'),
                    ('representative', 'Name of Representative:'),
                    ('filing_date', 'Filing Date:'),
                    ('tax_date', 'Tax Date:'),
                    ('section', 'Section:'),
                    ('reason_for_appeal', 'Reason for Appeal:')
                ]
                
                for field_name, label_text in appellant_mappings:
                    try:
                        selector = f'div.row:has(div:has-text("{label_text}")) div.col-md-4:nth-child(2)'
                        element = self.page.query_selector(selector)
                        if element:
                            value = element.text_content().strip()
                            # Clean up line breaks in reason for appeal
                            if field_name == 'reason_for_appeal':
                                value = value.replace('\n', '')
                            appeal_detail["appellant_info"][field_name] = value
                    except Exception as e:
                        logger.debug(f"Could not extract {field_name}: {e}")
                
                # Extract status information
                try:
                    status_selector = 'div.row:has(div:has-text("Status:")) div.col-md-4:nth-child(2)'
                    status_element = self.page.query_selector(status_selector)
                    if status_element:
                        appeal_detail["status_info"]["status"] = status_element.text_content().strip()
                except Exception as e:
                    logger.debug(f"Could not extract status: {e}")
                
                # Extract decision information
                decision_mappings = [
                    ('decision_number', 'Decision Number:'),
                    ('mailing_date', 'Decision Mailing Date:'),
                    ('decisions', 'Decision(s):'),
                    ('decision_details', 'DecisionDetails:')
                ]
                
                for field_name, label_text in decision_mappings:
                    try:
                        selector = f'div.row:has(div:has-text("{label_text}")) div.col-md-4:nth-child(2)'
                        element = self.page.query_selector(selector)
                        if element:
                            value = element.text_content().strip()
                            # Clean up line breaks in decisions and decision_details
                            if field_name in ['decisions', 'decision_details']:
                                value = value.replace('\n', '')
                            appeal_detail["decision_info"][field_name] = value
                    except Exception as e:
                        logger.debug(f"Could not extract {field_name}: {e}")
                
                # Take a screenshot of the detail page if needed
                try:
                    screenshot_path = os.path.join(output_dir, f"appeal_{appeal_number}_detail.png")
                    self.take_screenshot(screenshot_path)
                except:
                    pass
                
                all_appeals_details["appeals"].append(appeal_detail)
                
                # Navigate back to the appeals list
                try:
                    self.page.go_back()
                    self.page.wait_for_load_state("networkidle", timeout=10000)
                except Exception as e:
                    logger.warning(f"Error navigating back from appeal {appeal_number}: {e}")
                    # Try to navigate to the main page again
                    self.navigate_to_site()
                
            except Exception as e:
                logger.error(f"Error processing appeal {appeal_number}: {e}")
                # Try to recover
                try:
                    self.navigate_to_site()
                except:
                    pass
        
        logger.info(f"Extracted details for {len(all_appeals_details['appeals'])} appeals")
        return all_appeals_details

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

    def is_browser_alive(self) -> bool:
        """
        Check if the browser is still alive and responsive.
        """
        try:
            if not self.page:
                return False
            # Try to get the title - if this fails, browser is dead
            _ = self.page.title()
            return True
        except:
            return False
    
    def restart_browser(self) -> None:
        """
        Restart the browser if it has crashed.
        """
        logger.info("Restarting browser...")
        self.close()  # Clean up any existing resources
        time.sleep(2)  # Brief pause
        self.start_browser()
        self.navigate_to_site()
        logger.info("Browser restarted successfully")
    
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