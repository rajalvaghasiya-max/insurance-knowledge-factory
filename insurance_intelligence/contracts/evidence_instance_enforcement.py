"""Contract binding Instance Sufficiency to MO-016 Evidence Resolution."""
from __future__ import annotations

from dataclasses import dataclass

from insurance_intelligence.contracts.evidence import EvidenceResolverInput, EvidenceResolverOutput
from insurance_intelligence.contracts.instance_sufficiency import InstanceSufficiencyOutput

SUPPORTED_CONTRACT_VERSION = "1.0"
ENFORCEMENT_OUTCOMES = frozenset({"EVIDENCE_RESOLUTION_AUTHORIZED", "INSTANCE_SUFFICIENCY_BLOCKED"})


class EvidenceInstanceEnforcementError(ValueError):
    """Raised when evidence-instance enforcement inputs are invalid."""


@dataclass(frozen=True)
class EvidenceInstanceEnforcementInput:
    contract_version: str
    request_id: str
    instance_sufficiency: InstanceSufficiencyOutput
    evidence_input: EvidenceResolverInput


@dataclass(frozen=True)
class EvidenceInstanceEnforcementOutput:
    contract_version: str
    request_id: str
    outcome: str
    evidence_resolver_called: bool
    evidence_output: EvidenceResolverOutput | None
    basis: str


def build_input(*, request_id: str, instance_sufficiency: InstanceSufficiencyOutput,
                evidence_input: EvidenceResolverInput,
                contract_version: str = SUPPORTED_CONTRACT_VERSION) -> EvidenceInstanceEnforcementInput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise EvidenceInstanceEnforcementError("unsupported contract_version")
    if not isinstance(request_id, str) or not request_id.strip():
        raise EvidenceInstanceEnforcementError("request_id must be non-empty")
    if not isinstance(instance_sufficiency, InstanceSufficiencyOutput):
        raise EvidenceInstanceEnforcementError("instance_sufficiency must be validated")
    if not isinstance(evidence_input, EvidenceResolverInput):
        raise EvidenceInstanceEnforcementError("evidence_input must be validated")
    if instance_sufficiency.request_id != request_id or evidence_input.request_id != request_id:
        raise EvidenceInstanceEnforcementError("request_id must match all inputs")
    return EvidenceInstanceEnforcementInput(contract_version, request_id, instance_sufficiency, evidence_input)


def build_output(*, request_id: str, outcome: str, evidence_resolver_called: bool,
                 evidence_output: EvidenceResolverOutput | None, basis: str,
                 contract_version: str = SUPPORTED_CONTRACT_VERSION) -> EvidenceInstanceEnforcementOutput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise EvidenceInstanceEnforcementError("unsupported contract_version")
    if outcome not in ENFORCEMENT_OUTCOMES:
        raise EvidenceInstanceEnforcementError("unsupported outcome")
    if not isinstance(evidence_resolver_called, bool):
        raise EvidenceInstanceEnforcementError("evidence_resolver_called must be boolean")
    if evidence_resolver_called != (evidence_output is not None):
        raise EvidenceInstanceEnforcementError("resolver call flag must match output presence")
    if outcome == "EVIDENCE_RESOLUTION_AUTHORIZED" and not evidence_resolver_called:
        raise EvidenceInstanceEnforcementError("authorized outcome requires resolver execution")
    if outcome == "INSTANCE_SUFFICIENCY_BLOCKED" and evidence_resolver_called:
        raise EvidenceInstanceEnforcementError("blocked outcome may not call resolver")
    if not isinstance(basis, str) or not basis.strip():
        raise EvidenceInstanceEnforcementError("basis must be non-empty")
    return EvidenceInstanceEnforcementOutput(contract_version, request_id, outcome,
                                             evidence_resolver_called, evidence_output, basis)
