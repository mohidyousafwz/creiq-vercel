"""
Utility for reading roll numbers from CSV files.
"""
import csv
import io
from typing import List
from pathlib import Path
from fastapi import UploadFile

from src.creiq.utils.logger import logger


class RollNumberReader:
    """
    A class to read roll numbers from a CSV file.
    """
    
    def __init__(self, csv_file_path: str):
        """
        Initialize the reader with a CSV file path.
        
        Args:
            csv_file_path: Path to the CSV file containing roll numbers
        """
        self.csv_file_path = Path(csv_file_path)
    
    def get_roll_numbers(self) -> List[str]:
        """
        Read and return all valid roll numbers from the CSV file.
        
        Returns:
            List of roll numbers (strings)
            
        Raises:
            FileNotFoundError: If the CSV file doesn't exist
            Exception: For other errors during file reading
        """
        if not self.csv_file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_file_path}")
        
        roll_numbers = []
        
        try:
            with open(self.csv_file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.reader(file)
                
                # Skip header if present
                first_row = next(csv_reader, None)
                if first_row and not self._is_roll_number(first_row[0]):
                    logger.info(f"Skipping header row: {first_row}")
                elif first_row:
                    # First row is a roll number
                    roll_numbers.append(first_row[0].strip())
                
                # Read remaining rows
                for row in csv_reader:
                    if row and row[0].strip():  # Check if row exists and has content
                        roll_number = row[0].strip()
                        if self._is_roll_number(roll_number):
                            roll_numbers.append(roll_number)
                        else:
                            logger.warning(f"Skipping invalid roll number: {roll_number}")
            
            logger.info(f"Successfully read {len(roll_numbers)} roll numbers from {self.csv_file_path}")
            return roll_numbers
            
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            raise
    
    def _is_roll_number(self, value: str) -> bool:
        """
        Basic validation to check if a value looks like a roll number.
        
        Args:
            value: String to validate
            
        Returns:
            True if value appears to be a roll number
        """
        # Remove dashes and check if it's numeric
        cleaned = value.replace('-', '').strip()
        return cleaned.isdigit() and len(cleaned) >= 10  # Roll numbers should have at least 10 digits


async def read_roll_numbers_from_csv(file: UploadFile) -> List[str]:
    """
    Read roll numbers from an uploaded CSV file.
    
    Args:
        file: Uploaded CSV file
        
    Returns:
        List of roll numbers
        
    Raises:
        ValueError: If the file is empty or contains no valid roll numbers
    """
    try:
        content = await file.read()
        if not content:
            raise ValueError("The uploaded file is empty")
            
        text = content.decode('utf-8')
        if not text.strip():
            raise ValueError("The uploaded file contains no data")
        
        roll_numbers = []
        csv_reader = csv.reader(io.StringIO(text))
        
        # Read all rows
        rows = list(csv_reader)
        if not rows:
            raise ValueError("The CSV file contains no rows")
            
        # Process each row
        for row in rows:
            if not row:  # Skip empty rows
                continue
                
            # Clean the roll number
            roll_number = row[0].strip()
            # Remove all quotes and extra spaces
            roll_number = roll_number.replace('"', '').strip()
            
            if roll_number:
                # Remove dashes and check if it's numeric
                cleaned = roll_number.replace('-', '').strip()
                if cleaned.isdigit() and len(cleaned) >= 10:
                    roll_numbers.append(roll_number)
                else:
                    logger.warning(f"Skipping invalid roll number format: {roll_number}")
        
        if not roll_numbers:
            raise ValueError("No valid roll numbers found in the CSV file")
            
        logger.info(f"Successfully read {len(roll_numbers)} roll numbers from uploaded file")
        return roll_numbers
        
    except UnicodeDecodeError:
        raise ValueError("The file is not a valid UTF-8 encoded CSV file")
    except csv.Error as e:
        raise ValueError(f"Invalid CSV format: {str(e)}")
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        raise ValueError(f"Error processing the CSV file: {str(e)}")