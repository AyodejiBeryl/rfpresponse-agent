"""RFP type definitions for flexible document handling."""
from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


class RFPType(str, Enum):
    """Supported RFP/RFI document types."""

    # Government
    GOVERNMENT_RFP = "government_rfp"
    GOVERNMENT_RFI = "government_rfi"
    GOVERNMENT_RFQ = "government_rfq"
    GOVERNMENT_SOURCES_SOUGHT = "sources_sought"

    # Commercial
    COMMERCIAL_RFP = "commercial_rfp"
    COMMERCIAL_RFQ = "commercial_rfq"
    VENDOR_APPLICATION = "vendor_application"

    # Other
    GRANT_APPLICATION = "grant"
    CUSTOM = "custom"


class RequirementType(str, Enum):
    """Types of requirements that can be extracted."""

    TECHNICAL = "technical"
    MANAGEMENT = "management"
    PAST_PERFORMANCE = "past_performance"
    COST = "cost"
    SCHEDULE = "schedule"
    COMPLIANCE = "compliance"
    QUALIFICATIONS = "qualifications"
    STAFFING = "staffing"
    SECURITY = "security"
    OTHER = "other"


class RequirementPriority(str, Enum):
    """Priority levels for requirements."""

    MUST = "must"  # Mandatory, pass/fail
    SHOULD = "should"  # Important but not mandatory
    NICE_TO_HAVE = "nice_to_have"  # Adds value but optional
    INFORMATIONAL = "informational"  # For context only


class ExtractedSection(BaseModel):
    """A section detected from the RFP document."""

    section_id: str
    section_title: str
    subsections: List[str] = []
    requirements: List[str] = []
    page_limit: Optional[int] = None
    is_mandatory: bool = True
    evaluation_weight: Optional[str] = None
    order: int = 0


class ExtractedMetadata(BaseModel):
    """Metadata extracted from RFP document."""

    # Common fields
    document_type: Optional[str] = None
    title: Optional[str] = None
    reference_number: Optional[str] = None
    issuing_organization: Optional[str] = None
    due_date: Optional[str] = None
    due_time: Optional[str] = None
    timezone: Optional[str] = None

    # Government-specific
    naics_code: Optional[str] = None
    psc_code: Optional[str] = None
    set_aside: Optional[str] = None
    contract_type: Optional[str] = None

    # Contact info
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

    # Submission requirements
    page_limit: Optional[int] = None
    font_requirements: Optional[str] = None
    file_format: Optional[str] = None

    # Evaluation
    evaluation_criteria: List[str] = []

    # Additional fields (flexible)
    additional_fields: dict = {}


class EnhancedRequirement(BaseModel):
    """Enhanced requirement with more context."""

    id: str
    source_section: Optional[str] = None
    requirement_text: str
    requirement_type: RequirementType = RequirementType.OTHER
    priority: RequirementPriority = RequirementPriority.SHOULD
    evaluation_weight: Optional[str] = None
    compliance_keywords: List[str] = []
    source_reference: str = ""


# RFP type configurations
RFP_TYPE_CONFIGS = {
    RFPType.GOVERNMENT_RFP: {
        "name": "Government RFP",
        "description": "Federal, state, or local government Request for Proposal",
        "expected_metadata": [
            "solicitation_number", "naics_code", "psc_code", "set_aside",
            "contracting_officer", "due_date", "agency"
        ],
        "common_sections": [
            "Executive Summary", "Technical Approach", "Management Approach",
            "Past Performance", "Staffing Plan", "Cost/Price"
        ]
    },
    RFPType.GOVERNMENT_RFI: {
        "name": "Government RFI",
        "description": "Federal Request for Information (market research)",
        "expected_metadata": [
            "rfi_number", "agency", "due_date", "contact_email"
        ],
        "common_sections": [
            "Company Profile", "Capabilities", "Technical Approach", "Questions/Responses"
        ]
    },
    RFPType.GOVERNMENT_RFQ: {
        "name": "Government RFQ",
        "description": "Federal Request for Quote",
        "expected_metadata": [
            "rfq_number", "naics_code", "due_date", "quantities"
        ],
        "common_sections": [
            "Vendor Information", "Pricing", "Delivery Terms"
        ]
    },
    RFPType.COMMERCIAL_RFP: {
        "name": "Commercial RFP",
        "description": "Private sector Request for Proposal",
        "expected_metadata": [
            "rfp_reference", "company", "due_date", "contact"
        ],
        "common_sections": [
            "Executive Summary", "Solution Overview", "Implementation Plan",
            "Pricing", "References"
        ]
    },
    RFPType.COMMERCIAL_RFQ: {
        "name": "Commercial RFQ",
        "description": "Private sector Request for Quote",
        "expected_metadata": [
            "rfq_reference", "company", "due_date"
        ],
        "common_sections": [
            "Vendor Profile", "Product/Service Details", "Pricing"
        ]
    },
    RFPType.GRANT_APPLICATION: {
        "name": "Grant Application",
        "description": "Grant proposal for funding",
        "expected_metadata": [
            "grant_number", "funding_agency", "deadline", "funding_amount"
        ],
        "common_sections": [
            "Project Summary", "Statement of Need", "Goals and Objectives",
            "Methods", "Evaluation Plan", "Budget"
        ]
    },
    RFPType.CUSTOM: {
        "name": "Custom",
        "description": "Custom document type with user-defined extraction",
        "expected_metadata": [],
        "common_sections": []
    }
}
