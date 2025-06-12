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

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from src.creiq.utils.roll_number_reader import read_roll_numbers_from_csv
from src.creiq.services.extraction_service import ExtractionService
from src.creiq.utils.logger import logger
from src.creiq.config.settings import API_HOST, API_PORT, API_RELOAD
from src.creiq.database.database import get_db, engine, Base
from src.creiq.database.service import DatabaseService
from src.creiq.database.models import RollNumber, Appeal
from sqlalchemy.orm import Session

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

# Create database tables
Base.metadata.create_all(bind=engine)


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


@app.get("/api/roll_numbers")
async def get_roll_numbers(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get all roll numbers with pagination.
    
    Args:
        limit: Maximum number of records to return
        offset: Number of records to skip
        
    Returns:
        List of roll numbers with their status
    """
    db_service = DatabaseService(db)
    roll_numbers = db_service.get_all_roll_numbers(limit=limit, offset=offset)
    
    return {
        "roll_numbers": [
            {
                "roll_number": r.roll_number,
                "property_description": r.property_description,
                "municipality": r.municipality,
                "extraction_status": r.extraction_status,
                "last_extracted_at": r.last_extracted_at.isoformat() if r.last_extracted_at else None,
                "appeals_count": len(r.appeals)
            }
            for r in roll_numbers
        ],
        "limit": limit,
        "offset": offset
    }


@app.get("/api/roll_numbers/{roll_number}")
async def get_roll_number_details(
    roll_number: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed information for a specific roll number.
    
    Args:
        roll_number: The roll number to retrieve
        
    Returns:
        Roll number details including all appeals with complete data
    """
    db_service = DatabaseService(db)
    roll_record = db_service.get_roll_number(roll_number)
    
    if not roll_record:
        raise HTTPException(status_code=404, detail="Roll number not found")
    
    return {
        "roll_number": roll_record.roll_number,
        "property_info": {
            "description": roll_record.property_description,
            "municipality": roll_record.municipality,
            "classification": roll_record.classification,
            "nbhd": roll_record.nbhd
        },
        "extraction_status": roll_record.extraction_status,
        "extraction_error": roll_record.extraction_error,
        "created_at": roll_record.created_at.isoformat() if roll_record.created_at else None,
        "updated_at": roll_record.updated_at.isoformat() if roll_record.updated_at else None,
        "last_extracted_at": roll_record.last_extracted_at.isoformat() if roll_record.last_extracted_at else None,
        "appeals": [
            {
                # Basic info
                "id": a.id,
                "appeal_number": a.appeal_number,
                
                # Summary information (from main page)
                "summary_info": {
                    "appellant": a.appellant,
                    "representative": a.representative,
                    "section": a.section,
                    "tax_date": a.tax_date,
                    "hearing_number": a.hearing_number,
                    "hearing_date": a.hearing_date,
                    "status": a.status,
                    "board_order_number": a.board_order_number
                },
                
                # Appellant information (from detail page)
                "appellant_info": {
                    "name1": a.appellant_name1,
                    "name2": a.appellant_name2,
                    "filing_date": a.filing_date,
                    "reason_for_appeal": a.reason_for_appeal
                },
                
                # Decision information
                "decision_info": {
                    "decision_number": a.decision_number,
                    "mailing_date": a.decision_mailing_date,
                    "decisions": a.decisions,
                    "decision_details": a.decision_details
                },
                
                # Property information from detail page
                "property_info_from_appeal": {
                    "roll_number": a.property_roll_number,
                    "municipality": a.property_municipality,
                    "classification": a.property_classification,
                    "nbhd": a.property_nbhd,
                    "description": a.property_description
                },
                
                # Additional data
                "detail_screenshot_path": a.detail_screenshot_path,
                "summary_data": a.summary_data,
                "detail_data": a.detail_data,
                
                # Timestamps
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "updated_at": a.updated_at.isoformat() if a.updated_at else None
            }
            for a in roll_record.appeals
        ]
    }


@app.get("/api/appeals/{appeal_number}")
async def get_appeal_details(
    appeal_number: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed information for a specific appeal.
    
    Args:
        appeal_number: The appeal number to retrieve
        
    Returns:
        Complete appeal details
    """
    db_service = DatabaseService(db)
    appeal = db_service.get_appeal(appeal_number)
    
    if not appeal:
        raise HTTPException(status_code=404, detail="Appeal not found")
    
    return {
        "appeal_number": appeal.appeal_number,
        "roll_number": appeal.roll_number,
        "summary_info": {
            "appellant": appeal.appellant,
            "representative": appeal.representative,
            "section": appeal.section,
            "tax_date": appeal.tax_date,
            "hearing_number": appeal.hearing_number,
            "hearing_date": appeal.hearing_date,
            "status": appeal.status,
            "board_order_number": appeal.board_order_number
        },
        "appellant_info": {
            "name1": appeal.appellant_name1,
            "name2": appeal.appellant_name2,
            "filing_date": appeal.filing_date,
            "reason_for_appeal": appeal.reason_for_appeal
        },
        "decision_info": {
            "decision_number": appeal.decision_number,
            "mailing_date": appeal.decision_mailing_date,
            "decisions": appeal.decisions,
            "decision_details": appeal.decision_details
        },
        "property_info": {
            "roll_number": appeal.property_roll_number,
            "municipality": appeal.property_municipality,
            "classification": appeal.property_classification,
            "nbhd": appeal.property_nbhd,
            "description": appeal.property_description
        }
    }


@app.delete("/api/roll_numbers/{roll_number}")
async def delete_roll_number(
    roll_number: str,
    db: Session = Depends(get_db)
):
    """
    Delete a roll number and all associated appeals.
    
    Args:
        roll_number: The roll number to delete
        
    Returns:
        Deletion confirmation
    """
    db_service = DatabaseService(db)
    
    if not db_service.delete_roll_number(roll_number):
        raise HTTPException(status_code=404, detail="Roll number not found")
    
    return {"message": f"Roll number {roll_number} and associated appeals deleted successfully"}


@app.delete("/api/appeals/{appeal_id}")
async def delete_appeal(
    appeal_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete an individual appeal.
    
    Args:
        appeal_id: The appeal ID to delete
        
    Returns:
        Deletion confirmation
    """
    db_service = DatabaseService(db)
    
    if not db_service.delete_appeal(appeal_id):
        raise HTTPException(status_code=404, detail="Appeal not found")
    
    return {"message": f"Appeal {appeal_id} deleted successfully"}


@app.get("/api/stats")
async def get_database_stats(db: Session = Depends(get_db)):
    """
    Get database statistics.
    
    Returns:
        Statistics about roll numbers and appeals
    """
    from sqlalchemy import func
    
    total_roll_numbers = db.query(func.count(RollNumber.roll_number)).scalar()
    total_appeals = db.query(func.count(Appeal.id)).scalar()
    
    status_counts = db.query(
        RollNumber.extraction_status,
        func.count(RollNumber.roll_number)
    ).group_by(RollNumber.extraction_status).all()
    
    appeal_status_counts = db.query(
        Appeal.status,
        func.count(Appeal.id)
    ).group_by(Appeal.status).all()
    
    return {
        "total_roll_numbers": total_roll_numbers,
        "total_appeals": total_appeals,
        "roll_number_status_breakdown": {
            status: count for status, count in status_counts
        },
        "appeal_status_breakdown": {
            status: count for status, count in appeal_status_counts if status
        }
    }


if __name__ == "__main__":
    # Run the API server
    uvicorn.run(
        "src.creiq.api:app",
        host=API_HOST,
        port=API_PORT,
        reload=API_RELOAD
    )
