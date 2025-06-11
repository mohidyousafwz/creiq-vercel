"""
FastAPI application for CREIQ data extraction service.
"""
import sys
import asyncio

# Fix for Windows asyncio issues - must be done before any other asyncio operations
if sys.platform == 'win32':
    # Set Windows ProactorEventLoop to prevent NotImplementedError
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import os
import threading
from typing import List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from src.creiq.utils.roll_number_reader import read_roll_numbers_from_csv
from src.creiq.services.extraction_service import ExtractionService
from src.creiq.utils.logger import logger
from src.creiq.config.settings import API_HOST, API_PORT, API_RELOAD

# Create FastAPI app
app = FastAPI(
    title="CREIQ Data Extraction API",
    description="API for extracting appeal data from ARB website",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global shutdown signal
shutdown_signal = threading.Event()

# Background task tracking
active_tasks: Dict[str, Any] = {}
task_locks: Dict[str, threading.Lock] = {}


@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    logger.info("CREIQ API starting up...")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("CREIQ API shutting down...")
    shutdown_signal.set()
    
    # Wait for active tasks to complete or timeout
    for task_id, task_info in active_tasks.items():
        if task_info["status"] == "running":
            logger.info(f"Waiting for task {task_id} to complete...")
            try:
                # Wait up to 5 seconds for task to complete
                await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, 
                        lambda: task_locks[task_id].acquire(timeout=5)
                    ),
                    timeout=5
                )
                task_locks[task_id].release()
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"Task {task_id} did not complete gracefully: {e}")
                active_tasks[task_id].update({
                    "status": "cancelled",
                    "error": "Task cancelled during shutdown"
                })


@app.get("/")
async def root():
    """Root endpoint."""
    return FileResponse("static/index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "CREIQ API"
    }


@app.post("/upload")
async def upload_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload a CSV file containing roll numbers for processing.
    
    Args:
        file: CSV file with roll numbers
        
    Returns:
        Task information
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    try:
        # Read roll numbers from CSV
        roll_numbers = await read_roll_numbers_from_csv(file)
        
        if not roll_numbers:
            raise HTTPException(status_code=400, detail="No valid roll numbers found in CSV")
        
        # Create task ID
        import uuid
        task_id = str(uuid.uuid4())
        
        # Track task
        active_tasks[task_id] = {
            "id": task_id,
            "status": "processing",
            "roll_numbers": roll_numbers,
            "total": len(roll_numbers),
            "completed": 0
        }
        
        # Start processing in background
        background_tasks.add_task(
            process_roll_numbers_task,
            task_id,
            roll_numbers
        )
        
        return {
            "task_id": task_id,
            "message": f"Processing started for {len(roll_numbers)} roll numbers",
            "roll_numbers": roll_numbers
        }
        
    except Exception as e:
        logger.error(f"Error processing upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of a processing task."""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return active_tasks[task_id]


@app.get("/tasks")
async def list_tasks():
    """List all tasks."""
    return {"tasks": list(active_tasks.values())}


def process_roll_numbers_task(task_id: str, roll_numbers: List[str]):
    """
    Background task to process roll numbers.
    
    Args:
        task_id: Unique task identifier
        roll_numbers: List of roll numbers to process
    """
    # Create a lock for this task
    task_locks[task_id] = threading.Lock()
    task_locks[task_id].acquire()
    
    try:
        # Create extraction service
        service = ExtractionService(shutdown_signal=shutdown_signal)
        
        # Run extraction
        results = service.extract_roll_numbers(roll_numbers)
        
        # Update task status
        active_tasks[task_id].update({
            "status": "completed",
            "completed": results["successful"],
            "failed": results["failed"],
            "results": results
        })
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        active_tasks[task_id].update({
            "status": "failed",
            "error": str(e)
        })
    finally:
        # Release the lock
        task_locks[task_id].release()
        # Clean up task resources
        if task_id in task_locks:
            del task_locks[task_id]


if __name__ == "__main__":
    # Run the API server
    uvicorn.run(
        "src.creiq.api:app",
        host=API_HOST,
        port=API_PORT,
        reload=API_RELOAD
    )
