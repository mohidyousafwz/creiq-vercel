"""
Application settings and configuration.
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
TEST_EXTRACTION_DIR = DATA_DIR / "test_extraction"
SAMPLE_DATA_DIR = DATA_DIR / "sample_upload_files"

# Optional: Output Settings - Load early to use in directory creation
RESULTS_DIR = Path(os.getenv("RESULTS_DIR", str(DATA_DIR / "results")))
SAVE_HTML = os.getenv("SAVE_HTML", "true").lower() == "true"
SAVE_SCREENSHOTS = os.getenv("SAVE_SCREENSHOTS", "false").lower() == "true"

# Ensure directories exist
for dir_path in [DATA_DIR, RESULTS_DIR, TEST_EXTRACTION_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# ARB Website Configuration
ARB_URL = os.getenv("URL", "")
if not ARB_URL:
    raise ValueError("URL not found in environment variables. Please set it in .env file.")

# Browser Configuration
BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "true").lower() == "true"
BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "60000"))
BROWSER_SLOW_MO = int(os.getenv("BROWSER_SLOW_MO", "0"))

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_RELOAD = os.getenv("API_RELOAD", "true").lower() == "true"

# Processing Configuration
MAX_CONCURRENT_EXTRACTIONS = int(os.getenv("MAX_CONCURRENT_EXTRACTIONS", "1"))
EXTRACTION_TIMEOUT = int(os.getenv("EXTRACTION_TIMEOUT", "300"))  # seconds

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Database Configuration (for future use)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./creiq.db")

# Authentication Configuration (for future use)
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Dashboard Authentication
PASSCODE = os.getenv("PASSCODE", "1234")  # Default passcode for development
SESSION_DURATION_DAYS = 90  # 3 months

# Optional: Processing Settings
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3").split('#')[0].strip())
RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5").split('#')[0].strip()) 