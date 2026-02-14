"""LLM-based document parsing for flexible RFP extraction."""
from __future__ import annotations

import json
import logging
from typing import List, Optional

from app.schemas.rfp_types import (
    EnhancedRequirement,
    ExtractedMetadata,
    ExtractedSection,
    RFPType,
    RFP_TYPE_CONFIGS,
    RequirementPriority,
    RequirementType,
)
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


async def extract_metadata_with_llm(
    text: str,
    rfp_type: RFPType,
    llm_client: LLMClient,
) -> ExtractedMetadata:
    """
    Extract metadata from RFP document using LLM.

    This replaces the hardcoded regex patterns with intelligent extraction
    that adapts to different RFP types.
    """
    config = RFP_TYPE_CONFIGS.get(rfp_type, RFP_TYPE_CONFIGS[RFPType.CUSTOM])

    # Build the prompt based on RFP type
    if rfp_type in [RFPType.GOVERNMENT_RFP, RFPType.GOVERNMENT_RFI, RFPType.GOVERNMENT_RFQ, RFPType.GOVERNMENT_SOURCES_SOUGHT]:
        extraction_instructions = """
For this GOVERNMENT document, extract:
- document_type: The type of document (RFP, RFI, RFQ, Sources Sought, etc.)
- title: The title or subject of the solicitation
- reference_number: Solicitation number, RFP number, or reference ID
- issuing_organization: The government agency or department
- due_date: Submission deadline date (format: YYYY-MM-DD if possible)
- due_time: Submission deadline time (format: HH:MM AM/PM)
- timezone: Timezone for the deadline (e.g., "Eastern", "Central", "Pacific")
- naics_code: 6-digit NAICS code if present
- psc_code: Product Service Code if present
- set_aside: Any set-aside designation (Small Business, 8(a), WOSB, HUBZone, SDVOSB, etc.)
- contract_type: Type of contract (FFP, T&M, Cost-Plus, IDIQ, BPA, etc.)
- contact_name: Contracting Officer or Contract Specialist name
- contact_email: Contact email address
- contact_phone: Contact phone number
- page_limit: Maximum page count for response
- font_requirements: Required font and size
- file_format: Required file format for submission (.docx, .pdf, etc.)
- evaluation_criteria: List of evaluation factors or criteria
"""
    elif rfp_type in [RFPType.COMMERCIAL_RFP, RFPType.COMMERCIAL_RFQ, RFPType.VENDOR_APPLICATION]:
        extraction_instructions = """
For this COMMERCIAL document, extract:
- document_type: The type of document (RFP, RFQ, Vendor Application, etc.)
- title: The title or subject
- reference_number: RFP/RFQ reference number or ID
- issuing_organization: The company or organization issuing the RFP
- due_date: Submission deadline date (format: YYYY-MM-DD if possible)
- due_time: Submission deadline time if specified
- timezone: Timezone for the deadline
- contact_name: Primary contact name
- contact_email: Contact email address
- contact_phone: Contact phone number
- page_limit: Maximum page count if specified
- file_format: Required submission format
- evaluation_criteria: List of evaluation criteria or selection factors
"""
    elif rfp_type == RFPType.GRANT_APPLICATION:
        extraction_instructions = """
For this GRANT APPLICATION, extract:
- document_type: Type of grant (Federal Grant, Foundation Grant, etc.)
- title: Grant program name or title
- reference_number: Grant number, CFDA number, or reference ID
- issuing_organization: Funding agency or foundation
- due_date: Application deadline date (format: YYYY-MM-DD if possible)
- due_time: Application deadline time
- timezone: Timezone for the deadline
- contact_name: Program officer or contact name
- contact_email: Contact email
- page_limit: Page limits for application sections
- evaluation_criteria: Review criteria or scoring factors
"""
    else:
        extraction_instructions = """
Extract any relevant metadata including:
- document_type: What type of document this is
- title: The title or subject
- reference_number: Any reference or ID number
- issuing_organization: Who issued this document
- due_date: Any deadline date
- contact_name: Contact person
- contact_email: Contact email
- evaluation_criteria: Any evaluation or selection criteria
"""

    prompt = f"""Analyze this document and extract metadata.

{extraction_instructions}

IMPORTANT INSTRUCTIONS:
- Only extract information that is explicitly stated in the document
- Use null for any field not found in the document
- For dates, try to use YYYY-MM-DD format when possible
- For evaluation_criteria, return as a list of strings
- Return ONLY valid JSON, no markdown formatting

Document text (first 15000 characters):
{text[:15000]}

Return the extracted metadata as a JSON object with snake_case keys:
"""

    try:
        messages = [
            {"role": "system", "content": "You are a document analysis assistant that extracts structured metadata from RFP documents. Always return valid JSON."},
            {"role": "user", "content": prompt}
        ]

        response = llm_client.complete(messages, temperature=0.1)

        # Clean up response - remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        response = response.strip()

        # Parse JSON response
        data = json.loads(response)

        # Build ExtractedMetadata object
        return ExtractedMetadata(
            document_type=data.get("document_type"),
            title=data.get("title"),
            reference_number=data.get("reference_number") or data.get("solicitation_number"),
            issuing_organization=data.get("issuing_organization") or data.get("agency"),
            due_date=data.get("due_date"),
            due_time=data.get("due_time"),
            timezone=data.get("timezone"),
            naics_code=data.get("naics_code"),
            psc_code=data.get("psc_code"),
            set_aside=data.get("set_aside"),
            contract_type=data.get("contract_type"),
            contact_name=data.get("contact_name"),
            contact_email=data.get("contact_email"),
            contact_phone=data.get("contact_phone"),
            page_limit=data.get("page_limit"),
            font_requirements=data.get("font_requirements"),
            file_format=data.get("file_format"),
            evaluation_criteria=data.get("evaluation_criteria", []),
            additional_fields={k: v for k, v in data.items() if k not in ExtractedMetadata.model_fields}
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        return ExtractedMetadata()
    except Exception as e:
        logger.error(f"Error in LLM metadata extraction: {e}")
        return ExtractedMetadata()


async def extract_sections_with_llm(
    text: str,
    rfp_type: RFPType,
    llm_client: LLMClient,
) -> List[ExtractedSection]:
    """
    Extract required response sections from RFP document using LLM.

    This identifies what sections/questions the response must address,
    adapting to the actual RFP structure rather than using fixed templates.
    """
    config = RFP_TYPE_CONFIGS.get(rfp_type, RFP_TYPE_CONFIGS[RFPType.CUSTOM])
    common_sections = config.get("common_sections", [])

    prompt = f"""Analyze this RFP/solicitation document and identify ALL sections that must be addressed in the response.

CONTEXT: This is a {config.get('name', 'document')}. Common sections for this type include: {', '.join(common_sections)}

INSTRUCTIONS:
1. Read through the document carefully
2. Identify every section, question, or topic that requires a response
3. Note any page limits, word limits, or evaluation weights mentioned
4. Determine if each section is mandatory or optional

For each section found, extract:
- section_id: A unique identifier (e.g., "1", "2.1", "A", "executive_summary")
- section_title: The title or topic name
- subsections: List of any subsections or sub-questions
- requirements: List of specific requirements or questions to address
- page_limit: Page limit if specified (as integer, or null)
- is_mandatory: true if required, false if optional
- evaluation_weight: Evaluation weight if stated (e.g., "30%", "High Priority")
- order: Suggested order in the response (1, 2, 3, etc.)

Document text (first 20000 characters):
{text[:20000]}

Return as a JSON array of section objects. Return ONLY valid JSON, no markdown formatting:
"""

    try:
        messages = [
            {"role": "system", "content": "You are a document analysis assistant that identifies response sections from RFP documents. Always return valid JSON arrays."},
            {"role": "user", "content": prompt}
        ]

        response = llm_client.complete(messages, temperature=0.1)

        # Clean up response
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        response = response.strip()

        # Parse JSON response
        sections_data = json.loads(response)

        if not isinstance(sections_data, list):
            sections_data = [sections_data]

        sections = []
        for i, section in enumerate(sections_data):
            sections.append(ExtractedSection(
                section_id=section.get("section_id", f"section_{i+1}"),
                section_title=section.get("section_title", f"Section {i+1}"),
                subsections=section.get("subsections", []),
                requirements=section.get("requirements", []),
                page_limit=section.get("page_limit"),
                is_mandatory=section.get("is_mandatory", True),
                evaluation_weight=section.get("evaluation_weight"),
                order=section.get("order", i + 1)
            ))

        # Sort by order
        sections.sort(key=lambda s: s.order)

        return sections

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM sections response as JSON: {e}")
        # Return default sections based on RFP type
        return _get_default_sections(rfp_type)
    except Exception as e:
        logger.error(f"Error in LLM section extraction: {e}")
        return _get_default_sections(rfp_type)


async def extract_requirements_with_llm(
    text: str,
    sections: List[ExtractedSection],
    rfp_type: RFPType,
    llm_client: LLMClient,
) -> List[EnhancedRequirement]:
    """
    Extract and categorize requirements from RFP document using LLM.

    This provides semantic understanding of requirements, not just keyword matching.
    """
    sections_context = "\n".join([f"- {s.section_id}: {s.section_title}" for s in sections])

    prompt = f"""Analyze this RFP document and extract ALL requirements that the response must address.

DETECTED SECTIONS:
{sections_context}

INSTRUCTIONS:
1. Extract both EXPLICIT requirements (stated with "shall", "must", "required")
2. Extract IMPLICIT requirements (implied by evaluation criteria, scope descriptions)
3. Categorize each requirement by type
4. Assign priority based on language strength and evaluation importance
5. Link requirements to their source sections

For each requirement, provide:
- id: Unique identifier (e.g., "REQ-001", "REQ-002")
- source_section: Which section this requirement comes from (use section_id from above)
- requirement_text: The requirement statement (summarized if very long)
- requirement_type: One of: technical, management, past_performance, cost, schedule, compliance, qualifications, staffing, security, other
- priority: One of: must (mandatory/pass-fail), should (important), nice_to_have (optional), informational (context only)
- evaluation_weight: If stated (e.g., "30%")
- compliance_keywords: List of key terms that should appear in the response
- source_reference: Brief note on where this was found

Document text (first 25000 characters):
{text[:25000]}

Return as a JSON array. Return ONLY valid JSON, no markdown formatting:
"""

    try:
        messages = [
            {"role": "system", "content": "You are a requirements analyst that extracts and categorizes requirements from RFP documents. Always return valid JSON arrays."},
            {"role": "user", "content": prompt}
        ]

        response = llm_client.complete(messages, temperature=0.1)

        # Clean up response
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        response = response.strip()

        # Parse JSON response
        requirements_data = json.loads(response)

        if not isinstance(requirements_data, list):
            requirements_data = [requirements_data]

        requirements = []
        for i, req in enumerate(requirements_data):
            # Map string values to enums
            req_type = req.get("requirement_type", "other").lower()
            try:
                requirement_type = RequirementType(req_type)
            except ValueError:
                requirement_type = RequirementType.OTHER

            priority_str = req.get("priority", "should").lower()
            try:
                priority = RequirementPriority(priority_str)
            except ValueError:
                priority = RequirementPriority.SHOULD

            requirements.append(EnhancedRequirement(
                id=req.get("id", f"REQ-{i+1:03d}"),
                source_section=req.get("source_section"),
                requirement_text=req.get("requirement_text", ""),
                requirement_type=requirement_type,
                priority=priority,
                evaluation_weight=req.get("evaluation_weight"),
                compliance_keywords=req.get("compliance_keywords", []),
                source_reference=req.get("source_reference", "")
            ))

        return requirements

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM requirements response as JSON: {e}")
        return []
    except Exception as e:
        logger.error(f"Error in LLM requirements extraction: {e}")
        return []


def _get_default_sections(rfp_type: RFPType) -> List[ExtractedSection]:
    """Return default sections based on RFP type when LLM extraction fails."""
    config = RFP_TYPE_CONFIGS.get(rfp_type, RFP_TYPE_CONFIGS[RFPType.CUSTOM])
    common_sections = config.get("common_sections", [])

    if not common_sections:
        common_sections = ["Executive Summary", "Technical Approach", "Management", "Past Performance"]

    sections = []
    for i, title in enumerate(common_sections):
        section_id = title.lower().replace(" ", "_").replace("/", "_")
        sections.append(ExtractedSection(
            section_id=section_id,
            section_title=title,
            subsections=[],
            requirements=[],
            page_limit=None,
            is_mandatory=True,
            evaluation_weight=None,
            order=i + 1
        ))

    return sections


async def detect_rfp_type(
    text: str,
    llm_client: LLMClient,
) -> RFPType:
    """
    Auto-detect the RFP type from document content.

    Useful when user doesn't specify the type.
    """
    prompt = f"""Analyze this document and determine what type of RFP/solicitation it is.

Possible types:
- government_rfp: Federal, state, or local government Request for Proposal
- government_rfi: Government Request for Information (market research)
- government_rfq: Government Request for Quote
- sources_sought: Government Sources Sought notice
- commercial_rfp: Private company Request for Proposal
- commercial_rfq: Private company Request for Quote
- vendor_application: Vendor registration or qualification application
- grant: Grant application or funding request
- custom: Other/unknown type

Look for indicators like:
- Government: NAICS codes, PSC codes, FAR references, agency names, .gov contacts
- Commercial: Company names, corporate language, vendor requirements
- Grant: Funding amounts, grant numbers, CFDA references

Document text (first 5000 characters):
{text[:5000]}

Return ONLY the type identifier (e.g., "government_rfp"), nothing else:
"""

    try:
        messages = [
            {"role": "system", "content": "You are a document classifier. Return only the document type identifier, no explanation."},
            {"role": "user", "content": prompt}
        ]

        response = llm_client.complete(messages, temperature=0.1)
        response = response.strip().lower().replace('"', '').replace("'", "")

        # Try to match to RFPType enum
        for rfp_type in RFPType:
            if rfp_type.value == response or rfp_type.name.lower() == response:
                return rfp_type

        # Default to government RFP if unclear
        if "government" in response or "federal" in response:
            return RFPType.GOVERNMENT_RFP
        elif "commercial" in response or "private" in response:
            return RFPType.COMMERCIAL_RFP
        elif "grant" in response:
            return RFPType.GRANT_APPLICATION
        else:
            return RFPType.CUSTOM

    except Exception as e:
        logger.error(f"Error detecting RFP type: {e}")
        return RFPType.CUSTOM
