"""Deterministic Instance Sufficiency Guard for the Insurance Intelligence path."""
from __future__ import annotations

from insurance_intelligence.contracts.instance_sufficiency import (
    InstanceSufficiencyInput,
    InstanceSufficiencyOutput,
    build_output,
)

# These are identity-bearing context keys. A textual/candidate context value is
# not authoritative identity; the corresponding governed attestation must resolve.
_REQUIRED_INSTANCE_KEYS_BY_INTENT: dict[str, tuple[str, ...]] = {
    "POLICY_FACT_LOOKUP": ("policy_or_document_reference",),
    "POLICY_SUMMARY": ("policy_or_document_reference",),
    "COVERAGE_CHECK": ("policy_or_product_reference",),
    "EXCLUSION_CHECK": ("policy_or_product_reference",),
    "CLAIM_SCENARIO": ("policy_or_product_reference",),
    "PRODUCT_EXPLANATION": ("product_reference",),
    "PRODUCT_COMPARISON": ("comparison_subject_1", "comparison_subject_2"),
    "POLICY_COMPARISON": ("comparison_subject_1", "comparison_subject_2"),
    "QUOTE_COMPARISON": ("quote_reference_1", "quote_reference_2"),
    "DOCUMENT_INTERPRETATION": ("document_reference",),
    "SUITABILITY_ASSESSMENT": ("subject_reference",),
}

# Clause implication is intentionally conditional: it can be a generic concept
# explanation. If the context includes a specific policy/product reference, that
# reference must be governed before instance-specific planning.
_CONDITIONAL_INSTANCE_KEYS_BY_INTENT: dict[str, tuple[str, ...]] = {
    "CLAUSE_IMPLICATION": ("policy_or_product_reference",),
}


class InstanceSufficiencyGuard:
    """Require governed instance identity before instance-specific planning."""

    def evaluate(self, data: InstanceSufficiencyInput) -> InstanceSufficiencyOutput:
        if not isinstance(data, InstanceSufficiencyInput):
            raise TypeError("data must be InstanceSufficiencyInput")

        context = data.context
        reconciliation = data.reconciliation

        if reconciliation.reconciliation_status == "OUT_OF_SCOPE" or context.answerability == "OUT_OF_SCOPE":
            return build_output(
                request_id=data.request_id,
                outcome="OUT_OF_SCOPE",
                required_instance_keys=(),
                resolved_instance_keys=(),
                unresolved_instance_keys=(),
                planning_authorized=False,
                clarification_required=False,
                basis="request is out of scope before instance planning",
            )

        if reconciliation.intent_exit_required or context.answerability == "CLARIFICATION_REQUIRED":
            return build_output(
                request_id=data.request_id,
                outcome="CLARIFICATION_REQUIRED",
                required_instance_keys=(),
                resolved_instance_keys=(),
                unresolved_instance_keys=(),
                planning_authorized=False,
                clarification_required=True,
                basis="upstream intent/context sufficiency requires clarification before planning",
            )

        if context.answerability in {"NOT_ANSWERABLE", "PARTIALLY_ANSWERABLE"}:
            return build_output(
                request_id=data.request_id,
                outcome="NOT_ANSWERABLE",
                required_instance_keys=(),
                resolved_instance_keys=(),
                unresolved_instance_keys=(),
                planning_authorized=False,
                clarification_required=False,
                basis="context is not sufficiently answerable for planning",
            )

        active_context_keys = {item.key for item in context.resolved_context if item.status == "ACTIVE"}
        required = list(_REQUIRED_INSTANCE_KEYS_BY_INTENT.get(reconciliation.primary_intent, ()))
        for key in _CONDITIONAL_INSTANCE_KEYS_BY_INTENT.get(reconciliation.primary_intent, ()):
            if key in active_context_keys:
                required.append(key)
        required_keys = tuple(required)

        if not required_keys:
            return build_output(
                request_id=data.request_id,
                outcome="PASS",
                required_instance_keys=(),
                resolved_instance_keys=(),
                unresolved_instance_keys=(),
                planning_authorized=True,
                clarification_required=False,
                basis="intent does not require a governed product/policy/document instance",
            )

        by_key = {item.context_key: item for item in data.attestations}
        resolved: list[str] = []
        unresolved: list[str] = []
        for key in required_keys:
            attestation = by_key.get(key)
            if (
                key in active_context_keys
                and attestation is not None
                and attestation.resolution_status == "RESOLVED"
            ):
                resolved.append(key)
            else:
                unresolved.append(key)

        if unresolved:
            return build_output(
                request_id=data.request_id,
                outcome="CLARIFICATION_REQUIRED",
                required_instance_keys=required_keys,
                resolved_instance_keys=tuple(resolved),
                unresolved_instance_keys=tuple(unresolved),
                planning_authorized=False,
                clarification_required=True,
                basis="required instance identity is missing, ambiguous, unresolved, or not bound to active context",
            )

        return build_output(
            request_id=data.request_id,
            outcome="PASS",
            required_instance_keys=required_keys,
            resolved_instance_keys=tuple(resolved),
            unresolved_instance_keys=(),
            planning_authorized=True,
            clarification_required=False,
            basis="all required instance identities are governed and resolved",
        )
