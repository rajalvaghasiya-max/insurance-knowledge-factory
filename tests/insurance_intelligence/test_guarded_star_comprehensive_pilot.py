from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from insurance_intelligence.contracts.rendering_exit import build_candidate
from insurance_intelligence.orchestration import guarded_star_comprehensive_pilot as guarded
from insurance_intelligence.orchestration.guarded_star_comprehensive_pilot import (
    CURRENTNESS_LIMITATION_TEXT,
    GuardedStarComprehensivePilotError,
    run_guarded_star_comprehensive_copay_pilot,
)


def _response_registry(root: Path) -> Path:
    base = root / "star_health_star_comprehensive"
    binding_dir = base / "generic_legal_condition_binding"
    projection_dir = base / "generic_legal_condition_canonical_projection"
    registration_dir = base / "generic_source_registration"
    source_dir = base / "source"
    for item in (binding_dir, projection_dir, registration_dir, source_dir):
        item.mkdir(parents=True, exist_ok=True)

    source = source_dir / "policy_wording.txt"
    source.write_text(
        "10% co-payment applies under the documented entry-age condition.",
        encoding="utf-8",
    )
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    candidate_hash = hashlib.sha256(b"10% co-payment").hexdigest()

    binding = binding_dir / "star_health_star_comprehensive_conditional_copayment.json"
    binding.write_text(
        json.dumps(
            {
                "product_context": {"product_display_name": "Star Comprehensive"},
                "assertions": [
                    {
                        "reviewed_statement": (
                            "A 10% co-payment applies under the documented entry-age condition."
                        ),
                        "evidence": [
                            {
                                "candidate_id": "candidate-1",
                                "document_id": "star-policy-wording",
                                "document_version_id": "star-policy-wording-v1",
                                "source_page": 39,
                                "candidate_text_sha256": candidate_hash,
                            }
                        ],
                    }
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    binding_hash = hashlib.sha256(binding.read_bytes()).hexdigest()

    projection = projection_dir / "star_health_star_comprehensive_conditional_copayment.canonical.json"
    projection.write_text(
        json.dumps(
            {
                "projection_report": {"binding_manifest_sha256": binding_hash},
                "canonical_bundle": {
                    "source_documents": [{"document_type": "POLICY_WORDING"}],
                    "document_versions": [
                        {
                            "storage_locator": str(source),
                            "content_sha256": source_hash,
                            "effective_from": "2025-01-01",
                            "effective_to": None,
                        }
                    ],
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (registration_dir / "policy_wording_registration.json").write_text(
        json.dumps(
            {
                "evidence_review": {
                    "candidates": [
                        {
                            "candidate_id": "candidate-1",
                            "excerpt": "10% co-payment applies.",
                        }
                    ]
                }
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return root


def _run(tmp_path: Path, *, question: str = "Will this co-payment apply to my treatment?", **kwargs):
    response_root = _response_registry(tmp_path / "response_registry")
    return run_guarded_star_comprehensive_copay_pilot(
        request_id="guarded-response-1",
        question=question,
        repository_root=response_root,
        knowledge_snapshot_id="snapshot-guarded-1",
        customer_context={"trigger_status": "CONFIRMED"},
        **kwargs,
    )


def test_real_star_identity_and_all_guard_boundaries_are_exercised(tmp_path: Path) -> None:
    result = _run(tmp_path)

    assert result.guard_status == "GUARDED"
    assert result.authority.authority_class == "ASSERTIVE"
    assert result.intent.primary_intent == "CLAIM_SCENARIO"
    assert result.reconciliation.reconciliation_status == "CONSISTENT_ASSERTIVE"
    assert result.identity_resolution.status == "RESOLVED"
    assert result.identity_resolution.selected_entity.canonical_entity_id == "star_health:star_comprehensive"
    assert result.identity_resolution.selected_entity.uin == "SHAHLIP26044V092526"
    assert result.identity_record_ref.endswith(
        "docs/architecture/star_health_star_comprehensive_product_identity_reference_spec.json"
    )
    assert len(result.identity_record_hash) == 64
    assert result.instance_sufficiency.outcome == "PASS"
    assert result.instance_sufficiency.planning_authorized is True
    assert result.evidence_enforcement.outcome == "EVIDENCE_RESOLUTION_AUTHORIZED"
    assert result.evidence_enforcement.evidence_resolver_called is True
    assert result.authority_enforcement.enforcement_outcome == "DELEGATED_TO_DECISION_GATE"
    assert result.authority_enforcement.decision_gate_called is True
    assert result.render_conformance.outcome == "PASS"
    assert result.temporal_status == "compatibility_unverified"
    assert CURRENTNESS_LIMITATION_TEXT in result.limitations
    assert any(
        section.section_type == "LIMITATION" and CURRENTNESS_LIMITATION_TEXT in section.text
        for section in result.response.sections
    )


def test_blank_identity_attestation_blocks_before_evidence_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = guarded._evaluate_instance_sufficiency

    def without_attestation(*, request_id, reconciliation, context, attestations):
        return original(
            request_id=request_id,
            reconciliation=reconciliation,
            context=context,
            attestations=(),
        )

    monkeypatch.setattr(guarded, "_evaluate_instance_sufficiency", without_attestation)

    with pytest.raises(GuardedStarComprehensivePilotError, match="instance sufficiency blocked"):
        _run(tmp_path)


def test_advisory_or_mixed_request_is_withheld_by_authority_enforced_decision(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        GuardedStarComprehensivePilotError,
        match="authority enforcement withheld the ordinary answer path",
    ):
        _run(
            tmp_path,
            question="What should I do if this co-payment will apply to my treatment?",
        )


def test_rendering_exit_failure_blocks_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def empty_candidate(envelope):
        return build_candidate(
            request_id=envelope.request_id,
            response_id=envelope.response_id,
            units=(),
        )

    monkeypatch.setattr(guarded, "_exact_render_candidate", empty_candidate)

    with pytest.raises(GuardedStarComprehensivePilotError, match="rendering exit safety blocked release"):
        _run(tmp_path)


def test_explain_copayment_remains_a_real_classified_request(tmp_path: Path) -> None:
    result = _run(tmp_path, question="Explain co-payment")
    assert result.authority.authority_class == "ASSERTIVE"
    assert result.intent.primary_intent == "TERM_EXPLANATION"
    assert result.guard_status == "GUARDED"
