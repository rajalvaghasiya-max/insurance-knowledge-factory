# Insurance Intelligence — Authority Downstream Enforcement v1

**Status:** implementation contract for post-reconciliation enforcement.

## Purpose

This milestone makes the Assertion / Advisory Boundary operational downstream. It consumes the governed `AuthorityIntentReconciliationOutput` and ensures that a stronger authority obligation cannot disappear before communication.

The enforcement layer does **not** classify authority or intent, retrieve evidence, reason, assess suitability, or authorize recommendations. It only decides whether the existing deterministic Decision/Safety Gate may be invoked.

## Design choice: wrapper, not mutation of the proven gate

The existing `DecisionSafetyGate` is already an active and tested component. Rather than changing its historical constructor or making new authority fields mandatory for legacy pilots, v1 introduces an `AuthorityEnforcedDecisionGate` wrapper.

```text
Authority output -----\
                      +--> Reconciliation --> Authority Enforcement --> existing Decision/Safety Gate
Intent output --------/                            |
                                                   +--> governed preflight exit
```

This preserves the existing gate while defining a new authority-aware path for Insurance Intelligence execution.

## Monotonic enforcement rule

Downstream stages may preserve or strengthen a reconciled safety obligation; they may never weaken it.

In v1:

- only `ordinary_assertion_path_permitted=true` may delegate to the existing Decision/Safety Gate;
- `ADVISORY` and `MIXED` obligations do not delegate because no advisory execution capability is authorized yet;
- `UNRESOLVED` authority remains under advisory hold and exits for authority clarification;
- authority/intent disagreement requiring reconciliation clarification exits before the Decision Gate;
- intent-level exit and out-of-scope states remain exits.

No caller may convert any of these exits into an ordinary assertive approval.

## Why advisory requests are withheld rather than given a clearance flag

This milestone does not implement recommendation, suitability, affordability, personalized financial advice, or an advisory context-sufficiency contract. Introducing a boolean such as `advisory_safety_cleared=true` would create a new authority surface with no governed producer.

Therefore v1 uses the only defensible posture:

> A reconciled advisory obligation is withheld until a future, separately authorized advisory-context/safety milestone defines what constitutes sufficient context, evidence, and safety clearance.

This is not a recommendation refusal policy for the final product. It is a milestone boundary preventing an unimplemented advisory capability from being simulated by the factual pipeline.

## Enforcement outcomes

- `DELEGATED_TO_DECISION_GATE` — consistent ordinary assertive request only.
- `ADVISORY_PATH_NOT_AUTHORIZED` — resolved advisory or mixed request; future advisory capability required.
- `AUTHORITY_CLARIFICATION_REQUIRED` — authority remains unresolved under advisory hold.
- `RECONCILIATION_CLARIFICATION_REQUIRED` — authority/intent disagreement cannot be silently resolved.
- `INTENT_EXIT_REQUIRED` — governed Intent Analyzer exit is preserved.
- `OUT_OF_SCOPE` — governed out-of-scope exit is preserved.

Every non-delegated outcome proves `decision_gate_called=false`.

## Non-negotiable invariants

1. Recommendation authorization is always false in this layer.
2. Advisory obligations never enter the ordinary assertion path.
3. `UNRESOLVED` never defaults to assertive.
4. `ASSERTIVE + RECOMMENDATION/SUITABILITY` disagreement never delegates until reconciliation is resolved.
5. `MIXED` never delegates through the factual portion alone.
6. Preflight exits never call the underlying Decision/Safety Gate.
7. The existing Decision/Safety Gate remains unchanged and retains its own evidence, reasoning, and safety policies.
8. No LLM, network, Knowledge Factory, product-document, or recommendation logic is introduced.

## What this milestone does not authorize

This milestone does not authorize recommendation generation, suitability scoring, advisory reasoning, new user-context collection, advisor/consumer UI, Motor, Life, frontend work, or any relaxation of existing evidence governance.

## Next boundary after closure

Once this enforcement slice is proven, the Assertion / Advisory Boundary is complete for the currently authorized scope:

```text
independent authority + intent
        ↓
reconciliation
        ↓
monotonic downstream enforcement
```

The next architectural milestone should be selected from the frozen Insurance Intelligence roadmap rather than expanding advisory capability implicitly.
