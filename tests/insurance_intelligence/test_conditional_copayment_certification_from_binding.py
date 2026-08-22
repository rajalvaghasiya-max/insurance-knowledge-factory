import hashlib
import json
from pathlib import Path

import pytest

from insurance_intelligence.rule_certification.conditional_copayment import (
    ConditionalCopaymentCertificationError,
    build_conditional_copayment_certification_cases,
    run_conditional_copayment_certification_cases,
)


STATEMENTS = {
    "lab": (
        "For Doctor Prescribed Investigations - Pathology & Radiology, where reimbursement is used "
        "and the reimbursement claim was not pre-approved, a 20% co-payment applies. This assertion "
        "is limited to that investigations cover and does not establish a general product-level co-payment."
    ),
    "international": (
        "For International Cover - Emergency Care only, a mandatory 10% co-payment applies and is "
        "additional to any other co-payment or deductible applicable under the policy. This assertion "
        "is limited to the optional international emergency cover and preserves the stated stacking rule."
    ),
    "voluntary": (
        "If the Voluntary Co-payment option is selected and an In-patient Hospitalization Treatment "
        "claim is admitted, the insured bears 5%, 10%, 15%, or 20% of the eligible claim amount in "
        "proportion to the discount availed. The applicable rate therefore depends on the selected "
        "voluntary co-payment option and must not be inferred without that policy-specific selection context."
    ),
}


def _write(path: Path, data: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(data, indent=2, sort_keys=True) + "\n").encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _fixture(tmp_path: Path) -> str:
    root = tmp_path
    registration_path = Path("knowledge/registration/policy.json")
    bundle_path = Path("knowledge/registration/bundle.json")
    binding_path = Path("knowledge/binding/copay.json")

    candidates = []
    for index, key in enumerate(("lab", "international", "voluntary"), start=1):
        statement = STATEMENTS[key]
        candidates.append(
            {
                "candidate_id": f"candidate_{key}",
                "text_sha256": hashlib.sha256(statement.encode()).hexdigest(),
                "source_page": index,
                "source_char_range": {"start": index * 100, "end": index * 100 + len(statement)},
            }
        )
    registration = {
        "registration_status": "source_registered_evidence_review_required",
        "registered_at": "2026-08-22T00:00:00+00:00",
        "document": {
            "document_id": "policy_wording_v2",
            "document_version_id": "docver_policy_wording_v2",
            "document_type": "policy_wording",
            "content_sha256": "a" * 64,
            "storage_locator": "archive/policy_wording.pdf",
        },
        "evidence_review": {"candidates": candidates},
    }
    _write(root / registration_path, registration)

    bundle = {
        "registration_type": "generic_source_registration_bundle_v1",
        "product_context": {
            "insurer_id": "test_insurer",
            "product_id": "test_product",
            "source_scope": "reusable_generic",
        },
        "sources": [
            {
                "document_id": "policy_wording_v2",
                "document_version_id": "docver_policy_wording_v2",
                "authority_role": "primary_legal",
                "registration_output_path": registration_path.as_posix(),
            }
        ],
    }
    bundle_sha = _write(root / bundle_path, bundle)

    assertions = []
    for key in ("lab", "international", "voluntary"):
        statement = STATEMENTS[key]
        assertions.append(
            {
                "assertion_id": f"assertion_{key}",
                "assertion_type": "conditional_copayment_rule",
                "semantic_key": f"copayment.{key}",
                "reviewed_statement": statement,
                "scope": "reusable_generic_product_legal_condition",
                "publication_status": "bound_not_published",
                "evidence": [
                    {
                        "document_id": "policy_wording_v2",
                        "document_version_id": "docver_policy_wording_v2",
                        "authority_role": "primary_legal",
                        "candidate_id": f"candidate_{key}",
                        "source_page": {"lab": 1, "international": 2, "voluntary": 3}[key],
                        "source_char_range": {
                            "start": {"lab": 100, "international": 200, "voluntary": 300}[key],
                            "end": {"lab": 100, "international": 200, "voluntary": 300}[key] + len(statement),
                        },
                        "candidate_text_sha256": hashlib.sha256(statement.encode()).hexdigest(),
                    }
                ],
            }
        )
    binding = {
        "schema_version": "1.0",
        "binding_type": "generic_legal_condition_binding_v1",
        "binding_status": "reviewed_generic_legal_conditions_bound_not_published",
        "product_context": {
            "insurer_id": "test_insurer",
            "product_id": "test_product",
            "source_scope": "reusable_generic",
        },
        "generic_source_bundle_path": bundle_path.as_posix(),
        "generic_source_bundle_sha256": bundle_sha,
        "assertions": assertions,
        "reviewed_by_human": True,
    }
    _write(root / binding_path, binding)
    return binding_path.as_posix()


def _claims(case) -> dict[str, str]:
    return {
        package.field_or_topic: package.claim
        for package in case.evidence_output.evidence_packages
    }


def test_three_governed_copayment_bindings_certify_through_generic_builder(tmp_path: Path) -> None:
    binding_path = _fixture(tmp_path)
    bundle = build_conditional_copayment_certification_cases(
        binding_manifest_path=binding_path,
        repository_root=tmp_path,
    )

    assert len(bundle.cases) == 3
    results = run_conditional_copayment_certification_cases(bundle)
    assert [result.outcome for result in results] == ["PASS", "PASS", "PASS"]
    assert all(result.actual_completeness_status == "COMPLETE" for result in results)
    assert all(result.actual_explanation_permitted is True for result in results)


def test_certification_preserves_distinct_bajaj_semantics(tmp_path: Path) -> None:
    binding_path = _fixture(tmp_path)
    bundle = build_conditional_copayment_certification_cases(
        binding_manifest_path=binding_path,
        repository_root=tmp_path,
    )
    cases = {case.case_id: case for case in bundle.cases}

    lab = _claims(cases["conditional_copayment:assertion_lab"])
    assert lab["OBLIGATION_VALUE"] == "20% of the admissible claim amount"
    assert "not pre-approved" in lab["TRIGGER_CONDITION"]
    assert "Pathology & Radiology" in lab["APPLICABILITY_SCOPE"]

    international = _claims(cases["conditional_copayment:assertion_international"])
    assert international["OBLIGATION_VALUE"].startswith("10% of the admissible claim amount")
    assert "additional to any other co-payment or deductible" in international["OBLIGATION_VALUE"]
    assert international["APPLICABILITY_SCOPE"] == "For International Cover - Emergency Care only"

    voluntary = _claims(cases["conditional_copayment:assertion_voluntary"])
    for rate in ("5%", "10%", "15%", "20%"):
        assert rate in voluntary["OBLIGATION_VALUE"]
    assert "selected co-payment option" in voluntary["OBLIGATION_VALUE"]
    assert "In-patient Hospitalization Treatment claim is admitted" in voluntary["APPLICABILITY_SCOPE"]


def test_builder_can_select_bounded_assertion_subset(tmp_path: Path) -> None:
    binding_path = _fixture(tmp_path)
    bundle = build_conditional_copayment_certification_cases(
        binding_manifest_path=binding_path,
        repository_root=tmp_path,
        assertion_ids=("assertion_lab",),
    )

    assert [case.case_id for case in bundle.cases] == ["conditional_copayment:assertion_lab"]


def test_builder_fails_closed_for_unknown_requested_assertion(tmp_path: Path) -> None:
    binding_path = _fixture(tmp_path)
    with pytest.raises(ConditionalCopaymentCertificationError, match="were not found"):
        build_conditional_copayment_certification_cases(
            binding_manifest_path=binding_path,
            repository_root=tmp_path,
            assertion_ids=("assertion_missing",),
        )
