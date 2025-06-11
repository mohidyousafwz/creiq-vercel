"""Database service for CREIQ."""
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .models import RollNumber, Appeal
from ..utils.logger import logger


class DatabaseService:
    """Service for database operations."""
    
    def __init__(self, db: Session):
        """Initialize database service with session."""
        self.db = db
    
    def create_or_update_roll_number(self, roll_number: str, property_info: Dict[str, Any] = None) -> RollNumber:
        """Create or update a roll number record."""
        try:
            # Check if roll number exists
            roll_record = self.db.query(RollNumber).filter(RollNumber.roll_number == roll_number).first()
            
            if not roll_record:
                # Create new record
                roll_record = RollNumber(roll_number=roll_number)
                self.db.add(roll_record)
            
            # Update property info if provided
            if property_info:
                roll_record.property_description = property_info.get("description")
                roll_record.municipality = property_info.get("municipality")
                roll_record.classification = property_info.get("classification")
                roll_record.nbhd = property_info.get("nbhd")
            
            roll_record.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Created/updated roll number: {roll_number}")
            return roll_record
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating/updating roll number {roll_number}: {e}")
            raise
    
    def update_roll_number_status(self, roll_number: str, status: str, error: str = None) -> None:
        """Update roll number extraction status."""
        try:
            roll_record = self.db.query(RollNumber).filter(RollNumber.roll_number == roll_number).first()
            if roll_record:
                roll_record.extraction_status = status
                roll_record.extraction_error = error
                if status == "completed":
                    roll_record.last_extracted_at = datetime.utcnow()
                self.db.commit()
                logger.info(f"Updated status for {roll_number}: {status}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating status for {roll_number}: {e}")
            raise
    
    def create_or_update_appeal(self, appeal_data: Dict[str, Any], roll_number: str) -> Appeal:
        """Create or update an appeal record."""
        try:
            appeal_number = appeal_data.get("appealnumber") or appeal_data.get("appeal_number")
            
            if not appeal_number:
                raise ValueError("Appeal number is required")
            
            # Check if appeal exists
            appeal = self.db.query(Appeal).filter(Appeal.appeal_number == appeal_number).first()
            
            if not appeal:
                # Create new appeal
                appeal = Appeal(
                    appeal_number=appeal_number,
                    roll_number=roll_number
                )
                self.db.add(appeal)
            
            # Update summary data
            appeal.appellant = appeal_data.get("appellant")
            appeal.representative = appeal_data.get("representative")
            appeal.section = appeal_data.get("section")
            appeal.tax_date = appeal_data.get("tax_date")
            appeal.hearing_number = appeal_data.get("hearing_number")
            appeal.hearing_date = appeal_data.get("hearing_date")
            appeal.status = appeal_data.get("status")
            appeal.board_order_number = appeal_data.get("board_order_number")
            
            # Store full summary data as JSON
            appeal.summary_data = appeal_data
            appeal.updated_at = datetime.utcnow()
            
            self.db.commit()
            logger.info(f"Created/updated appeal: {appeal_number}")
            return appeal
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating/updating appeal {appeal_data.get('appealnumber')}: {e}")
            raise
    
    def update_appeal_details(self, appeal_number: str, detail_data: Dict[str, Any]) -> None:
        """Update appeal with detailed information."""
        try:
            appeal = self.db.query(Appeal).filter(Appeal.appeal_number == appeal_number).first()
            
            if not appeal:
                logger.warning(f"Appeal {appeal_number} not found for detail update")
                return
            
            # Update appellant info
            appellant_info = detail_data.get("appellant_info", {})
            appeal.appellant_name1 = appellant_info.get("name1")
            appeal.appellant_name2 = appellant_info.get("name2")
            appeal.filing_date = appellant_info.get("filing_date")
            appeal.reason_for_appeal = appellant_info.get("reason_for_appeal")
            
            # Update decision info
            decision_info = detail_data.get("decision_info", {})
            appeal.decision_number = decision_info.get("decision_number")
            appeal.decision_mailing_date = decision_info.get("mailing_date")
            appeal.decisions = decision_info.get("decisions")
            appeal.decision_details = decision_info.get("decision_details")
            
            # Update property info from detail page
            property_info = detail_data.get("property_info", {})
            appeal.property_roll_number = property_info.get("roll_number")
            appeal.property_municipality = property_info.get("municipality")
            appeal.property_classification = property_info.get("classification")
            appeal.property_nbhd = property_info.get("nbhd")
            appeal.property_description = property_info.get("description")
            
            # Store full detail data as JSON
            appeal.detail_data = detail_data
            appeal.updated_at = datetime.utcnow()
            
            self.db.commit()
            logger.info(f"Updated appeal details: {appeal_number}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating appeal details for {appeal_number}: {e}")
            raise
    
    def save_extraction_results(self, roll_number: str, summary_data: Dict[str, Any], 
                              detail_data: Dict[str, Any] = None) -> None:
        """Save complete extraction results to database."""
        try:
            # Create/update roll number
            property_info = summary_data.get("property_info", {})
            roll_record = self.create_or_update_roll_number(roll_number, property_info)
            
            # Update status to processing
            self.update_roll_number_status(roll_number, "processing")
            
            # Process appeals from summary
            appeals_info = summary_data.get("appeal_info", [])
            for appeal_data in appeals_info:
                self.create_or_update_appeal(appeal_data, roll_number)
            
            # Process detailed appeal data if available
            if detail_data and detail_data.get("appeals"):
                for appeal_detail in detail_data["appeals"]:
                    appeal_number = appeal_detail.get("appeal_number")
                    if appeal_number:
                        self.update_appeal_details(appeal_number, appeal_detail)
            
            # Update status to completed
            self.update_roll_number_status(roll_number, "completed")
            
            logger.info(f"Successfully saved extraction results for {roll_number}")
            
        except Exception as e:
            # Update status to failed
            self.update_roll_number_status(roll_number, "failed", str(e))
            logger.error(f"Error saving extraction results for {roll_number}: {e}")
            raise
    
    def get_roll_number(self, roll_number: str) -> Optional[RollNumber]:
        """Get roll number with appeals."""
        return self.db.query(RollNumber).filter(RollNumber.roll_number == roll_number).first()
    
    def get_all_roll_numbers(self, limit: int = 100, offset: int = 0) -> List[RollNumber]:
        """Get all roll numbers with pagination."""
        return self.db.query(RollNumber).limit(limit).offset(offset).all()
    
    def get_appeal(self, appeal_number: str) -> Optional[Appeal]:
        """Get appeal by appeal number."""
        return self.db.query(Appeal).filter(Appeal.appeal_number == appeal_number).first()
    
    def get_appeals_by_roll_number(self, roll_number: str) -> List[Appeal]:
        """Get all appeals for a roll number."""
        return self.db.query(Appeal).filter(Appeal.roll_number == roll_number).all()
    
    def delete_roll_number(self, roll_number: str) -> bool:
        """Delete roll number and associated appeals."""
        try:
            roll_record = self.get_roll_number(roll_number)
            if roll_record:
                self.db.delete(roll_record)
                self.db.commit()
                logger.info(f"Deleted roll number: {roll_number}")
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting roll number {roll_number}: {e}")
            raise 