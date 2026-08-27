from __future__ import annotations

import pytest

from insurance_intelligence.contracts.evidence import EvidenceResolverInput
from insurance_intelligence.contracts.evidence_instance_enforcement import (
    EvidenceInstanceEnforcementError,
    build_input,
    build_output,
)
from insurance_intelligence.contracts.instance_sufficiency import build_output as build_instance_output
from insurance_intelligence.evidence_instance_enforcement import EvidenceInstanceEnforcer


class SpyResolver:
    def __init__(self) -> None:
        self.calls = 0
        self.output = object()

    def resolve(self, data):
        self.calls += 1
        return self.output


def evidence_input(request_id: str = "req-1") -> EvidenceResolverInput:
    # Direct construction isolates this boundary from the already-tested MO-016
    # input validator and planner implementation.
    return EvidenceResolverInput(
        contract_version="1.0",
        request_id=request_id,
        reasoning_plan=None,  # type: ignore[arg-type]
        resolution_context={},
        repository_roots=("knowledge/factory/registry_backed",),
        as_of_date=None,
        strict_mode="STRICT",
    )


def instance(*, outcome="PASS", request_id="req-1"):
    if outcome == "PASS":
        return build_instance_output(
            request_id=request_id,
            outcome="PASS",
            required_instance_keys=(),
            resolved_instance_keys=(),
            unresolved_instance_keys=(),
            planning_authorized=True,
            clarification_required=False,
            basis="test pass",
        )
    if outcome == "OUT_OF_SCOPE":
        return build_instance_output(
            request_id=request_id,
            outcome="OUT_OF_SCOPE",
            required_instance_keys=(),
            resolved_instance_keys=(),
            unresolved_instance_keys=(),
            planning_authorized=False,
            clarification_required=False,
            basis="test out of scope",
        )
    if outcome == "NOT_ANSWERABLE":
        return build_instance_output(
            request_id=request_id,
            outcome="NOT_ANSWERABLE",
            required_instance_keys=("product_reference",),
            resolved_instance_keys=(),
            unresolved_instance_keys=("product_reference",),
            planning_authorized=False,
            clarification_required=False,
            basis="test not answerable",
        )
    return build_instance_output(
        request_id=request_id,
        outcome="CLARIFICATION_REQUIRED",
        required_instance_keys=("product_reference",),
        resolved_instance_keys=(),
        unresolved_instance_keys=("product_reference",),
        planning_authorized=False,
        clarification_required=True,
        basis="test clarification",
    )


def enforce(instance_output, spy=None):
    resolver = spy or SpyResolver()
    result = EvidenceInstanceEnforcer(resolver).resolve(
        build_input(
            request_id="req-1",
            instance_sufficiency=instance_output,
            evidence_input=evidence_input(),
        )
    )
    return result, resolver


def test_pass_delegates_to_existing_evidence_resolver():
    result, spy = enforce(instance())
    assert result.outcome == "EVIDENCE_RESOLUTION_AUTHORIZED"
    assert result.evidence_resolver_called is True
    assert result.evidence_output is spy.output
    assert spy.calls == 1


@pytest.mark.parametrize("outcome", ["CLARIFICATION_REQUIRED", "NOT_ANSWERABLE", "OUT_OF_SCOPE"])
def test_non_pass_instance_sufficiency_never_calls_resolver(outcome):
    result, spy = enforce(instance(outcome=outcome))
    assert result.outcome == "INSTANCE_SUFFICIENCY_BLOCKED"
    assert result.evidence_resolver_called is False
    assert result.evidence_output is None
    assert spy.calls == 0


def test_cross_request_mismatch_is_rejected():
    with pytest.raises(EvidenceInstanceEnforcementError):
        build_input(
            request_id="req-1",
            instance_sufficiency=instance(request_id="other"),
            evidence_input=evidence_input(),
        )


def test_blocked_output_cannot_claim_resolver_was_called():
    with pytest.raises(EvidenceInstanceEnforcementError):
        build_output(
            request_id="req-1",
            outcome="INSTANCE_SUFFICIENCY_BLOCKED",
            evidence_resolver_called=True,
            evidence_output=object(),  # type: ignore[arg-type]
            basis="forged",
        )


def test_authorized_output_requires_resolver_result():
    with pytest.raises(EvidenceInstanceEnforcementError):
        build_output(
            request_id="req-1",
            outcome="EVIDENCE_RESOLUTION_AUTHORIZED",
            evidence_resolver_called=False,
            evidence_output=None,
            basis="forged",
        )


def test_enforcer_rejects_unvalidated_input():
    with pytest.raises(TypeError):
        EvidenceInstanceEnforcer(SpyResolver()).resolve(object())
