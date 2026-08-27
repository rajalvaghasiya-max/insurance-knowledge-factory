# Insurance Intelligence — Assertion / Advisory Boundary v1

**Status:** implementation contract for the first post-C5.36 Insurance Intelligence slice.

## Purpose

The Assertion / Advisory Boundary classifies the authority the user is asking PolicyScna to exercise:

> Is the user asking PolicyScna to state/explain what is true, to advise what action to take, or both?

It does **not** answer the insurance question, retrieve evidence, resolve entities, decide suitability, or generate a recommendation.

## Load-bearing property: independence, not temporal precedence

Authority and intent are two independent classifications over the same normalized request. Neither is permitted to overwrite, suppress, or redefine the other. A deployment may compute them sequentially or in parallel, but downstream reconciliation must receive both governed outputs.

This is stronger and more precise than requiring a fixed `Authority -> Intent` runtime order. The safety invariant is:

> An intent decision, classifier replacement, serving optimization, or fallback model may never weaken an independently established advisory obligation.

## Authority classes

- `ASSERTIVE` — asks for facts, meaning, explanation, calculation, coverage interpretation, or comparison without asking PolicyScna to choose an action for the user.
- `ADVISORY` — asks PolicyScna to recommend, choose, judge suitability, or direct an action.
- `MIXED` — contains both assertive and advisory requested outcomes; downstream processing must preserve both and may not let the factual portion lower the safety bar for the advisory portion.
- `UNRESOLVED` — requested authority cannot be classified safely from available request language. This does not default to `ASSERTIVE`; it carries the advisory safety obligation until authority is clarified.

## Conceptual placement

```text
                    normalized request
                          /      \
                         /        \
                        v          v
              Authority Class   Intent Class
                        \          /
                         \        /
                          v      v
                    Reconciliation
                          |
                          v
               Context + instance resolution
                          |
                          v
               Instance sufficiency guard
                          |
                          v
                  Evidence resolution
                          |
                          v
                Evidence sufficiency guard
                          |
                          v
                       Reasoning
                          |
                          v
           Decision / safety + authority enforcement
                          |
                          v
                 Explanation / response
```

The current v1 implementation is a standalone authority classifier; it does not yet implement the reconciliation component. Existing intent analysis may proceed independently.

This boundary is complementary to the existing MO-012 conclusion classes. `Source Fact`, `Deterministic Calculation`, `Derived Insurance Implication`, `Contextual Judgement`, and `Recommendation` classify conclusions after reasoning. The Assertion / Advisory Boundary classifies the **authority requested by the user** independently of task intent.

## Non-negotiable rules

1. Advisory language must never be silently downgraded to an ordinary factual request.
2. `MIXED` requests retain an advisory obligation even when the factual portion is answerable.
3. `UNRESOLVED` does not default to `ASSERTIVE`.
4. `UNRESOLVED` fails toward the stricter posture: advisory safety remains required and authority clarification is required. An ordinary assertive response may not bypass that hold while authority remains unresolved.
5. Authority uncertainty does not suppress independent intent classification; the two signals are reconciled downstream.
6. This stage may inspect request language only. It may not access the Knowledge Factory, governed evidence, product documents, model memory, or user financial/medical facts beyond the request text supplied to it.
7. It may not determine whether advice is good, safe, suitable, affordable, or supported.
8. It may not create a recommendation or claim.
9. Classification is deterministic in v1. LLM assistance is not authorized.

## Downstream routing obligations

- `ASSERTIVE` -> `STANDARD_ASSERTION_GROUNDING`; no advisory safety obligation from this boundary.
- `ADVISORY` -> `ADVISORY_CONTEXT_AND_SAFETY_REQUIRED`; advisory safety obligation is mandatory.
- `MIXED` -> `SPLIT_ASSERTIVE_AND_ADVISORY_WITH_ADVISORY_SAFETY_REQUIRED`; advisory safety obligation is mandatory for the request.
- `UNRESOLVED` -> `ADVISORY_HOLD_AND_CLARIFY_AUTHORITY`; advisory safety obligation remains mandatory until clarification/reclassification.

`ADVISORY` is **not** a recommendation authorization. It is a routing label that raises downstream context/evidence/safety obligations.

## Independent authority vs intent examples

| Request | Authority | Possible intent |
|---|---|---|
| “What is a co-pay?” | `ASSERTIVE` | `TERM_EXPLANATION` |
| “Compare these two policies.” | `ASSERTIVE` | `POLICY_COMPARISON` |
| “Should I increase my base cover or buy a super top-up?” | `ADVISORY` | `SUITABILITY_ASSESSMENT` or `RECOMMENDATION` |
| “Compare these two policies and tell me which I should buy.” | `MIXED` | comparison + recommendation-related intent signal |
| “And this one?” | `UNRESOLVED` | intent may also be unresolved or may resolve from conversation context; authority still remains under strict advisory hold until resolved |

## Governed taxonomy vs classifier decomposition

The existing governed intent taxonomy is a downstream contract and is not changed by this milestone. Future classifier implementations may use any benchmark-proven internal decomposition — flat multiclass, coarse-to-fine, hierarchical, slot-conditioned, or hybrid — provided the final output validates against the governed intent contract.

Classifier implementation shape is therefore **not** an architectural commitment. For example, a future internal `COMPARISON` head refined by the compared entity/document type may emit one of the existing governed `PRODUCT_COMPARISON`, `POLICY_COMPARISON`, or `QUOTE_COMPARISON` labels without collapsing those downstream distinctions.

Likewise, future replacement of the deterministic intent classifier is a benchmark decision, not part of this authority-boundary milestone. The deterministic implementation is the incumbent; a replacement must clear frozen safety metrics such as advisory/mixed false-negative risk and risk-at-accepted-coverage, not merely improve aggregate accuracy.

## v1 classification policy

The deterministic authority classifier uses frozen phrase/pattern registries. The registry is intentionally conservative. Missing a governed authority cue produces `UNRESOLVED`; the classifier is not permitted to infer a safe factual default.

## Scope exclusions

This slice does not implement the authority/intent reconciliation stage, intent taxonomy changes, Context Builder changes, recommendation logic, suitability scoring, evidence resolution, reasoning, response generation, Motor, Life, frontend, or UI behavior.

## Acceptance criteria

- executable versioned input/output contract;
- deterministic classifier with governed immutable cue registries;
- advisory, assertive, mixed, and unresolved cases covered by tests;
- authority and intent explicitly modeled as independent classifications over the same request;
- intent analysis may proceed independently for all authority states;
- `UNRESOLVED` carries advisory safety obligation plus authority clarification requirement;
- no imports from `factory_core` or `knowledge_domains`;
- no network or LLM calls;
- output explicitly declares the required downstream guard;
- no recommendation authorization is ever emitted.
