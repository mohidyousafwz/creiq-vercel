#!/usr/bin/env python3
"""
Test script to verify the data extraction works correctly by simulating the upload process.
"""

import os
import sys
import threading
from datetime import datetime

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.creiq.api import start_processing

def test_extraction(roll_number="38-29-300-012-10400-0000"):
    """
    Test the extraction for a single roll number by simulating the upload process.
    """
    print(f"Testing extraction for roll number: {roll_number}")
    
    # Create test output directory with timestamp and roll number
    timestamp = datetime.now().strftime("%I_%M%p")  # Format: 01_19PM
    folder_name = f"{timestamp}-{roll_number}"
    test_dir = os.path.join("data", "test_extraction", folder_name)
    os.makedirs(test_dir, exist_ok=True)
    
    print(f"Creating output directory: {test_dir}")
    
    # Create a dummy shutdown signal (not set) for testing
    shutdown_signal = threading.Event()
    
    # Simulate the upload process by calling start_processing directly
    # This mimics what happens when a CSV is uploaded through the API
    roll_numbers = [roll_number]
    
    try:
        print(f"Starting processing for {len(roll_numbers)} roll number(s)...")
        start_processing(roll_numbers, test_dir, shutdown_signal)
        print("\nExtraction test completed successfully!")
        print(f"Results saved in: {test_dir}")
    except Exception as e:
        print(f"Error during extraction test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Allow passing a custom roll number as command line argument
    if len(sys.argv) > 1:
        test_extraction(sys.argv[1])
    else:
        test_extraction() 