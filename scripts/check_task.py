#!/usr/bin/env python3
"""Check task status."""
import requests
import json
import sys

def check_task(task_id: str):
    """Check the status of a task."""
    url = f"http://localhost:8000/tasks/{task_id}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            print(json.dumps(data, indent=2))
        else:
            print(f"Error: Status code {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_task(sys.argv[1])
    else:
        # Check the latest task
        check_task("553bc24f-76d4-4250-906d-2f0744145963") 