from datetime import date
from enum import Enum
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    RULEMAKING_RELEASE = "RulemakingRelease"
    STANDARD = "Standard"
    STAFF_GUIDANCE = "StaffGuidance"
    SEC_FORM = "SECForm"


class Status(str, Enum):
    EFFECTIVE = "Effective"
    PROPOSED = "Proposed"
    DELAYED = "Delayed"


class SourceA_Document(BaseModel):
    standard_id: str = Field(description="PCAOB standard identifier (AS/QC/EI prefix + number)")
    title: str = Field(description="Full title of the standard or guidance")
    document_type: DocumentType = Field(description="Type of PCAOB document")
    issue_date: date = Field(description="Date the document was issued")
    effective_date: date = Field(description="Effective date for compliance")
    status: Status = Field(description="Current status of the standard")
    source_url: str = Field(description="URL to the authoritative source")
    file_path: str = Field(description="Local path to the document file")
