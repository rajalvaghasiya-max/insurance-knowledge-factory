"""Bounded tests for MO-008: normalize Star Comprehensive copay governed
specifications. These test governed data only -- no production code,
generic contract, or Star-specific Python is exercised beyond calling
the real, unmodified generic contracts to confirm the normalized specs
fail closed only at genuine missing-upstream-artifact boundaries."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from factory_core.canonical.generic_legal_condition_binding import (
    GenericLegalConditionBinding,
    GenericLegalConditionBindingError,
)
from factory_core.canonical.generic_legal_condition_canonical_projection import (
    GenericLegalConditionCanonicalProjection,
    GenericLegalConditionCanonicalProjectionError,
)
from factory_core.canonical.canonical_publication_decision_gate import (
    CanonicalPublicationDecisionGate,
    CanonicalPublicationDecisionGateError,
)
from factory_core.canonical.canonical_authoritative_publisher import (
    CanonicalAuthoritativePublisher,
    CanonicalAuthoritativePublisherError,
)

BINDING_SPEC = "docs/architecture/star_health_star_comprehensive_conditional_copayment_binding_spec.json"
PROJECTION_SPEC = "docs/architecture/star_health_star_comprehensive_conditional_copayment_canonical_projection_spec.json"
DECISION_SPEC = "docs/architecture/star_health_star_comprehensive_conditional_copayment_publication_decision_spec.json"
PUBLICATION_SPEC = "docs/architecture/star_health_star_comprehensive_conditional_copayment_authoritative_publication_spec.json"
ALL_COPAY_SPECS = (BINDING_SPEC, PROJECTION_SPEC, DECISION_SPEC, PUBLICATION_SPEC)

APPROVED_ENTITY_ID = "star_health:star_comprehensive"
APPROVED_UIN = "SHAHLIP26044V092526"
APPROVED_DOCUMENT_ID = "star_health_star_comprehensive_policy_wording_v1"
APPROVED_SHA256_PREFIX = "b1dbe8fb78646f75"

# Matches "star_comprehensive_" NOT preceded by "star_health_" -- i.e. the
# unapproved short-form prefix this order was asked to eliminate.
_UNAPPROVED_PREFIX_PATTERN = re.compile(r"(?<!star_health_)star_comprehensive_")


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


_PATH_FIELD_NAMES = (
    "generic_source_bundle_path",
    "binding_manifest_path",
    "classification_manifest_path",
    "canonical_projection_path",
    "publication_decision_path",
)


def _extract_path_field_values(obj) -> list[str]:
    """Recursively collect values of known path-bearing fields only. This
    deliberately does not scan assertion_id / semantic_key / other
    semantic identifiers, which are out of this order's explicit scope
    (path references only)."""
    values: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in _PATH_FIELD_NAMES and isinstance(value, str):
                values.append(value)
            values.extend(_extract_path_field_values(value))
    elif isinstance(obj, list):
        for item in obj:
            values.extend(_extract_path_field_values(item))
    return values


def test_no_unapproved_path_prefix_remains_in_any_copay_spec():
    for spec_path in ALL_COPAY_SPECS:
        spec = _load(spec_path)
        for path_value in _extract_path_field_values(spec):
            matches = _UNAPPROVED_PREFIX_PATTERN.findall(path_value)
            assert matches == [], f"{spec_path} field value still contains unapproved prefix: {path_value!r}"


def test_binding_spec_document_id_matches_approved_registration():
    spec = _load(BINDING_SPEC)
    selections = spec["assertions"][0]["evidence_selections"]
    document_ids = {entry["document_id"] for entry in selections}
    assert document_ids == {APPROVED_DOCUMENT_ID}


def test_binding_spec_has_no_prospectus_dependency():
    """Preferred decision: policy wording is the sole authoritative binding
    source; the prospectus is not a required dependency until it is
    separately registered, hash-verified, and approved."""
    spec = _load(BINDING_SPEC)
    selections = spec["assertions"][0]["evidence_selections"]
    assert len(selections) == 1
    for entry in selections:
        assert "prospectus" not in entry["document_id"].lower()


def test_publication_decision_spec_has_no_prospectus_dependency():
    spec = _load(DECISION_SPEC)
    bindings = spec["source_document_bindings"]
    assert len(bindings) == 1
    for entry in bindings:
        assert "prospectus" not in entry["document_id"].lower()
        assert entry["document_id"] == APPROVED_DOCUMENT_ID


def test_publication_decision_spec_document_version_id_uses_approved_sha_prefix():
    spec = _load(DECISION_SPEC)
    entry = spec["source_document_bindings"][0]
    assert entry["document_version_id"].endswith(APPROVED_SHA256_PREFIX)


def test_no_spec_invents_or_asserts_a_prospectus_hash():
    """The order explicitly prohibits treating the previously observed
    prospectus SHA as governed without independent verification, which
    is not possible in this environment. No spec may reference it."""
    unverified_prospectus_sha_fragment = "0404693147bd5202"
    for spec_path in ALL_COPAY_SPECS:
        text = Path(spec_path).read_text(encoding="utf-8").lower()
        assert unverified_prospectus_sha_fragment not in text, f"{spec_path} still references the unverified prospectus hash"


def test_approved_foundation_values_unchanged():
    manifest = json.loads(
        Path("docs/architecture/star_health_star_comprehensive_migration_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["entity_id"] == APPROVED_ENTITY_ID
    assert manifest["expected_source_sha256"] == "b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f"
    identity_spec = _load("docs/architecture/star_health_star_comprehensive_product_identity_reference_spec.json")
    assert identity_spec["product_identity"]["uin"] == APPROVED_UIN


def test_binding_contract_accepts_the_specification_shape():
    """The generic binding contract must either:

    1. execute successfully when the governed upstream bundle exists, or
    2. fail closed only because that upstream bundle is absent.

    A specification-shape, identity, or document_id error is never valid.
    """
    try:
        GenericLegalConditionBinding().bind_from_spec_file(
            spec_path=BINDING_SPEC,
            repository_root=".",
        )
    except (GenericLegalConditionBindingError, FileNotFoundError) as exc:
        message = str(exc)
        assert "generic_source_bundle was not found" in message
        assert "star_health_star_comprehensive_generic_source_bundle.json" in message


def test_canonical_projection_contract_accepts_the_specification_shape():
    try:
        GenericLegalConditionCanonicalProjection().project_from_spec_file(
            spec_path=PROJECTION_SPEC,
            repository_root=".",
        )
    except (GenericLegalConditionCanonicalProjectionError, FileNotFoundError) as exc:
        message = str(exc)
        assert "binding_manifest was not found" in message
        assert "star_health_star_comprehensive_conditional_copayment.json" in message


def test_publication_decision_gate_accepts_the_specification_shape():
    try:
        CanonicalPublicationDecisionGate().decide_from_spec_file(
            spec_path=DECISION_SPEC,
            repository_root=".",
        )
    except (CanonicalPublicationDecisionGateError, FileNotFoundError) as exc:
        message = str(exc)
        assert "canonical_projection was not found" in message
        assert "star_health_star_comprehensive_conditional_copayment.canonical.json" in message


def test_authoritative_publisher_accepts_the_specification_shape():
    try:
        CanonicalAuthoritativePublisher().publish_from_spec_file(
            spec_path=PUBLICATION_SPEC,
            repository_root=".",
        )
    except (CanonicalAuthoritativePublisherError, FileNotFoundError) as exc:
        message = str(exc)
        assert "canonical_projection was not found" in message
        assert "star_health_star_comprehensive_conditional_copayment.canonical.json" in message


def test_no_spec_claims_published_or_current_entitlement_state():
    forbidden_terms = ("published_current", "current_entitlement_approved", "authoritative_current")
    for spec_path in ALL_COPAY_SPECS:
        text = Path(spec_path).read_text(encoding="utf-8").lower()
        for term in forbidden_terms:
            assert term not in text, f"{spec_path} contains a forbidden published/current-entitlement claim: {term}"
