from __future__ import annotations

import os
from collections import Counter
from typing import Dict, List

from openai import OpenAI

from app.schemas.analysis import ComplianceRow, RequirementItem


def _build_prompt(
    metadata: Dict[str, str],
    requirements: List[RequirementItem],
    matrix: List[ComplianceRow],
    company_name: str | None,
    company_profile: str,
    past_performance: List[str],
) -> str:
    req_preview = "\n".join(
        f"- {r.id}: {r.requirement_text}" for r in requirements[:40]
    )
    gap_preview = "\n".join(f"- {m.requirement_id}: {m.status}" for m in matrix[:40])
    pp = (
        "\n".join(f"- {p}" for p in past_performance[:8])
        if past_performance
        else "- None provided"
    )

    return f"""
You are an expert federal proposal writer.
Write concise, compliant-first proposal draft sections using only provided context.
Do not invent certifications, contracts, or legal claims.

Company Name: {company_name or "Not provided"}
Metadata: {metadata}

Company Profile:
{company_profile[:5000]}

Past Performance:
{pp}

Requirements:
{req_preview}

Coverage Snapshot:
{gap_preview}

Output exactly these section headers in markdown:
## executive_summary
## technical_approach
## past_performance
## management_plan

Each section should be practical, specific, and ready for human editing.
""".strip()


def _split_sections(markdown: str) -> Dict[str, str]:
    sections = {
        "executive_summary": "",
        "technical_approach": "",
        "past_performance": "",
        "management_plan": "",
    }
    current = None
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        header = line.lower().replace(" ", "_")
        if header in {"##_executive_summary", "##executive_summary"}:
            current = "executive_summary"
            continue
        if header in {"##_technical_approach", "##technical_approach"}:
            current = "technical_approach"
            continue
        if header in {"##_past_performance", "##past_performance"}:
            current = "past_performance"
            continue
        if header in {"##_management_plan", "##management_plan"}:
            current = "management_plan"
            continue
        if current:
            sections[current] += raw_line + "\n"

    return {k: v.strip() for k, v in sections.items()}


def _generate_with_llm(prompt: str) -> str | None:
    provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()
    timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "90"))

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return None
        client = OpenAI(
            api_key=api_key, base_url="https://api.groq.com/openai/v1", timeout=timeout
        )
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        client = OpenAI(api_key=api_key, timeout=timeout)
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": "You draft federal proposal responses with strict factual grounding.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def _fallback_sections(
    metadata: Dict[str, str],
    requirements: List[RequirementItem],
    matrix: List[ComplianceRow],
    company_profile: str,
    past_performance: List[str],
) -> Dict[str, str]:
    status_counts = Counter(row.status for row in matrix)
    executive_summary = (
        "AI-generated draft; human review required.\n\n"
        f"This package addresses {len(requirements)} identified requirements for "
        f"solicitation {metadata.get('solicitation_number', 'not found')}. "
        f"Coverage snapshot: met={status_counts.get('met', 0)}, "
        f"partial={status_counts.get('partial', 0)}, missing={status_counts.get('missing', 0)}."
    )

    technical_approach = (
        "The team will execute through phased mobilization, requirements traceability, "
        "quality control checkpoints, and milestone-based reporting. "
        "Tailor this section to agency mission outcomes, staffing, and delivery timeline."
    )

    pp = (
        "\n".join(f"- {item}" for item in past_performance[:5])
        if past_performance
        else "- Add comparable project references."
    )
    past_performance_section = f"Relevant past performance:\n{pp}"

    management_plan = (
        "Assign a proposal manager, technical lead, and compliance reviewer. "
        "Run final red-team checks against every mandatory requirement and attachment."
    )

    profile_ref = f"Company context reference:\n{company_profile[:1800]}"
    return {
        "executive_summary": executive_summary,
        "technical_approach": technical_approach,
        "past_performance": past_performance_section,
        "management_plan": management_plan,
        "company_profile_reference": profile_ref,
    }


def build_draft_sections(
    metadata: Dict[str, str],
    requirements: List[RequirementItem],
    matrix: List[ComplianceRow],
    company_profile: str,
    past_performance: List[str],
    company_name: str | None = None,
) -> Dict[str, str]:
    prompt = _build_prompt(
        metadata=metadata,
        requirements=requirements,
        matrix=matrix,
        company_name=company_name,
        company_profile=company_profile,
        past_performance=past_performance,
    )

    try:
        llm_output = _generate_with_llm(prompt)
    except Exception:
        llm_output = None

    if not llm_output:
        return _fallback_sections(
            metadata, requirements, matrix, company_profile, past_performance
        )

    parsed = _split_sections(llm_output)
    if parsed.get("executive_summary") and parsed.get("technical_approach"):
        parsed["company_profile_reference"] = company_profile[:1800]
        return parsed

    return _fallback_sections(
        metadata, requirements, matrix, company_profile, past_performance
    )
