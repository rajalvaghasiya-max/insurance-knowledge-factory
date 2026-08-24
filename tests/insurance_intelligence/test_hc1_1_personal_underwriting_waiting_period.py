from __future__ import annotations

import json
from pathlib import Path

import pytest

from factory_core.canonical.personal_underwriting_waiting_period_binding import (
    PersonalUnderwritingWaitingPeriodBinding,
    PersonalUnderwritingWaitingPeriodBindingError,
)
from insurance_intelligence.benefits.personal_underwriting_waiting_period import (
    PersonalUnderwritingWaitingPeriodError,
    PersonalUnderwritingWaitingPeriodMechanic,
)
from insurance_intelligence.benefits.waiting_period_contracts import (
    WaitingPeriodDurationUnit,
    WaitingPeriodStartBasis,
)
from insurance_intelligence.rule_certification.personal_underwriting_waiting_period import (
    build_personal_underwriting_waiting_period_certification_case,
    run_personal_underwriting_waiting_period_certification_case,
)


CANDIDATE_HASH = "74408d4896f75d5127ed7ef4109bd7229a184c9c2589a6ac5dfe30f653579015"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _fixture_repo(root: Path) -> Path:
    registration_rel = "knowledge/factory/registry_backed/test/v1/generic_source_registration/policy_wording_registration.json"
    bundle_rel = "knowledge/factory/registry_backed/test/v1/generic_source_registration/source_registration_bundle.json"
    _write_json(
        root / registration_rel,
        {
            "registration_status": "source_registered_evidence_review_required",
            "document": {
                "document_id": "test_policy_wording_v1",
                "document_version_id": "test_policy_wording_v1_sha",
                "document_type": "policy_wording",
                "storage_locator": "archive/raw_pdf/test.pdf",
                "content_sha256": "a" * 64,
            },
            "evidence_review": {
                "candidates": [
                    {
                        "candidate_id": "candidate_page_33",
                        "source_page": 33,
                        "text_sha256": CANDIDATE_HASH,
                        "excerpt": "Personal Waiting Period: Conditions specified for an individual insured person may be subject to a waiting period of up to 48 months from inception of the First Policy with us.",
                    }
                ]
            },
        },
    )
    _write_json(
        root / bundle_rel,
        {
            "registration_type": "generic_source_registration_bundle_v1",
            "product_context": {
                "insurer_id": "test_insurer",
                "product_id": "test_product",
                "product_display_name": "Test Product",
                "source_scope": "reusable_generic",
            },
            "sources": [
                {
                    "document_id": "test_policy_wording_v1",
                    "document_version_id": "test_policy_wording_v1_sha",
                    "authority_role": "primary_legal",
                    "registration_output_path": registration_rel,
                }
            ],
        },
    )
    spec_rel = "docs/architecture/test_personal_underwriting_waiting_period_binding_spec.json"
    _write_json(
        root / spec_rel,
        {
            "schema_version": "1.0",
            "binding_type": "personal_underwriting_waiting_period_binding_v1",
            "reviewed_by_human": True,
            "generic_source_bundle_path": bundle_rel,
            "binding_id": "test_personal_wait_v1",
            "evidence_selection": {
                "document_id": "test_policy_wording_v1",
                "candidate_id": "candidate_page_33",
                "candidate_text_sha256": CANDIDATE_HASH,
            },
            "mechanic": {
                "maximum_duration_value": 48,
                "maximum_duration_unit": "MONTHS",
                "start_basis": "INSURED_PERSON_FIRST_COVERAGE",
                "applies_to": ["underwriting-specified conditions for an individual insured person"],
                "instance_resolution_dependency": "Actual conditions and actual duration require authoritative policy-instance underwriting evidence.",
            },
        },
    )
    return root / spec_rel


def test_contract_preserves_maximum_bound_and_instance_guard() -> None:
    mechanic = PersonalUnderwritingWaitingPeriodMechanic(
        maximum_duration_value=48,
        maximum_duration_unit=WaitingPeriodDurationUnit.MONTHS,
        start_basis=WaitingPeriodStartBasis.INSURED_PERSON_FIRST_COVERAGE,
        applies_to=("underwriting-specified conditions",),
        evidence_reference_ids=("doc:candidate:hash",),
        instance_resolution_dependency="Resolve actual conditions and duration from policy-instance evidence.",
    )
    assert mechanic.duration_semantics == "MAXIMUM_BOUND"
    assert mechanic.scope_type == "INSURED_PERSON_CONDITION_SCOPED"
    assert mechanic.instance_resolution_required is True


def test_contract_rejects_turning_personal_wait_into_resolved_instance() -> None:
    with pytest.raises(PersonalUnderwritingWaitingPeriodError, match="must require instance resolution"):
        PersonalUnderwritingWaitingPeriodMechanic(
            maximum_duration_value=48,
            maximum_duration_unit=WaitingPeriodDurationUnit.MONTHS,
            start_basis=WaitingPeriodStartBasis.INSURED_PERSON_FIRST_COVERAGE,
            applies_to=("underwriting-specified conditions",),
            evidence_reference_ids=("doc:candidate:hash",),
            instance_resolution_dependency="instance evidence required",
            instance_resolution_required=False,
        )


def test_binding_preserves_exact_candidate_hash_and_never_resolves_customer_scalar(tmp_path: Path) -> None:
    spec_path = _fixture_repo(tmp_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    manifest = PersonalUnderwritingWaitingPeriodBinding().bind(
        spec=spec,
        repository_root=tmp_path,
        bound_at="2026-08-24T00:00:00+00:00",
    ).manifest
    assert manifest["mechanic"]["maximum_duration_value"] == 48
    assert manifest["mechanic"]["duration_semantics"] == "MAXIMUM_BOUND"
    assert manifest["mechanic"]["instance_resolution_required"] is True
    assert manifest["evidence"]["candidate_text_sha256"] == CANDIDATE_HASH
    assert manifest["publication_status"] == "bound_not_published"


def test_binding_fails_closed_on_candidate_hash_mismatch(tmp_path: Path) -> None:
    spec_path = _fixture_repo(tmp_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["evidence_selection"]["candidate_text_sha256"] = "b" * 64
    with pytest.raises(PersonalUnderwritingWaitingPeriodBindingError, match="candidate text hash mismatch"):
        PersonalUnderwritingWaitingPeriodBinding().bind(spec=spec, repository_root=tmp_path)


def test_certification_says_up_to_and_preserves_instance_dependency(tmp_path: Path) -> None:
    spec_path = _fixture_repo(tmp_path)
    case = build_personal_underwriting_waiting_period_certification_case(
        binding_spec_path=spec_path.relative_to(tmp_path),
        repository_root=tmp_path,
    )
    claims = {package.field_or_topic: package.claim for package in case.evidence_output.evidence_packages}
    assert "up to 48 MONTHS" in claims["WAITING_PERIOD_DURATION"]
    assert "maximum bound" in claims["WAITING_PERIOD_DURATION"]
    assert "policy-instance" in claims["APPLICABILITY_SCOPE"]
    result = run_personal_underwriting_waiting_period_certification_case(case)
    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True


def test_real_reassure_spec_encodes_only_the_governed_maximum_bound() -> None:
    spec = json.loads(
        Path("docs/architecture/niva_bupa_reassure_3_0_personal_underwriting_waiting_period_binding_spec.json").read_text(encoding="utf-8")
    )
    assert spec["mechanic"]["maximum_duration_value"] == 48
    assert spec["mechanic"]["maximum_duration_unit"] == "MONTHS"
    assert spec["evidence_selection"]["candidate_id"] == "candidate_page_33"
    assert spec["evidence_selection"]["candidate_text_sha256"] == CANDIDATE_HASH
    assert spec["governance"]["customer_specific_conditions_resolved"] is False
    assert spec["governance"]["customer_specific_duration_resolved"] is False
