import json
from pathlib import Path

from insurance_intelligence.benefits.star_comprehensive import (
    STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = REPOSITORY_ROOT / "docs/architecture/STAR_COMPREHENSIVE_RESTORATION_SOURCE_SHAPE_SPEC.json"


def _spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def _registration(spec: dict) -> dict:
    path = REPOSITORY_ROOT / spec["authoritative_source"]["registration_path"]
    return json.loads(path.read_text(encoding="utf-8"))


def _page_by_number(registration: dict, source_page: int) -> dict:
    return next(
        item
        for item in registration["evidence_review"]["candidates"]
        if item["source_page"] == source_page
    )


def _mechanics() -> dict:
    return {
        item.dimension_id: item
        for item in STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.mechanics
    }


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def test_shape_spec_is_bound_to_the_registered_current_policy_wording() -> None:
    spec = _spec()
    source = spec["authoritative_source"]
    registration = _registration(spec)
    document = registration["document"]

    assert document["document_id"] == source["document_id"]
    assert document["document_version_id"] == source["document_version_id"]
    assert document["content_sha256"] == source["content_sha256"]
    assert _normalized(source["version_marker"]) in _normalized(
        _page_by_number(registration, 13)["excerpt"]
    )

    for expected_page in source["evidence_pages"]:
        actual = _page_by_number(registration, expected_page["source_page"])
        assert actual["text_sha256"] == expected_page["text_sha256"]
        assert _normalized(expected_page["printed_page"]) in _normalized(actual["excerpt"])


def test_every_shape_finding_is_reproducible_from_registered_page_evidence() -> None:
    spec = _spec()
    registration = _registration(spec)

    for finding in spec["mechanics"]:
        page_text = _page_by_number(registration, finding["source_page"])["excerpt"]
        for fragment in finding["required_fragments"]:
            assert _normalized(fragment) in _normalized(page_text), (finding["dimension_id"], fragment)

    boundary = spec["policy_instance_boundary"]
    page_text = _page_by_number(registration, boundary["source_page"])["excerpt"]
    for fragment in boundary["required_fragments"]:
        assert _normalized(fragment) in _normalized(page_text), fragment


def test_explicit_and_composite_mechanics_match_the_existing_implementation() -> None:
    mechanics = _mechanics()

    for finding in _spec()["mechanics"]:
        if finding["implementation_disposition"] in {
            "MATCHES",
            "MATCHES_WITH_IMPORTANT_NOTE_CONTEXT",
        }:
            assert mechanics[finding["dimension_id"]].value == finding["expected_value"]

    assert "first_claim_use" not in mechanics
    assert mechanics["same_hospitalization_use"].value is False
    assert mechanics["subsequent_hospitalization_use"].value is True


def test_unstated_or_ambiguous_mechanics_remain_unmanufactured() -> None:
    mechanics = _mechanics()
    withheld = {
        item["dimension_id"]
        for item in _spec()["mechanics"]
        if item["implementation_disposition"] == "DO_NOT_MANUFACTURE"
    }

    assert withheld == {
        "partial_restoration_use",
        "maximum_liability_per_claim_percentage",
        "utilization_sequence",
    }
    assert withheld.isdisjoint(mechanics)


def test_only_registered_policy_wording_remains_governed_evidence() -> None:
    spec = _spec()
    evidence = STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.evidence_references

    assert len(evidence) == 1
    assert evidence[0].authority_type == "policy_wording"
    assert evidence[0].source_sha256 == spec["authoritative_source"]["content_sha256"]
    assert spec["secondary_source_disposition"] == {
        "source_type": "prospectus",
        "classification": "UNVERIFIED_SECONDARY_EVIDENCE_FAIL_CLOSED",
        "reason": (
            "The approved Star identity record and registered source bundle do not contain a registered, "
            "byte-verifiable prospectus document version. The policy wording alone supports every retained "
            "restoration mechanic."
        ),
        "implementation_action": "REMOVE_FROM_GOVERNED_RESTORATION_EVIDENCE",
    }
    assert all(
        mechanic.evidence_reference_ids == (evidence[0].evidence_reference_id,)
        for mechanic in STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.mechanics
    )


def test_policy_schedule_and_endorsement_boundary_is_preserved() -> None:
    limitations = STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.limitations

    assert any("Policy Schedule and any Endorsement" in item for item in limitations)
    assert _spec()["policy_instance_boundary"]["implementation_action"] == "PRESERVE_AS_LIMITATION"


def test_shape_decision_reuses_existing_contract_without_new_architecture() -> None:
    assert _spec()["decision"] == {
        "existing_generic_concept_fit": "CONFIRMED",
        "new_runtime_architecture": "NOT_AUTHORIZED",
        "new_restoration_implementation": "NOT_REQUIRED",
        "existing_implementation": "REUSE_WITH_BOUNDED_GOVERNANCE_CORRECTION",
        "next_milestone": "Star Comprehensive initial waiting-period current-source manufacturing",
    }
