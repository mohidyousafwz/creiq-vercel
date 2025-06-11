#!/usr/bin/env python
"""
Test runner script for PlaywrightAutomation tests
"""
import os
import sys
import subprocess

def main():
    """Run the test suite with proper environment setup"""
    # Ensure we're in the project root
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)
    
    # Create necessary directories
    os.makedirs('tests', exist_ok=True)
    os.makedirs('src/creiq', exist_ok=True)
    
    # Create a test .env file if it doesn't exist
    test_env_path = os.path.join(project_root, '.env.test')
    if not os.path.exists(test_env_path):
        with open(test_env_path, 'w') as f:
            f.write('URL=https://test.arb.website.com\n')
        print(f"Created test environment file: {test_env_path}")
    
    # Set environment to use test env file
    os.environ['DOTENV_PATH'] = test_env_path
    
    # Install test dependencies
    print("Installing test dependencies...")
    subprocess.run([
        sys.executable, '-m', 'pip', 'install', '-r', 'tests/requirements-test.txt'
    ], check=True)
    
    # Run pytest with coverage
    print("\nRunning tests...")
    result = subprocess.run([
        sys.executable, '-m', 'pytest',
        'tests/test_playwright_automation.py',
        '-v',
        '--tb=short'
    ])
    
    return result.returncode

if __name__ == '__main__':
    sys.exit(main()) 