"""MO-009: execute the real, unmodified generic legal-condition binding
contract against the normalized Star Comprehensive copay specification.

Environment constraint (consistent with every prior milestone in this
engagement): the approved source PDF
(archive/raw_documents/star_health/star_comprehensive_policy_wording_2025.pdf)
is gitignored and not present in this checkout, so the real
GenericSourceRegistration -> PilotSourceRegistration extraction chain
(which reads actual PDF bytes to produce page-level text candidates)
cannot run here. Real execution against the committed repository state
fails closed at exactly the missing-bundle boundary -- proven below.

To prove the generic binding contract genuinely executes end-to-end
for Star (not merely that it rejects things), the success-path tests
below construct an isolated (tmp_path, never committed) registration
scaffold. The one evidence value that matters -- candidate_text_sha256
-- is copied verbatim from the CTO-approved, already-committed binding
specification (not invented). Positional metadata that only genuine
PDF extraction could supply (source_char_range) is left explicitly
None rather than fabricated; source_page is taken directly from the
candidate_id's own naming ("candidate_page_39" -> 39), not invented
separately. No new evidence fact is created anywhere in this file.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from factory_core.canonical.generic_legal_condition_binding import (
    GenericLegalConditionBinding,
    GenericLegalConditionBindingError,
)

BINDING_SPEC = "docs/architecture/star_health_star_comprehensive_conditional_copayment_binding_spec.json"
BUNDLE_OUTPUT_RELATIVE = (
    "knowledge/factory/registry_backed/star_health_star_comprehensive/"
    "generic_source_registration/star_health_star_comprehensive_generic_source_bundle.json"
)
REGISTRATION_OUTPUT_RELATIVE = (
    "knowledge/factory/registry_backed/star_health_star_comprehensive/"
    "generic_source_registration/policy_wording_registration.json"
)

APPROVED_ENTITY_ID = "star_health:star_comprehensive"
APPROVED_DOCUMENT_ID = "star_health_star_comprehensive_policy_wording_v1"
APPROVED_SOURCE_SHA256 = "b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f"
APPROVED_CANDIDATE_TEXT_SHA256 = "ea3aa9a64bd799fbdcc52bdebb48a5b6917c90673451cf84230005506bb09594"


def _binding_spec() -> dict:
    return json.loads(Path(BINDING_SPEC).read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _registration_record(*, authority_role: str = "primary_legal", document_id: str = APPROVED_DOCUMENT_ID) -> dict:
    return {
        "registration_status": "source_registered_evidence_review_required",
        "document": {
            "document_id": document_id,
            "document_version_id": APPROVED_SOURCE_SHA256,
        },
        "evidence_review": {
            "candidates": [
                {
                    "candidate_id": "candidate_page_39",
                    "text_sha256": APPROVED_CANDIDATE_TEXT_SHA256,
                    "source_page": 39,
                    "source_char_range": {"start": None, "end": None},
                }
            ]
        },
    }


def _bundle(*, authority_role: str = "primary_legal", document_id: str = APPROVED_DOCUMENT_ID) -> dict:
    return {
        "registration_type": "generic_source_registration_bundle_v1",
        "product_context": {
            "insurer_id": "star_health",
            "product_id": "star_comprehensive",
            "product_display_name": "Star Comprehensive Insurance Policy",
            "source_scope": "reusable_generic",
        },
        "sources": [
            {
                "document_id": document_id,
                "authority_role": authority_role,
                "registration_output_path": REGISTRATION_OUTPUT_RELATIVE,
                "document_version_id": APPROVED_SOURCE_SHA256,
            }
        ],
    }


def _seed_valid_bundle(root: Path, *, authority_role: str = "primary_legal", document_id: str = APPROVED_DOCUMENT_ID) -> None:
    _write_json(root / BUNDLE_OUTPUT_RELATIVE, _bundle(authority_role=authority_role, document_id=document_id))
    _write_json(root / REGISTRATION_OUTPUT_RELATIVE, _registration_record(authority_role=authority_role, document_id=document_id))


def _copy_spec_into(root: Path) -> Path:
    import shutil

    destination = root / BINDING_SPEC
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(BINDING_SPEC), destination)
    return destination


# --- Real execution against the committed repository -----------------------

def test_real_execution_fails_closed_on_missing_source_bundle():
    """Against the actual committed repository (no source PDF present),
    the real, unmodified contract must fail closed at exactly the missing
    upstream bundle -- never at a spec-shape error."""
    with pytest.raises((GenericLegalConditionBindingError, FileNotFoundError)) as excinfo:
        GenericLegalConditionBinding().bind_from_spec_file(spec_path=BINDING_SPEC, repository_root=".")
    message = str(excinfo.value)
    assert "generic_source_bundle was not found" in message
    assert "star_health_star_comprehensive_generic_source_bundle.json" in message


# --- Failure-boundary tests (isolated, tmp_path) ----------------------------

def test_wrong_document_id_fails_closed(tmp_path):
    spec_path = _copy_spec_into(tmp_path)
    _seed_valid_bundle(tmp_path, document_id="star_health_star_comprehensive_policy_wording_WRONG")
    with pytest.raises(GenericLegalConditionBindingError, match="unregistered source"):
        GenericLegalConditionBinding().bind_from_spec_file(spec_path=spec_path, repository_root=tmp_path)


def test_wrong_source_sha_fails_closed(tmp_path):
    spec_path = _copy_spec_into(tmp_path)
    _write_json(tmp_path / BUNDLE_OUTPUT_RELATIVE, _bundle())
    bad_registration = _registration_record()
    bad_registration["document"]["document_version_id"] = "0" * 64
    _write_json(tmp_path / REGISTRATION_OUTPUT_RELATIVE, bad_registration)
    with pytest.raises(GenericLegalConditionBindingError, match="document_version_id mismatch"):
        GenericLegalConditionBinding().bind_from_spec_file(spec_path=spec_path, repository_root=tmp_path)


def test_missing_source_bundle_fails_closed(tmp_path):
    spec_path = _copy_spec_into(tmp_path)
    # Deliberately do not seed anything under knowledge/factory/.
    with pytest.raises((GenericLegalConditionBindingError, FileNotFoundError), match="generic_source_bundle was not found"):
        GenericLegalConditionBinding().bind_from_spec_file(spec_path=spec_path, repository_root=tmp_path)


def test_unsupported_entity_binding_fails_closed(tmp_path):
    """'Unsupported entity binding' is exercised here as a discovery-only
    source attempting to establish a reusable legal assertion -- the
    contract's own rejection for a source role insufficient to bind a
    product-level legal condition."""
    spec_path = _copy_spec_into(tmp_path)
    _seed_valid_bundle(tmp_path, authority_role="discovery_only")
    with pytest.raises(GenericLegalConditionBindingError, match="discovery-only sources cannot bind"):
        GenericLegalConditionBinding().bind_from_spec_file(spec_path=spec_path, repository_root=tmp_path)


# --- Success path (isolated, tmp_path, real contract, real approved hash) --

def test_valid_governed_bundle_succeeds(tmp_path):
    spec_path = _copy_spec_into(tmp_path)
    _seed_valid_bundle(tmp_path)
    result = GenericLegalConditionBinding().bind_from_spec_file(spec_path=spec_path, repository_root=tmp_path)

    assert result.manifest["product_context"]["insurer_id"] == "star_health"
    assert result.manifest["product_context"]["product_id"] == "star_comprehensive"

    assertion = result.manifest["assertions"][0]
    assert assertion["assertion_type"] == "conditional_copayment_rule"
    assert "age at entry is 61 years or above" in assertion["reviewed_statement"]
    assert "before attaining 61 years of age and renewed continuously without a break" in assertion["reviewed_statement"]
    assert "Sections II.1, II.2" in assertion["reviewed_statement"]
    assert assertion["evidence"][0]["document_id"] == APPROVED_DOCUMENT_ID
    assert assertion["evidence"][0]["document_version_id"] == APPROVED_SOURCE_SHA256
    assert assertion["evidence"][0]["candidate_text_sha256"] == APPROVED_CANDIDATE_TEXT_SHA256


def test_binding_remains_unpublished(tmp_path):
    spec_path = _copy_spec_into(tmp_path)
    _seed_valid_bundle(tmp_path)
    result = GenericLegalConditionBinding().bind_from_spec_file(spec_path=spec_path, repository_root=tmp_path)
    assert result.manifest["binding_status"] == "reviewed_generic_legal_conditions_bound_not_published"
    assert result.manifest["assertions"][0]["publication_status"] == "bound_not_published"


def test_current_entitlement_remains_blocked(tmp_path):
    """The binding manifest's own guardrails must continue to disclaim
    entitlement -- this stage never approves current applicability."""
    spec_path = _copy_spec_into(tmp_path)
    _seed_valid_bundle(tmp_path)
    result = GenericLegalConditionBinding().bind_from_spec_file(spec_path=spec_path, repository_root=tmp_path)
    guardrail_text = " ".join(result.manifest["guardrails"]).lower()
    assert "entitlement" in guardrail_text
    assert "remains blocked" in guardrail_text or "blocked" in guardrail_text


def test_second_execution_is_semantically_deterministic(tmp_path):
    spec_path = _copy_spec_into(tmp_path)
    _seed_valid_bundle(tmp_path)
    result_a = GenericLegalConditionBinding().bind_from_spec_file(spec_path=spec_path, repository_root=tmp_path)
    result_b = GenericLegalConditionBinding().bind_from_spec_file(spec_path=spec_path, repository_root=tmp_path)

    a, b = dict(result_a.manifest), dict(result_b.manifest)
    differing = {k for k in set(a) | set(b) if a.get(k) != b.get(k)}
    # bound_at is a wall-clock timestamp and is expected to differ; no
    # other field may differ between two runs of the same governed input.
    assert differing <= {"bound_at"}, f"non-timestamp fields differ between runs: {differing}"
    assert a["assertions"] == b["assertions"]
    assert a["generic_source_bundle_sha256"] == b["generic_source_bundle_sha256"]
