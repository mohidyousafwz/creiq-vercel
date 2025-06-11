#!/usr/bin/env python3
"""Test script to upload a CSV file to the API."""
import requests
import sys
from pathlib import Path

def test_upload(file_path: str):
    """Test uploading a CSV file to the API."""
    url = "http://localhost:8000/upload"
    
    # Check if file exists
    if not Path(file_path).exists():
        print(f"Error: File {file_path} not found")
        return
    
    try:
        # Open and upload the file
        with open(file_path, 'rb') as f:
            files = {'file': (Path(file_path).name, f, 'text/csv')}
            response = requests.post(url, files=files)
        
        # Print response
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # If successful, get task status
        if response.status_code == 200:
            data = response.json()
            task_id = data.get('task_id')
            if task_id:
                print(f"\nTask ID: {task_id}")
                print(f"Check status at: http://localhost:8000/tasks/{task_id}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    file_path = sys.argv[1] if len(sys.argv) > 1 else "data/sample_upload_files/minimum_roll-number.csv"
    test_upload(file_path) 