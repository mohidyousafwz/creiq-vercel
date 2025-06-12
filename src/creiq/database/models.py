"""Database models for CREIQ."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, JSON, Integer
from sqlalchemy.orm import relationship
from .database import Base


class RollNumber(Base):
    """Roll number model."""
    __tablename__ = "roll_numbers"
    
    # Primary key
    roll_number = Column(String(50), primary_key=True, index=True)
    
    # Property information
    property_description = Column(Text, nullable=True)
    municipality = Column(String(200), nullable=True)
    classification = Column(String(100), nullable=True)
    nbhd = Column(String(50), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_extracted_at = Column(DateTime, nullable=True)
    
    # Status
    extraction_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    extraction_error = Column(Text, nullable=True)
    
    # Extraction progress tracking
    total_appeals_found = Column(Integer, nullable=True)  # Total appeals found on the main page
    appeals_extracted = Column(Integer, default=0)  # Number of appeals successfully extracted
    extraction_progress = Column(JSON, nullable=True)  # Detailed progress info (e.g., which appeals are done)
    
    # Relationships
    appeals = relationship("Appeal", back_populates="roll_number_ref", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<RollNumber {self.roll_number}>"


class Appeal(Base):
    """Appeal model."""
    __tablename__ = "appeals"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    appeal_number = Column(String(50), unique=True, index=True, nullable=False)
    
    # Foreign key
    roll_number = Column(String(50), ForeignKey("roll_numbers.roll_number"), nullable=False)
    
    # Appeal summary information (from main page)
    appellant = Column(String(500), nullable=True)
    representative = Column(String(500), nullable=True)
    section = Column(String(100), nullable=True)
    tax_date = Column(String(50), nullable=True)
    hearing_number = Column(String(50), nullable=True)
    hearing_date = Column(String(50), nullable=True)
    status = Column(String(100), nullable=True)
    board_order_number = Column(String(100), nullable=True)
    
    # Detailed appeal information (from detail page)
    # Appellant info
    appellant_name1 = Column(String(500), nullable=True)
    appellant_name2 = Column(String(500), nullable=True)
    filing_date = Column(String(50), nullable=True)
    reason_for_appeal = Column(Text, nullable=True)
    
    # Decision info
    decision_number = Column(String(100), nullable=True)
    decision_mailing_date = Column(String(50), nullable=True)
    decisions = Column(Text, nullable=True)
    decision_details = Column(Text, nullable=True)
    
    # Additional property info from detail page
    property_roll_number = Column(String(50), nullable=True)
    property_municipality = Column(String(200), nullable=True)
    property_classification = Column(String(100), nullable=True)
    property_nbhd = Column(String(50), nullable=True)
    property_description = Column(Text, nullable=True)
    
    # Store full JSON data for reference
    summary_data = Column(JSON, nullable=True)
    detail_data = Column(JSON, nullable=True)
    
    # File references
    detail_screenshot_path = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    roll_number_ref = relationship("RollNumber", back_populates="appeals")
    
    def __repr__(self):
        return f"<Appeal {self.appeal_number} for roll {self.roll_number}>" 