from datetime import date
from pydantic import BaseModel, Field


class SourceB_Document(BaseModel):
    company_name: str = Field(description="Full legal company name")
    ticker: str = Field(description="SEC ticker symbol (uppercase)")
    filing_date: date = Field(description="Date the 10-K was filed with SEC")
    fiscal_year: int = Field(description="Fiscal year covered by the filing")
    sections_present: list[str] = Field(description="List of SEC Items present in the filing")
    source_url: str = Field(description="URL to SEC EDGAR filing")
    file_path: str = Field(description="Local path to the filing file")
