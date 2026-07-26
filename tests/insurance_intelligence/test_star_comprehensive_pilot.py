from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from insurance_intelligence.orchestration.star_comprehensive_pilot import (
    PRODUCT_REFERENCE,
    TOPIC,
    StarComprehensivePilotError,
    run_star_comprehensive_copay_pilot,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _registry(tmp_path: Path) -> Path:
    root = tmp_path / "registry_backed"
    base = root / "star_health_star_comprehensive"
    binding_dir = base / "generic_legal_condition_binding"
    projection_dir = base / "generic_legal_condition_canonical_projection"
    registration_dir = base / "generic_source_registration"
    source_dir = base / "source"
    for item in (binding_dir, projection_dir, registration_dir, source_dir):
        item.mkdir(parents=True, exist_ok=True)
    source = source_dir / "policy_wording.txt"
    source.write_text("10% co-payment applies when treatment occurs in a non-network city.", encoding="utf-8")
    source_hash = _sha(source)
    candidate_hash = hashlib.sha256(b"10% co-payment").hexdigest()
    binding = binding_dir / "star_health_star_comprehensive_conditional_copayment.json"
    binding.write_text(json.dumps({
        "product_context": {"product_display_name": "Star Comprehensive"},
        "assertions": [{
            "reviewed_statement": "A 10% co-payment applies when treatment occurs in the documented triggering location.",
            "evidence": [{
                "candidate_id": "candidate-1",
                "document_id": "star-policy-wording",
                "document_version_id": "star-policy-wording-v1",
                "source_page": 39,
                "candidate_text_sha256": candidate_hash,
            }],
        }],
    }, sort_keys=True), encoding="utf-8")
    binding_hash = _sha(binding)
    projection = projection_dir / "star_health_star_comprehensive_conditional_copayment.canonical.json"
    projection.write_text(json.dumps({
        "projection_report": {"binding_manifest_sha256": binding_hash},
        "canonical_bundle": {
            "source_documents": [{"document_type": "POLICY_WORDING"}],
            "document_versions": [{
                "storage_locator": str(source),
                "content_sha256": source_hash,
                "effective_from": "2025-01-01",
                "effective_to": None,
            }],
        },
    }, sort_keys=True), encoding="utf-8")
    registration = registration_dir / "policy_wording_registration.json"
    registration.write_text(json.dumps({
        "evidence_review": {"candidates": [{"candidate_id": "candidate-1", "excerpt": "10% co-payment applies."}]}
    }, sort_keys=True), encoding="utf-8")
    return root


def _run(tmp_path: Path, **kwargs):
    values = dict(
        request_id="pilot-request-1",
        question="How does co-payment affect me?",
        repository_root=_registry(tmp_path),
        knowledge_snapshot_id="snapshot-star-001",
    )
    values.update(kwargs)
    return run_star_comprehensive_copay_pilot(**values)


def test_real_pilot_uses_star_product_and_topic(tmp_path):
    result = _run(tmp_path)
    assert result.product_reference == PRODUCT_REFERENCE
    assert result.topic == TOPIC


def test_real_registry_evidence_is_resolved(tmp_path):
    result = _run(tmp_path)
    assert result.evidence.resolution_status == "RESOLVED"
    assert result.evidence.evidence_packages[0].document_reference == "star-policy-wording"


def test_real_reasoning_creates_copay_finding(tmp_path):
    result = _run(tmp_path)
    assert any(item.finding_type == "CLAIM_COST_SHARING" for item in result.reasoning.findings)
    assert any("10%" in item.object_or_effect for item in result.reasoning.findings)


def test_general_question_is_approved_with_limitations(tmp_path):
    assert _run(tmp_path).decision.decision == "APPROVED_WITH_LIMITATIONS"


def test_general_question_returns_common_language_response(tmp_path):
    response = _run(tmp_path).response
    assert response.response_status == "ANSWER_WITH_LIMITATIONS"
    assert "10%" in " ".join(item.text for item in response.sections)


def test_response_preserves_condition(tmp_path):
    text = " ".join(item.text for item in _run(tmp_path).response.sections).lower()
    assert "when" in text or "condition" in text


def test_response_preserves_evidence_reference(tmp_path):
    refs = _run(tmp_path).response.evidence_references
    assert refs
    assert refs[0].locator == "page 39"


def test_response_uses_deterministic_fallback_only(tmp_path):
    result = _run(tmp_path)
    assert result.used_llm is False
    assert result.released_response_id == result.response.response_id


def test_case_specific_missing_trigger_asks_clarification(tmp_path):
    result = _run(tmp_path, customer_context={"case_specific_applicability": True})
    assert result.decision.decision == "CLARIFICATION_REQUIRED"
    assert result.response.response_status == "CLARIFICATION_REQUIRED"
    assert result.response.clarification_questions


def test_confirmed_trigger_returns_answer(tmp_path):
    result = _run(tmp_path, customer_context={"trigger_status": "CONFIRMED"})
    assert result.response.response_status in {"ANSWER", "ANSWER_WITH_LIMITATIONS"}


def test_not_triggered_returns_supported_answer(tmp_path):
    result = _run(tmp_path, customer_context={"trigger_status": "NOT_TRIGGERED"})
    assert result.response.response_status in {"ANSWER", "ANSWER_WITH_LIMITATIONS"}


def test_snapshot_identity_is_preserved(tmp_path):
    assert _run(tmp_path).knowledge_snapshot_id == "snapshot-star-001"


def test_request_identity_is_preserved_across_all_stages(tmp_path):
    result = _run(tmp_path)
    assert {result.plan.request_id, result.evidence.request_id, result.reasoning.request_id,
            result.decision.request_id, result.explanation.request_id, result.response.request_id} == {result.request_id}


def test_pilot_id_is_deterministic(tmp_path):
    root = _registry(tmp_path)
    kwargs = dict(request_id="r", question="Explain copay", repository_root=root, knowledge_snapshot_id="s")
    assert run_star_comprehensive_copay_pilot(**kwargs).pilot_id == run_star_comprehensive_copay_pilot(**kwargs).pilot_id


def test_response_id_is_deterministic(tmp_path):
    root = _registry(tmp_path)
    kwargs = dict(request_id="r", question="Explain copay", repository_root=root, knowledge_snapshot_id="s")
    assert run_star_comprehensive_copay_pilot(**kwargs).response.response_id == run_star_comprehensive_copay_pilot(**kwargs).response.response_id


def test_different_snapshot_changes_pilot_identity(tmp_path):
    root = _registry(tmp_path)
    one = run_star_comprehensive_copay_pilot(request_id="r", question="Explain", repository_root=root, knowledge_snapshot_id="s1")
    two = run_star_comprehensive_copay_pilot(request_id="r", question="Explain", repository_root=root, knowledge_snapshot_id="s2")
    assert one.pilot_id != two.pilot_id


def test_result_is_immutable(tmp_path):
    result = _run(tmp_path)
    with pytest.raises(FrozenInstanceError):
        result.used_llm = True  # type: ignore[misc]


def test_input_context_is_not_mutated(tmp_path):
    context = {"trigger_status": "CONFIRMED"}
    _run(tmp_path, customer_context=context)
    assert context == {"trigger_status": "CONFIRMED"}


def test_missing_repository_fails_closed(tmp_path):
    with pytest.raises(StarComprehensivePilotError, match="repository_root"):
        run_star_comprehensive_copay_pilot(request_id="r", question="q", repository_root=tmp_path / "missing", knowledge_snapshot_id="s")


@pytest.mark.parametrize("field,value", [
    ("request_id", ""),
    ("question", ""),
    ("knowledge_snapshot_id", ""),
])
def test_required_text_inputs_are_validated(tmp_path, field, value):
    values = dict(request_id="r", question="q", repository_root=_registry(tmp_path), knowledge_snapshot_id="s")
    values[field] = value
    with pytest.raises(StarComprehensivePilotError):
        run_star_comprehensive_copay_pilot(**values)


def test_failed_lineage_is_not_released(tmp_path):
    root = _registry(tmp_path)
    binding = root / "star_health_star_comprehensive/generic_legal_condition_binding/star_health_star_comprehensive_conditional_copayment.json"
    data = json.loads(binding.read_text())
    data["assertions"][0]["reviewed_statement"] = "changed"
    binding.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
    with pytest.raises(StarComprehensivePilotError, match="not eligible"):
        run_star_comprehensive_copay_pilot(request_id="r", question="q", repository_root=root, knowledge_snapshot_id="s")


def test_limitations_are_deduplicated(tmp_path):
    result = _run(tmp_path)
    assert len(result.limitations) == len(set(result.limitations))


def test_question_is_trimmed(tmp_path):
    assert _run(tmp_path, question="  Explain copay  ").question == "Explain copay"


def test_evidence_label_is_human_readable(tmp_path):
    ref = _run(tmp_path).response.evidence_references[0]
    assert ref.label == "Policy Wording"


def test_pilot_exposes_no_generated_example(tmp_path):
    text = " ".join(item.text for item in _run(tmp_path).response.sections)
    assert "₹" not in text
    assert "1,00,000" not in text


def test_pilot_does_not_crawl_or_build_knowledge(tmp_path):
    result = _run(tmp_path)
    assert not hasattr(result, "discovery")
    assert not hasattr(result, "crawl")


def _included_texts(result):
    return tuple(item.text for item in result.response.sections if item.status == "INCLUDED")


def test_not_triggered_leads_with_direct_no(tmp_path):
    result = _run(tmp_path, customer_context={"trigger_status": "NOT_TRIGGERED"})
    assert result.response.direct_answer.startswith("No.")
    assert "does not apply" in result.response.direct_answer


def test_confirmed_trigger_leads_with_direct_yes(tmp_path):
    result = _run(tmp_path, customer_context={"trigger_status": "CONFIRMED"})
    assert result.response.direct_answer.startswith("Yes.")
    assert "10% co-payment applies" in result.response.direct_answer


def test_general_response_is_conditional_not_case_conclusive(tmp_path):
    result = _run(tmp_path)
    assert result.response.direct_answer.startswith("This policy has a conditional 10% co-payment.")


def test_hardened_response_contains_no_empty_included_sections(tmp_path):
    for status in (None, "CONFIRMED", "NOT_TRIGGERED"):
        context = {} if status is None else {"trigger_status": status}
        result = _run(tmp_path, customer_context=context)
        assert all(text.strip() for text in _included_texts(result))


def test_hardened_response_contains_no_duplicated_condition_prefix(tmp_path):
    for status in (None, "CONFIRMED", "NOT_TRIGGERED"):
        context = {} if status is None else {"trigger_status": status}
        text = " ".join(_included_texts(_run(tmp_path, customer_context=context))).lower()
        assert "when where" not in text
        assert "when when" not in text


def test_not_triggered_does_not_claim_condition_applies_to_case(tmp_path):
    result = _run(tmp_path, customer_context={"trigger_status": "NOT_TRIGGERED"})
    assert "the documented trigger is not met for this case" in " ".join(_included_texts(result)).lower()


def test_hardened_section_order_is_deterministic(tmp_path):
    result = _run(tmp_path, customer_context={"trigger_status": "NOT_TRIGGERED"})
    assert tuple(item.section_type for item in result.response.sections) == (
        "DIRECT_ANSWER", "EXPLANATION", "CONDITION", "LIMITATION", "EVIDENCE"
    )
