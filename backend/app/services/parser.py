from __future__ import annotations

import io
import re
from typing import Dict, List

from docx import Document
from pypdf import PdfReader

from app.schemas.analysis import RequirementItem

META_PATTERNS = {
    "solicitation_number": [
        r"Solicitation\s*(?:No\.?|Number)?\s*[:#]?\s*([A-Z0-9\-]{5,})",
        r"RFP\s*(?:No\.?|Number)?\s*[:#]?\s*([A-Z0-9\-]{5,})",
        r"RFQ\s*(?:No\.?|Number)?\s*[:#]?\s*([A-Z0-9\-]{5,})",
    ],
    "due_date": [
        r"Due\s*Date\s*[:#]?\s*([A-Za-z]+\s+\d{1,2},\s*\d{4})",
        r"(?:Response|Proposal)\s*(?:Due|Deadline)\s*[:#]?\s*([A-Za-z]+\s+\d{1,2},\s*\d{4})",
    ],
    "naics": [r"NAICS\s*[:#]?\s*(\d{6})"],
    "psc": [r"PSC\s*[:#]?\s*([A-Z0-9]{4})"],
}

REQUIREMENT_HINTS = (
    "shall",
    "must",
    "required",
    "offeror shall",
    "vendor shall",
    "contractor shall",
    "is required to",
    "will provide",
)


def extract_text_from_pdf_bytes(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages).strip()


def extract_text_from_docx_bytes(data: bytes) -> str:
    doc = Document(io.BytesIO(data))
    lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n".join(lines)


def extract_metadata(text: str) -> Dict[str, str]:
    metadata: Dict[str, str] = {}
    for key, patterns in META_PATTERNS.items():
        value = "Not found"
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                break
        metadata[key] = value
    return metadata


def extract_requirements(text: str) -> List[RequirementItem]:
    requirements: List[RequirementItem] = []

    # Use sentence-level splitting first to improve capture quality over line-only parsing.
    normalized = re.sub(r"\s+", " ", text)
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", normalized)
    req_counter = 1

    for sentence in sentences:
        s = sentence.strip()
        if len(s) < 30:
            continue

        lower = s.lower()
        if any(h in lower for h in REQUIREMENT_HINTS):
            priority = (
                "must"
                if (" shall " in f" {lower} " or " must " in f" {lower} ")
                else "should"
            )
            requirements.append(
                RequirementItem(
                    id=f"REQ-{req_counter:03d}",
                    section="Auto-detected",
                    requirement_text=s,
                    priority=priority,
                    source_reference="sentence",
                )
            )
            req_counter += 1

    if not requirements:
        requirements.append(
            RequirementItem(
                id="REQ-001",
                section="General",
                requirement_text="No explicit requirement keywords auto-detected; manual review required.",
                priority="informational",
                source_reference="full_text",
            )
        )

    return requirements
