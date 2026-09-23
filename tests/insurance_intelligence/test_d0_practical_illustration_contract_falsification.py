from __future__ import annotations

from insurance_intelligence.contracts.explanation import build_section


def test_practical_illustration_supports_dual_governed_lineage() -> None:
    section = build_section(
        section_id="illustration-1",
        section_type="PRACTICAL_ILLUSTRATION",
        status="DRAFTED",
        text="Illustrative governed product scenario.",
        approved_finding_ids=("finding-duration",),
        evidence_ids=("evidence-duration",),
        education_publication_ids=("education-ped",),
    )

    assert section.section_type == "PRACTICAL_ILLUSTRATION"
    assert section.approved_finding_ids == ("finding-duration",)
    assert section.evidence_ids == ("evidence-duration",)
    assert section.education_publication_ids == ("education-ped",)
