from __future__ import annotations

import re
from typing import List, Optional

from app.schemas.analysis import ComplianceRow, RequirementItem

STOPWORDS = {
    "shall",
    "must",
    "required",
    "offeror",
    "contractor",
    "vendor",
    "provide",
    "response",
    "proposal",
    "agency",
    "government",
    "federal",
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _keywords(text: str) -> List[str]:
    words = re.findall(r"[a-z0-9\-]{4,}", _normalize(text))
    return [w for w in words if w not in STOPWORDS][:12]


def _text_block(company_profile: str, past_performance: List[str], capability_statement: Optional[str]) -> str:
    pp = "\n".join(past_performance)
    cap = capability_statement or ""
    return _normalize(f"{company_profile}\n{pp}\n{cap}")


def build_compliance_matrix(
    requirements: List[RequirementItem],
    company_profile: str,
    past_performance: List[str],
    capability_statement: Optional[str] = None,
    knowledge_chunks: Optional[List[dict]] = None,
) -> List[ComplianceRow]:
    """Build compliance matrix using keyword overlap + optional RAG knowledge chunks.

    When knowledge_chunks is provided (from the org's knowledge base), semantic
    matches boost the compliance score for each requirement.
    """
    corpus = _text_block(company_profile, past_performance, capability_statement)

    # Build a searchable text from knowledge chunks
    knowledge_text = ""
    chunk_lookup: dict[str, list[str]] = {}  # req_id -> matching chunk excerpts
    if knowledge_chunks:
        knowledge_text = _normalize(
            " ".join(c.get("chunk_text", "") for c in knowledge_chunks)
        )

    matrix: List[ComplianceRow] = []

    for req in requirements:
        keys = _keywords(req.requirement_text)
        overlap_words = [w for w in keys if w in corpus]
        overlap = len(overlap_words)

        # Check knowledge base for additional matches
        kb_overlap_words = []
        if knowledge_text:
            kb_overlap_words = [w for w in keys if w in knowledge_text and w not in overlap_words]

        total_overlap = overlap + len(kb_overlap_words)

        if total_overlap >= 4:
            status = "met"
            all_evidence = overlap_words + kb_overlap_words
            source = "profile + knowledge base" if kb_overlap_words else "profile"
            evidence = f"Strong match ({source}): {', '.join(all_evidence[:6])}"
            notes = "Verify exact deliverables, staffing, and due-date constraints."
        elif total_overlap >= 2:
            status = "partial"
            all_evidence = overlap_words + kb_overlap_words
            source = "profile + knowledge base" if kb_overlap_words else "profile"
            evidence = f"Partial match ({source}): {', '.join(all_evidence[:5])}"
            notes = "Add proof points, metrics, and contract-specific tailoring."
        else:
            status = "missing"
            evidence = "No clear support found in profile/capability/past performance context."
            notes = "Needs SME input, artifacts, or teaming partner detail."

        matrix.append(
            ComplianceRow(
                requirement_id=req.id,
                status=status,
                evidence=evidence,
                owner=None,
                notes=notes,
            )
        )

    return matrix


def build_gaps(matrix: List[ComplianceRow]) -> List[str]:
    gaps = [f"{row.requirement_id}: {row.notes}" for row in matrix if row.status != "met"]
    return gaps or ["No major gaps auto-detected. Human validation still required."]
