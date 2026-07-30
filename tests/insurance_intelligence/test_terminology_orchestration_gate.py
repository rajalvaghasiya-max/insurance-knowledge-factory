from datetime import date

import pytest

from insurance_intelligence.orchestration.star_comprehensive_terminology import (
    build_star_comprehensive_terminology_gate,
)
from insurance_intelligence.orchestration.terminology_gate import (
    TerminologyOrchestrationError,
    TerminologyOrchestrationRequest,
    TerminologyOrchestrationResult,
)


AS_OF = date(2026, 7, 30)
VARIANT = "pv_star_health_star_comprehensive_shahlip26044v092526"


def _request(text: str, **overrides: object) -> TerminologyOrchestrationRequest:
    values = {
        "request_id": "req-terminology-1",
        "text": text,
        "insurer_id": "star_health",
        "product_id": "star_comprehensive",
        "product_variant_id": VARIANT,
    }
    values.update(overrides)
    return TerminologyOrchestrationRequest(**values)


def test_direct_term_produces_ready_canonical_handoff() -> None:
    result = build_star_comprehensive_terminology_gate().evaluate(
        _request("Co-payment"), as_of=AS_OF
    )

    assert result.status == "READY"
    assert result.may_advance is True
    assert result.reason_codes == ()
    assert result.canonical_context["canonical_concept_family_id"] == (
        "health:cost_sharing:copayment"
    )
    assert result.canonical_context["canonical_concept_name"] == "Copayment"
    assert result.canonical_context["behaviour_signature_id"] == (
        "ga_star_comprehensive_entry_age_61_conditional_copayment_v1"
    )
    assert result.canonical_context["terminology_relationship"] == "EXACT_EQUIVALENT"


def test_exact_alias_produces_same_governed_handoff() -> None:
    result = build_star_comprehensive_terminology_gate().evaluate(
        _request("Copay"), as_of=AS_OF
    )

    assert result.status == "READY"
    assert result.canonical_context["terminology_display_name"] == "Co-payment"
    assert result.canonical_context["product_term_implementation_id"].startswith(
        "implementation:star_health:star_comprehensive"
    )


def test_missing_context_blocks_downstream_progress() -> None:
    result = build_star_comprehensive_terminology_gate().evaluate(
        _request("Copay", product_variant_id=None), as_of=AS_OF
    )

    assert result.status == "BLOCKED"
    assert result.may_advance is False
    assert result.reason_codes == ("MISSING_REQUIRED_PRODUCT_CONTEXT",)
    assert result.missing_context == ("product_variant_id",)
    assert result.canonical_context == {}
    assert "must not proceed" in result.warnings[0]


def test_unknown_text_blocks_without_canonical_context() -> None:
    result = build_star_comprehensive_terminology_gate().evaluate(
        _request("co/pay"), as_of=AS_OF
    )

    assert result.status == "BLOCKED"
    assert result.reason_codes == ("NO_GOVERNED_TERM_OR_ALIAS_MATCH",)
    assert result.canonical_context == {}


def test_wrong_product_context_blocks_without_guessing() -> None:
    result = build_star_comprehensive_terminology_gate().evaluate(
        _request("Copay", product_id="another_product"), as_of=AS_OF
    )

    assert result.status == "BLOCKED"
    assert result.reason_codes == ("NO_GOVERNED_MATCH_FOR_CONTEXT",)
    assert result.candidate_term_ids == (
        "term:star_health:star_comprehensive:copayment",
    )


def test_ready_context_is_immutable() -> None:
    result = build_star_comprehensive_terminology_gate().evaluate(
        _request("Co payment"), as_of=AS_OF
    )

    with pytest.raises(TypeError):
        result.canonical_context["canonical_concept_name"] = "Changed"


def test_ready_result_requires_complete_handoff_contract() -> None:
    with pytest.raises(TerminologyOrchestrationError):
        TerminologyOrchestrationResult(
            request_id="req-invalid-ready",
            status="READY",
            canonical_context={"canonical_concept_family_id": "health:test"},
        )


def test_blocked_result_requires_reason_codes() -> None:
    with pytest.raises(TerminologyOrchestrationError):
        TerminologyOrchestrationResult(
            request_id="req-invalid-blocked",
            status="BLOCKED",
            canonical_context={},
        )
