from dataclasses import replace
from pathlib import Path

from insurance_intelligence.authoritative_publication.governed import (
    build_governed_authoritative_publication,
)
from insurance_intelligence.evidence.published_materialization import (
    PublishedEvidenceSource,
    materialize_published_requirement,
)
from insurance_intelligence.publication_decision.governed import (
    build_governed_publication_context,
)
from insurance_intelligence.reasoning.rules import (
    build_rule_input,
    conditional_copayment_obligation,
)


ROOT = Path(__file__).resolve().parents[2]
PUBLICATION_SPEC_PATH = (
    "knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/v2/"
    "governance/bajaj_my_health_care_v2_lab_radiology_copay_publication_spec.json"
)
REQUIREMENT_ID = "requirement:bajaj-structured-copay-reasoning"
SUBJECT_REFERENCE = "product:bajaj_allianz_general:my_health_care"
NEUTRAL_PROSE = "Governed structured conditional copayment evidence."


def _published_packages():
    publication = build_governed_authoritative_publication(
        publication_spec_path=PUBLICATION_SPEC_PATH,
        repository_root=ROOT,
    )
    _, case, _ = build_governed_publication_context(
        publication_spec_path=PUBLICATION_SPEC_PATH,
        repository_root=ROOT,
    )
    packages, _ = materialize_published_requirement(
        source=PublishedEvidenceSource(
            publication=publication,
            certified_evidence=case.evidence_output,
        ),
        requirement_id=REQUIREMENT_ID,
        subject_reference=SUBJECT_REFERENCE,
    )
    return packages


def _attribute_values(packages) -> dict[str, str]:
    values: dict[str, str] = {}
    for package in packages:
        for attribute in package.semantic_attributes:
            values[attribute.key] = attribute.value
    return values


def _reason(packages):
    return conditional_copayment_obligation(
        build_rule_input(
            requirement_id=REQUIREMENT_ID,
            evidence=packages,
            approved_context={},
            scope="bajaj_allianz_general:my_health_care",
        )
    )[0]


def test_published_bajaj_structured_semantics_drive_reasoning_without_parseable_prose() -> None:
    packages = _published_packages()
    attributes = _attribute_values(packages)

    assert attributes["rate"] == "20% of the admissible claim amount"
    assert "not pre-approved" in attributes["trigger_condition"]
    assert attributes["applicability_scope"] == (
        "For Doctor Prescribed Investigations - Pathology & Radiology"
    )

    neutralized = tuple(
        replace(
            package,
            claim=NEUTRAL_PROSE,
            source_excerpt=NEUTRAL_PROSE,
        )
        for package in packages
    )
    finding = _reason(neutralized)

    assert finding.object_or_effect == "20% of the admissible claim amount"
    assert "not pre-approved" in (finding.trigger or "")
    assert finding.applicability_scope == (
        "For Doctor Prescribed Investigations - Pathology & Radiology"
    )
    assert set(finding.evidence_ids) == {
        package.evidence_id for package in packages if package.semantic_attributes
    }


def test_structured_rate_has_precedence_over_conflicting_legacy_prose() -> None:
    packages = _published_packages()
    perturbed = []
    for package in packages:
        semantic_attributes = tuple(
            replace(attribute, value="15% of the admissible claim amount")
            if attribute.key == "rate"
            else attribute
            for attribute in package.semantic_attributes
        )
        perturbed.append(replace(package, semantic_attributes=semantic_attributes))

    finding = _reason(tuple(perturbed))

    assert finding.object_or_effect == "15% of the admissible claim amount"
    assert "20%" not in finding.object_or_effect
    assert "not pre-approved" in (finding.trigger or "")
