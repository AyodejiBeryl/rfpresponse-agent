from __future__ import annotations
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field

Priority = Literal["must", "should", "informational"]
Status = Literal["met", "partial", "missing"]


class RequirementItem(BaseModel):
    id: str
    section: str
    requirement_text: str
    priority: Priority
    source_reference: str


class ComplianceRow(BaseModel):
    requirement_id: str
    status: Status
    evidence: str
    owner: Optional[str] = None
    notes: str = ""


class AnalyzeTextRequest(BaseModel):
    solicitation_text: str = Field(..., min_length=250)
    company_name: Optional[str] = None
    company_profile: str = Field(..., min_length=50)
    past_performance: List[str] = Field(default_factory=list)
    capability_statement: Optional[str] = None


class AnalysisResponse(BaseModel):
    disclaimer: str
    metadata: Dict[str, str]
    requirements: List[RequirementItem]
    compliance_matrix: List[ComplianceRow]
    draft_sections: Dict[str, str]
    gaps: List[str]


class ExportResponse(BaseModel):
    filename: str
    content_type: str
    content: str
