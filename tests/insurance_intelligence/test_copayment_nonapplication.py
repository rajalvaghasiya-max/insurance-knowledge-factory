import json
from pathlib import Path

import pytest

from factory_core.canonical.copayment_nonapplication_binding import (
    CopaymentNonapplicationBinding,
    CopaymentNonapplicationBindingError,
)
from insurance_intelligence.benefits.copayment_nonapplication import (
    ConditionalCopaymentNonapplication,
    CopaymentNonapplicationContractError,
)
from insurance_intelligence.rule_certification.copayment_nonapplication import (
    build_copayment_nonapplication_certification_case,
    run_copayment_nonapplication_certification_case,
)


def _write_synthetic_repo(root: Path) -> Path:
    registration_path = root / "knowledge/registration.json"
    bundle_path = root / "knowledge/bundle.json"
    spec_path = root / "docs/nonapplication_spec.json"
    registration_path.parent.mkdir(parents=True)
    spec_path.parent.mkdir(parents=True)

    registration = {
        "registration_status": "source_registered_evidence_review_required",
        "document": {
            "document_id": "synthetic_policy_wording_v1",
            "document_version_id": "v1",
            "document_type": "policy_wording",
            "storage_locator": "archive/synthetic_policy.pdf",
            "content_sha256": "a" * 64,
        },
        "evidence_review": {
            "candidates": [
                {
                    "candidate_id": "candidate_page_44",
                    "source_page": 44,
                    "source_char_range": {"start": 100, "end": 200},
                    "text_sha256": "b" * 64,
                    "excerpt": "No co-payment shall apply if an Insured Person from a lower tier avails treatment in a higher tier.",
                }
            ]
        },
    }
    registration_path.write_text(json.dumps(registration), encoding="utf-8")

    bundle = {
        "registration_type": "generic_source_registration_bundle_v1",
        "product_context": {
            "insurer_id": "synthetic_insurer",
            "product_id": "synthetic_product",
            "product_display_name": "Synthetic Product",
            "source_scope": "reusable_generic",
        },
        "sources": [
            {
                "document_id": "synthetic_policy_wording_v1",
                "document_version_id": "v1",
                "authority_role": "primary_legal",
                "registration_output_path": "knowledge/registration.json",
            }
        ],
    }
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    spec = {
        "schema_version": "1.0",
        "binding_type": "copayment_nonapplication_binding_v1",
        "reviewed_by_human": True,
        "generic_source_bundle_path": "knowledge/bundle.json",
        "rules": [
            {
                "rule_id": "synthetic_higher_tier_no_copayment",
                "semantic_key": "copayment.tier.nonapplication",
                "reviewed_statement": "No co-payment shall apply if an Insured Person from a lower tier avails treatment in a higher tier.",
                "trigger_condition": "Insured Person from a lower tier avails treatment in a higher tier.",
                "applicability_scope": "Cross-tier treatment from a lower policy tier to a higher treatment tier.",
                "evidence_selections": [
                    {
                        "document_id": "synthetic_policy_wording_v1",
                        "candidate_id": "candidate_page_44",
                        "candidate_text_sha256": "b" * 64,
                    }
                ],
            }
        ],
    }
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    return spec_path


def test_nonapplication_contract_requires_evidence() -> None:
    with pytest.raises(CopaymentNonapplicationContractError, match="requires evidence"):
        ConditionalCopaymentNonapplication(
            trigger_condition="lower tier to higher tier treatment",
            applicability_scope="premium tier treatment",
            evidence_reference_ids=(),
        )


def test_binding_preserves_nonapplication_without_manufacturing_zero_percent(tmp_path: Path) -> None:
    spec_path = _write_synthetic_repo(tmp_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    result = CopaymentNonapplicationBinding().bind(spec=spec, repository_root=tmp_path)

    assert result.manifest["binding_status"] == "reviewed_copayment_nonapplication_bound_not_published"
    rule = result.manifest["rules"][0]
    assert rule["rule_type"] == "conditional_copayment_nonapplication_rule"
    assert rule["semantic"]["affected_cost_share"] == "COPAYMENT"
    assert rule["semantic"]["effect"] == "DOES_NOT_APPLY"
    serialized = json.dumps(result.manifest)
    assert "0%" not in serialized
    assert '"percentage"' not in serialized
    assert rule["evidence"][0]["candidate_id"] == "candidate_page_44"


def test_binding_rejects_percentage_encoding_of_nonapplication(tmp_path: Path) -> None:
    spec_path = _write_synthetic_repo(tmp_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["rules"][0]["reviewed_statement"] = (
        "0% co-payment does not apply if an Insured Person moves to a higher tier."
    )
    with pytest.raises(CopaymentNonapplicationBindingError, match="must not encode"):
        CopaymentNonapplicationBinding().bind(spec=spec, repository_root=tmp_path)


def test_nonapplication_certification_is_complete_and_page_bound(tmp_path: Path) -> None:
    _write_synthetic_repo(tmp_path)
    case = build_copayment_nonapplication_certification_case(
        binding_spec_path="docs/nonapplication_spec.json",
        repository_root=tmp_path,
    )
    result = run_copayment_nonapplication_certification_case(case)

    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True
    assert result.failures == ()
    assert {check.component_id for check in result.component_checks} == {
        "affected_cost_share",
        "nonapplication_effect",
        "trigger_condition",
        "applicability_scope",
    }
    assert {package.page for package in case.evidence_output.evidence_packages} == {44}
    assert {
        package.retrieval_basis[-1]
        for package in case.evidence_output.evidence_packages
    } == {"candidate_page_44"}
