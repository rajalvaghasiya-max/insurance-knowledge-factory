"""Fail-closed preflight binding Instance Sufficiency to MO-016 Evidence Resolution."""
from __future__ import annotations

from insurance_intelligence.contracts.evidence_instance_enforcement import (
    EvidenceInstanceEnforcementInput,
    EvidenceInstanceEnforcementOutput,
    build_output,
)
from insurance_intelligence.evidence.resolver import EvidenceResolver


class EvidenceInstanceEnforcer:
    """Delegate to the existing resolver only after Instance Sufficiency PASS."""

    def __init__(self, resolver: EvidenceResolver | None = None) -> None:
        self._resolver = resolver or EvidenceResolver()

    def resolve(self, data: EvidenceInstanceEnforcementInput) -> EvidenceInstanceEnforcementOutput:
        if not isinstance(data, EvidenceInstanceEnforcementInput):
            raise TypeError("data must be EvidenceInstanceEnforcementInput")

        instance = data.instance_sufficiency
        if instance.outcome != "PASS" or not instance.planning_authorized:
            return build_output(
                request_id=data.request_id,
                outcome="INSTANCE_SUFFICIENCY_BLOCKED",
                evidence_resolver_called=False,
                evidence_output=None,
                basis=(
                    "evidence resolution is withheld because governed instance sufficiency "
                    f"did not pass: outcome={instance.outcome}"
                ),
                contract_version=data.contract_version,
            )

        output = self._resolver.resolve(data.evidence_input)
        return build_output(
            request_id=data.request_id,
            outcome="EVIDENCE_RESOLUTION_AUTHORIZED",
            evidence_resolver_called=True,
            evidence_output=output,
            basis="instance sufficiency passed before delegation to existing MO-016 resolver",
            contract_version=data.contract_version,
        )
