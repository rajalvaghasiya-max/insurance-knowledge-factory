"""Authority-enforced wrapper around the existing deterministic Decision/Safety Gate."""
from __future__ import annotations

from insurance_intelligence.contracts.authority_enforcement import (
    AuthorityEnforcedDecisionInput,
    AuthorityEnforcementResult,
    build_result,
)
from insurance_intelligence.decision.gate import DecisionSafetyGate


class AuthorityEnforcedDecisionGate:
    """Enforce reconciled authority posture before the legacy Decision/Safety Gate.

    v1 delegates only requests that are explicitly permitted on the ordinary
    assertive path. Advisory, mixed, unresolved-authority, intent-exit, and
    out-of-scope requests are withheld before the underlying gate is called.
    """

    def __init__(self, decision_gate: DecisionSafetyGate | None = None) -> None:
        self._decision_gate = decision_gate or DecisionSafetyGate()

    def decide(self, data: AuthorityEnforcedDecisionInput) -> AuthorityEnforcementResult:
        if not isinstance(data, AuthorityEnforcedDecisionInput):
            raise TypeError("data must be AuthorityEnforcedDecisionInput")

        reconciliation = data.reconciliation
        trace = [
            f"reconciliation_status={reconciliation.reconciliation_status}",
            f"minimum_guard={reconciliation.minimum_guard}",
            f"authority_class={reconciliation.authority_class}",
            f"primary_intent={reconciliation.primary_intent}",
        ]

        if reconciliation.reconciliation_status == "OUT_OF_SCOPE":
            trace.append("preflight_exit=OUT_OF_SCOPE")
            return self._exit(
                data,
                outcome="OUT_OF_SCOPE",
                clarification_required=False,
                out_of_scope=True,
                basis="reconciliation requires out-of-scope exit before Decision Gate",
                trace=tuple(trace),
            )

        if reconciliation.intent_exit_required:
            trace.append("preflight_exit=INTENT_EXIT_REQUIRED")
            return self._exit(
                data,
                outcome="INTENT_EXIT_REQUIRED",
                clarification_required=True,
                out_of_scope=False,
                basis="intent analysis requires governed exit before reasoning/Decision Gate",
                trace=tuple(trace),
            )

        if reconciliation.authority_clarification_required:
            trace.append("preflight_exit=AUTHORITY_CLARIFICATION_REQUIRED")
            return self._exit(
                data,
                outcome="AUTHORITY_CLARIFICATION_REQUIRED",
                clarification_required=True,
                out_of_scope=False,
                basis="authority remains unresolved and must be clarified under advisory hold",
                trace=tuple(trace),
            )

        if reconciliation.reconciliation_clarification_required:
            trace.append("preflight_exit=RECONCILIATION_CLARIFICATION_REQUIRED")
            return self._exit(
                data,
                outcome="RECONCILIATION_CLARIFICATION_REQUIRED",
                clarification_required=True,
                out_of_scope=False,
                basis="authority/intent conflict requires clarification before downstream approval",
                trace=tuple(trace),
            )

        if reconciliation.advisory_safety_obligation:
            trace.append("preflight_exit=ADVISORY_PATH_NOT_AUTHORIZED")
            return self._exit(
                data,
                outcome="ADVISORY_PATH_NOT_AUTHORIZED",
                clarification_required=False,
                out_of_scope=False,
                basis=(
                    "reconciled request carries advisory safety obligations, but no advisory execution "
                    "capability is authorized in this milestone"
                ),
                trace=tuple(trace),
            )

        if not reconciliation.ordinary_assertion_path_permitted:
            raise ValueError(
                "non-advisory request cannot delegate without ordinary_assertion_path_permitted"
            )

        trace.append("delegated_to_existing_decision_gate=true")
        decision_output = self._decision_gate.decide(data.decision_gate_input)
        trace.append(f"decision_gate_outcome={decision_output.decision}")
        return build_result(
            request_id=data.request_id,
            enforcement_outcome="DELEGATED_TO_DECISION_GATE",
            minimum_guard=reconciliation.minimum_guard,
            advisory_safety_obligation=False,
            ordinary_assertion_path_permitted=True,
            decision_gate_called=True,
            decision_output=decision_output,
            clarification_required=False,
            out_of_scope=False,
            basis="ordinary assertive path cleared reconciliation and delegated to existing Decision Gate",
            enforcement_trace=tuple(trace),
            recommendation_authorized=False,
            contract_version=data.contract_version,
        )

    @staticmethod
    def _exit(
        data: AuthorityEnforcedDecisionInput,
        *,
        outcome: str,
        clarification_required: bool,
        out_of_scope: bool,
        basis: str,
        trace: tuple[str, ...],
    ) -> AuthorityEnforcementResult:
        reconciliation = data.reconciliation
        return build_result(
            request_id=data.request_id,
            enforcement_outcome=outcome,
            minimum_guard=reconciliation.minimum_guard,
            advisory_safety_obligation=reconciliation.advisory_safety_obligation,
            ordinary_assertion_path_permitted=False,
            decision_gate_called=False,
            decision_output=None,
            clarification_required=clarification_required,
            out_of_scope=out_of_scope,
            basis=basis,
            enforcement_trace=trace,
            recommendation_authorized=False,
            contract_version=data.contract_version,
        )
