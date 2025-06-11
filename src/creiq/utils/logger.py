"""
Logging configuration and utilities.
"""
import logging
import sys
from pathlib import Path
from src.creiq.config.settings import LOG_LEVEL, LOG_FORMAT

def setup_logger(name: str = "creiq") -> logging.Logger:
    """
    Set up and return a configured logger.
    
    Args:
        name: Logger name (default: "creiq")
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(getattr(logging, LOG_LEVEL))
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, LOG_LEVEL))
        
        # Formatter
        formatter = logging.Formatter(LOG_FORMAT)
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(console_handler)
    
    return logger

# Create default logger instance
logger = setup_logger() 