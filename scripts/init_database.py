#!/usr/bin/env python3
"""Initialize the database with tables."""
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.creiq.database.database import engine, Base
from src.creiq.database.models import RollNumber, Appeal
from src.creiq.utils.logger import logger


def init_database():
    """Initialize the database with all tables."""
    try:
        logger.info("Creating database tables...")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database tables created successfully!")
        
        # List created tables
        table_names = Base.metadata.tables.keys()
        logger.info(f"Created tables: {', '.join(table_names)}")
        
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


if __name__ == "__main__":
    init_database() 