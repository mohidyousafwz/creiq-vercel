#!/usr/bin/env python3
"""
Main module for CREIQ application.
"""

import os
import time
from src.creiq import RollNumberReader, PlaywrightAutomation


def main():
    """
    Main function to run the CREIQ application.
    """
    # Define the path to the roll number CSV file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file_path = os.path.join(current_dir, 'data', 'roll-number.csv')
    
    # Create base directories for storing data if they don't exist
    data_dir = os.path.join(current_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # Create the results directory for individual roll number data
    results_dir = os.path.join(data_dir, 'results')
    os.makedirs(results_dir, exist_ok=True)
    
    # Create an instance of RollNumberReader with the CSV file path
    reader = RollNumberReader(csv_file_path)
    
    # Get the roll numbers without printing them
    roll_numbers = reader.get_roll_numbers()
    
    print(f"Found {len(roll_numbers)} roll numbers to process")
    
    # Initialize Playwright automation (headless mode for production)
    print("Starting browser automation...")
    automation = PlaywrightAutomation(headless=True)  # Set to True for production
    
    try:
        # Start the browser
        automation.start_browser()
        
        # Navigate to the website
        print(f"Navigating to ARB website...")
        automation.navigate_to_site()
        
        # Process all roll numbers in one go - with screenshot and HTML saving disabled by default
        automation.process_roll_numbers(
            roll_numbers, 
            results_dir,
            save_screenshots=False,  # Set to False by default
            save_html=False          # Set to False by default
        )
        
    except Exception as e:
        print(f"An error occurred during automation: {e}")
    finally:
        # Always close the browser
        print("\nClosing browser...")
        automation.close()
        print("\nAutomation completed. Results saved in the 'data/results' directory.")


if __name__ == "__main__":
    main()