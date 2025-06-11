#!/usr/bin/env python3
"""
Test runner for CREIQ application.
"""
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_tests():
    """Run all tests with coverage."""
    print("Running CREIQ tests with coverage...\n")
    
    # Run pytest with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/unit",
        "-v",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=html"
    ]
    
    result = subprocess.run(cmd, cwd=project_root)
    
    if result.returncode == 0:
        print("\n✅ All tests passed!")
        print("Coverage report generated in htmlcov/index.html")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    run_tests() 