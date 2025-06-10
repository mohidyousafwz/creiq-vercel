"""
Module for reading and processing roll numbers from CSV files.
"""

import csv
import os
from typing import List


class RollNumberReader:
    """
    A class to read and process roll numbers from CSV files.
    """
    
    def __init__(self, file_path: str):
        """
        Initialize the RollNumberReader with the path to the CSV file.
        
        Args:
            file_path (str): Path to the CSV file containing roll numbers
        """
        self.file_path = file_path
        self.roll_numbers = []
        
    def read_roll_numbers(self) -> List[str]:
        """
        Read roll numbers from the CSV file.
        
        Returns:
            List[str]: List of roll numbers read from the file
        """
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"The file {self.file_path} does not exist.")
        
        self.roll_numbers = []
        
        with open(self.file_path, 'r') as file:
            csv_reader = csv.reader(file)
            for row in csv_reader:
                if row:  # Check if row is not empty
                    # Remove any quotes and whitespace
                    roll_number = row[0].strip().strip('"').strip("'")
                    if roll_number:  # Check if roll_number is not empty
                        self.roll_numbers.append(roll_number)
        
        return self.roll_numbers
    
    def print_roll_numbers(self) -> None:
        """
        Print all roll numbers that have been read.
        If no roll numbers have been read yet, read them first.
        """
        if not self.roll_numbers:
            self.read_roll_numbers()
            
        if not self.roll_numbers:
            print("No roll numbers found in the file.")
            return
            
        print("Roll Numbers:")
        for i, roll_number in enumerate(self.roll_numbers, 1):
            print(f"{i}. {roll_number}")
    
    def get_roll_numbers(self) -> List[str]:
        """
        Get the list of roll numbers.
        If no roll numbers have been read yet, read them first.
        
        Returns:
            List[str]: List of roll numbers
        """
        if not self.roll_numbers:
            self.read_roll_numbers()
        
        return self.roll_numbers