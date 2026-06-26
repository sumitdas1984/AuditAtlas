from datetime import date
from enum import Enum
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    INTERNAL_AUDIT_REPORT = "InternalAuditReport"
    CONTROL_MATRIX = "ControlMatrix"
    RISK_REGISTER = "RiskRegister"
    POLICY = "Policy"
    SOP = "SOP"


class Classification(str, Enum):
    INTERNAL_USE_ONLY = "InternalUseOnly"
    INTERNAL_CONFIDENTIAL = "InternalConfidential"


class SourceC_Document(BaseModel):
    document_id: str = Field(description="Unique document identifier")
    document_type: DocumentType = Field(description="Type of synthetic document")
    version: str = Field(description="Document version")
    effective_date: date = Field(description="Date the document becomes effective")
    review_date: date = Field(description="Scheduled review date")
    classification: Classification = Field(description="Document classification level")
    owner: str = Field(description="Document owner name")
    company: str = Field(default="Northwind Retail Solutions Ltd.", description="Company name")
    file_path: str = Field(description="Local path to the document file")
