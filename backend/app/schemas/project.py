from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from app.schemas.analysis import ComplianceRow, RequirementItem


class ProjectCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    solicitation_text: str = Field(..., min_length=250)
    company_name: Optional[str] = None
    company_profile: str = Field(..., min_length=50)
    past_performance: List[str] = Field(default_factory=list)
    capability_statement: Optional[str] = None


class ProjectResponse(BaseModel):
    id: UUID
    title: str
    status: str
    metadata_json: Dict[str, str]
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
    metadata_json: Dict[str, str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectUpdateRequest(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
