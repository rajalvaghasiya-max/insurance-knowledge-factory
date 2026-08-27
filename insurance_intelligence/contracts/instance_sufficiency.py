"""Executable contract for governed instance-resolution sufficiency."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from insurance_intelligence.contracts.context import ContextBuilderOutput
from insurance_intelligence.contracts.authority_intent_reconciliation import AuthorityIntentReconciliationOutput

SUPPORTED_CONTRACT_VERSION = "1.0"
INSTANCE_KINDS = frozenset({"PRODUCT", "POLICY", "DOCUMENT"})
RESOLUTION_STATUSES = frozenset({"RESOLVED", "AMBIGUOUS", "UNRESOLVED", "NOT_REQUIRED"})
SUFFICIENCY_OUTCOMES = frozenset({"PASS", "CLARIFICATION_REQUIRED", "NOT_ANSWERABLE", "OUT_OF_SCOPE"})


class InstanceSufficiencyContractError(ValueError):
    """Raised when instance-resolution or sufficiency records are invalid."""


def _nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InstanceSufficiencyContractError(f"{label} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True)
class InstanceResolutionAttestation:
    instance_kind: str
    context_key: str
    resolution_status: str
    canonical_identity: str | None
    identity_record_ref: str | None
    identity_record_hash: str | None
    resolution_basis: str


def build_attestation(
    *,
    instance_kind: str,
    context_key: str,
    resolution_status: str,
    resolution_basis: str,
    canonical_identity: str | None = None,
    identity_record_ref: str | None = None,
    identity_record_hash: str | None = None,
) -> InstanceResolutionAttestation:
    if instance_kind not in INSTANCE_KINDS:
        raise InstanceSufficiencyContractError("unsupported instance_kind")
    if resolution_status not in RESOLUTION_STATUSES:
        raise InstanceSufficiencyContractError("unsupported resolution_status")
    if resolution_status == "RESOLVED":
        canonical_identity = _nonempty(canonical_identity, "canonical_identity")
        identity_record_ref = _nonempty(identity_record_ref, "identity_record_ref")
        identity_record_hash = _nonempty(identity_record_hash, "identity_record_hash")
    else:
        if any(value is not None for value in (canonical_identity, identity_record_ref, identity_record_hash)):
            raise InstanceSufficiencyContractError(
                "non-resolved attestations may not carry authoritative identity fields"
            )
    return InstanceResolutionAttestation(
        instance_kind=instance_kind,
        context_key=_nonempty(context_key, "context_key"),
        resolution_status=resolution_status,
        canonical_identity=canonical_identity,
        identity_record_ref=identity_record_ref,
        identity_record_hash=identity_record_hash,
        resolution_basis=_nonempty(resolution_basis, "resolution_basis"),
    )


@dataclass(frozen=True)
class InstanceSufficiencyInput:
    contract_version: str
    request_id: str
    reconciliation: AuthorityIntentReconciliationOutput
    context: ContextBuilderOutput
    attestations: tuple[InstanceResolutionAttestation, ...]


def build_input(
    *,
    request_id: str,
    reconciliation: AuthorityIntentReconciliationOutput,
    context: ContextBuilderOutput,
    attestations: Sequence[InstanceResolutionAttestation] = (),
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> InstanceSufficiencyInput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise InstanceSufficiencyContractError("unsupported contract_version")
    request_id = _nonempty(request_id, "request_id")
    if not isinstance(reconciliation, AuthorityIntentReconciliationOutput):
        raise InstanceSufficiencyContractError("reconciliation must be validated")
    if not isinstance(context, ContextBuilderOutput):
        raise InstanceSufficiencyContractError("context must be validated")
    if reconciliation.request_id != request_id or context.request_id != request_id:
        raise InstanceSufficiencyContractError("request_id must match reconciliation and context")
    values = tuple(attestations)
    if not all(isinstance(item, InstanceResolutionAttestation) for item in values):
        raise InstanceSufficiencyContractError("attestations must be validated")
    if len({item.context_key for item in values}) != len(values):
        raise InstanceSufficiencyContractError("attestations must have unique context_key values")
    return InstanceSufficiencyInput(contract_version, request_id, reconciliation, context, values)


@dataclass(frozen=True)
class InstanceSufficiencyOutput:
    contract_version: str
    request_id: str
    outcome: str
    required_instance_keys: tuple[str, ...]
    resolved_instance_keys: tuple[str, ...]
    unresolved_instance_keys: tuple[str, ...]
    planning_authorized: bool
    clarification_required: bool
    basis: str


def build_output(
    *,
    request_id: str,
    outcome: str,
    required_instance_keys: Sequence[str],
    resolved_instance_keys: Sequence[str],
    unresolved_instance_keys: Sequence[str],
    planning_authorized: bool,
    clarification_required: bool,
    basis: str,
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> InstanceSufficiencyOutput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise InstanceSufficiencyContractError("unsupported contract_version")
    if outcome not in SUFFICIENCY_OUTCOMES:
        raise InstanceSufficiencyContractError("unsupported outcome")
    if not isinstance(planning_authorized, bool) or not isinstance(clarification_required, bool):
        raise InstanceSufficiencyContractError("authorization flags must be boolean")
    required = tuple(required_instance_keys)
    resolved = tuple(resolved_instance_keys)
    unresolved = tuple(unresolved_instance_keys)
    if set(resolved).intersection(unresolved):
        raise InstanceSufficiencyContractError("resolved and unresolved keys must be disjoint")
    if set(resolved).union(unresolved) != set(required):
        raise InstanceSufficiencyContractError("resolved + unresolved must exactly cover required keys")
    if planning_authorized != (outcome == "PASS"):
        raise InstanceSufficiencyContractError("planning_authorized is permitted only for PASS")
    if outcome == "CLARIFICATION_REQUIRED" and not clarification_required:
        raise InstanceSufficiencyContractError("clarification outcome must require clarification")
    return InstanceSufficiencyOutput(
        contract_version=contract_version,
        request_id=_nonempty(request_id, "request_id"),
        outcome=outcome,
        required_instance_keys=required,
        resolved_instance_keys=resolved,
        unresolved_instance_keys=unresolved,
        planning_authorized=planning_authorized,
        clarification_required=clarification_required,
        basis=_nonempty(basis, "basis"),
    )
