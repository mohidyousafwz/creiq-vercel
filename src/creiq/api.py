from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
import csv
import io
import os
from .roll_number_reader import RollNumberReader
from .playwright_automation import PlaywrightAutomation  # Make sure GracefulShutdownException is importable or defined here/in playwright_automation
from fastapi.staticfiles import StaticFiles
import logging
import threading  # Added import
from typing import List

app = FastAPI(title="CREIQ Roll Number API")

# Determine project root and default CSV path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DEFAULT_CSV_PATH = os.path.join(PROJECT_ROOT, 'data', 'roll-number.csv')

# Serve static files under '/static'
app.mount("/static", StaticFiles(directory=os.path.join(PROJECT_ROOT, 'static')), name='static')

@app.get("/", include_in_schema=False)
def serve_index():
    """Serve the main upload page"""
    return FileResponse(os.path.join(PROJECT_ROOT, 'static', 'index.html'))

logger = logging.getLogger("uvicorn.error")

# --- Added for graceful shutdown ---
shutdown_signal = threading.Event()

# Try to import GracefulShutdownException from playwright_automation, or define it if not available
# This is important for the except block in start_processing
try:
    from .playwright_automation import GracefulShutdownException
except ImportError:
    class GracefulShutdownException(Exception):  # Define fallback if not in playwright_automation
        pass
# --- End of graceful shutdown additions ---


@app.on_event("startup")
async def startup_event():
    shutdown_signal.clear()
    logger.info("Application startup: shutdown signal cleared.")

@app.on_event("shutdown")
async def shutdown_event_handler():  # Renamed to avoid conflict with the new shutdown_signal variable
    logger.info("Application shutdown: setting shutdown signal for background tasks.")
    shutdown_signal.set()
    import asyncio # Import asyncio here
    await asyncio.sleep(0.1) # Add a small delay (e.g., 100ms)
    logger.info("Shutdown signal set and a brief pause completed. Uvicorn will now wait for tasks to complete.")


def start_processing(roll_numbers: list, results_dir: str, signal_event: threading.Event):
    logger.info(f"Found {len(roll_numbers)} roll numbers to process (background)")
    logger.info("Starting browser automation (background)...")
    
    # Check if we should run in debug mode (non-headless)
    debug_mode = os.getenv('BROWSER_DEBUG', 'false').lower() == 'true'
    headless = not debug_mode
    
    if debug_mode:
        logger.info("Running browser in DEBUG mode (non-headless)")
    
    # Pass the signal_event to PlaywrightAutomation constructor
    automation = PlaywrightAutomation(headless=headless, shutdown_signal=signal_event)
    try:
        automation.start_browser()
        if signal_event.is_set():  # Check signal after starting browser
            logger.info("Shutdown signaled after starting browser, before navigation.")
            return  # Exit early
        automation.navigate_to_site()
        if signal_event.is_set():  # Check signal after navigation
            logger.info("Shutdown signaled after navigation, before processing roll numbers.")
            return  # Exit early
        automation.process_roll_numbers(roll_numbers, results_dir)  # This method needs to check the signal
    except GracefulShutdownException:  # Catch the custom exception
        logger.info("Playwright automation gracefully shut down due to server signal.")
    except Exception as e:
        logger.error(f"Error during background processing: {e}")
    finally:
        logger.info("Closing Playwright automation in finally block...")
        automation.close()  # Ensure close is always called
        logger.info(f"Background automation task finished. Results potentially in {results_dir}")

@app.post("/upload-roll-numbers")
async def upload_roll_numbers(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Upload a CSV file of roll numbers, save it, and return the parsed list.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    content = await file.read()
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Unable to decode file. Ensure it's UTF-8 encoded.")

    # Save uploaded file to default location
    os.makedirs(os.path.dirname(DEFAULT_CSV_PATH), exist_ok=True)
    with open(DEFAULT_CSV_PATH, 'wb') as f:
        f.write(content)

    # Use RollNumberReader to parse saved file
    reader = RollNumberReader(DEFAULT_CSV_PATH)
    try:
        roll_numbers = reader.get_roll_numbers()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing CSV: {e}")

    # Trigger background processing of roll numbers
    results_dir = os.path.join(PROJECT_ROOT, 'data', 'results')
    os.makedirs(results_dir, exist_ok=True)
    # Pass the global shutdown_signal to the background task
    background_tasks.add_task(start_processing, roll_numbers, results_dir, shutdown_signal)

    return JSONResponse(content={
        "count": len(roll_numbers),
        "roll_numbers": roll_numbers,  # Consider removing full list from response if large
        "processing": "started"
    })

@app.get("/roll-numbers")
def get_default_roll_numbers():
    """
    Return roll numbers from the default CSV file.
    """
    reader = RollNumberReader(DEFAULT_CSV_PATH)
    try:
        roll_numbers = reader.get_roll_numbers()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Default roll-number.csv not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading CSV: {e}")

    return JSONResponse(content={
        "count": len(roll_numbers),
        "roll_numbers": roll_numbers
    })

if __name__ == "__main__":
    import uvicorn  # type: ignore
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=True
    )
