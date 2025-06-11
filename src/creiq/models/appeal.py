"""
Appeal data models.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class PropertyInfo:
    """Property information model."""
    roll_number: str
    description: Optional[str] = None
    municipality: Optional[str] = None
    classification: Optional[str] = None
    nbhd: Optional[str] = None


@dataclass
class AppellantInfo:
    """Appellant information model."""
    name1: Optional[str] = None
    name2: Optional[str] = None
    representative: Optional[str] = None
    filing_date: Optional[str] = None
    tax_date: Optional[str] = None
    section: Optional[str] = None
    reason_for_appeal: Optional[str] = None


@dataclass
class DecisionInfo:
    """Decision information model."""
    decision_number: Optional[str] = None
    mailing_date: Optional[str] = None
    decisions: Optional[str] = None
    decision_details: Optional[str] = None


@dataclass
class Appeal:
    """Appeal model."""
    appeal_number: str
    property_info: PropertyInfo
    appellant_info: AppellantInfo
    status: str
    decision_info: DecisionInfo
    extracted_timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert appeal to dictionary."""
        return {
            "appeal_number": self.appeal_number,
            "property_info": {
                "roll_number": self.property_info.roll_number,
                "description": self.property_info.description,
                "municipality": self.property_info.municipality,
                "classification": self.property_info.classification,
                "nbhd": self.property_info.nbhd
            },
            "appellant_info": {
                "name1": self.appellant_info.name1,
                "name2": self.appellant_info.name2,
                "representative": self.appellant_info.representative,
                "filing_date": self.appellant_info.filing_date,
                "tax_date": self.appellant_info.tax_date,
                "section": self.appellant_info.section,
                "reason_for_appeal": self.appellant_info.reason_for_appeal
            },
            "status_info": {
                "status": self.status
            },
            "decision_info": {
                "decision_number": self.decision_info.decision_number,
                "mailing_date": self.decision_info.mailing_date,
                "decisions": self.decision_info.decisions,
                "decision_details": self.decision_info.decision_details
            },
            "extracted_timestamp": self.extracted_timestamp.isoformat()
        }


@dataclass
class ExtractionResult:
    """Extraction result model."""
    roll_number: str
    page_title: str
    property_info: Dict[str, Any]
    appeals: list[Appeal]
    extracted_timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "roll_number": self.roll_number,
            "extracted_timestamp": self.extracted_timestamp.isoformat(),
            "page_title": self.page_title,
            "property_info": self.property_info,
            "appeals": [appeal.to_dict() for appeal in self.appeals]
        } 