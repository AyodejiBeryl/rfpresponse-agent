from __future__ import annotations

from app.services.parser import extract_metadata, extract_requirements
from app.services.matrix import build_compliance_matrix, build_gaps


def test_extract_metadata_solicitation_number():
    text = "Solicitation No: W911NF-24-R-0001 for IT Services. Due Date: March 15, 2026. NAICS: 541512"
    meta = extract_metadata(text)
    assert meta["solicitation_number"] == "W911NF-24-R-0001"
    assert meta["naics"] == "541512"


def test_extract_metadata_not_found():
    text = "This is a general document with no specific solicitation data."
    meta = extract_metadata(text)
    assert meta["solicitation_number"] == "Not found"


def test_extract_requirements():
    text = (
        "The contractor shall provide 24/7 monitoring of all network infrastructure. "
        "The vendor must maintain SOC 2 Type II compliance at all times. "
        "This is just some general informational text about the agency."
    )
    reqs = extract_requirements(text)
    assert len(reqs) >= 2
    assert any("shall" in r.requirement_text.lower() or "must" in r.requirement_text.lower() for r in reqs)


def test_extract_requirements_no_keywords():
    text = "Short text."
    reqs = extract_requirements(text)
    assert len(reqs) == 1
    assert reqs[0].priority == "informational"


def test_compliance_matrix_met():
    from app.schemas.analysis import RequirementItem
    reqs = [
        RequirementItem(
            id="REQ-001",
            section="Test",
            requirement_text="The contractor shall provide cloud migration services and infrastructure management",
            priority="must",
            source_reference="test",
        )
    ]
    matrix = build_compliance_matrix(
        requirements=reqs,
        company_profile="We provide cloud migration services, infrastructure management, DevOps, and monitoring solutions.",
        past_performance=["Completed cloud migration for DoD agency"],
    )
    assert len(matrix) == 1
    assert matrix[0].status in ("met", "partial")


def test_compliance_matrix_missing():
    from app.schemas.analysis import RequirementItem
    reqs = [
        RequirementItem(
            id="REQ-001",
            section="Test",
            requirement_text="The contractor shall provide quantum computing expertise",
            priority="must",
            source_reference="test",
        )
    ]
    matrix = build_compliance_matrix(
        requirements=reqs,
        company_profile="We are a small IT consulting firm specializing in web development.",
        past_performance=[],
    )
    assert len(matrix) == 1
    assert matrix[0].status == "missing"


def test_build_gaps():
    from app.schemas.analysis import ComplianceRow
    matrix = [
        ComplianceRow(requirement_id="REQ-001", status="met", evidence="ok", notes=""),
        ComplianceRow(requirement_id="REQ-002", status="missing", evidence="", notes="Needs input"),
        ComplianceRow(requirement_id="REQ-003", status="partial", evidence="", notes="More detail needed"),
    ]
    gaps = build_gaps(matrix)
    assert len(gaps) == 2
    assert any("REQ-002" in g for g in gaps)
