from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from app.schemas.analysis import ComplianceRow, RequirementItem
from app.schemas.rfp_types import (
    RFPType,
    ExtractedSection,
    ExtractedMetadata,
    EnhancedRequirement,
)


class ProjectCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    solicitation_text: str = Field(..., min_length=250)
    rfp_type: Optional[RFPType] = Field(
        default=None,
        description="Type of RFP document. If not provided, will be auto-detected."
    )
    company_name: Optional[str] = None
    company_profile: str = Field(..., min_length=50)
    past_performance: List[str] = Field(default_factory=list)
    capability_statement: Optional[str] = None


class ProjectResponse(BaseModel):
    id: UUID
    title: str
    status: str
    rfp_type: Optional[str] = None
    metadata_json: Dict[str, str]
    detected_sections: List[ExtractedSection] = []
    requirements: List[RequirementItem]
    compliance_matrix: List[ComplianceRow]
    gaps: List[str]
    draft_sections: Dict[str, str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListItem(BaseModel):
    id: UUID
    title: str
    status: str
    rfp_type: Optional[str] = None
    metadata_json: Dict[str, str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectUpdateRequest(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
