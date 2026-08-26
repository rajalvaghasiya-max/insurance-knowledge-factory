# Insurance Intelligence — Assertion / Advisory Boundary v1

**Status:** implementation contract for the first post-C5.36 Insurance Intelligence slice.

## Purpose

The Assertion / Advisory Boundary sits before the existing Intent Analyzer. It answers only:

> Is the user asking PolicyScna to state/explain what is true, to advise what action to take, or both?

It does **not** answer the insurance question, retrieve evidence, resolve entities, decide suitability, or generate a recommendation.

## Authority classes

- `ASSERTIVE` — asks for facts, meaning, explanation, calculation, coverage interpretation, or comparison without asking PolicyScna to choose an action for the user.
- `ADVISORY` — asks PolicyScna to recommend, choose, judge suitability, or direct an action.
- `MIXED` — contains both assertive and advisory requested outcomes; downstream processing must preserve both and may not let the factual portion lower the safety bar for the advisory portion.
- `UNRESOLVED` — the requested authority cannot be classified safely from the available request text. This fails closed into authority clarification rather than defaulting to `ASSERTIVE`.

## Placement

```text
User interaction
    ↓
Assertion / Advisory Boundary
    ↓
Intent Analyzer
    ↓
Context + instance resolution
    ↓
Instance sufficiency guard
    ↓
Evidence resolution
    ↓
Evidence sufficiency guard
    ↓
Reasoning
    ↓
Decision / safety + same authority boundary enforcement
    ↓
Explanation / response
```

This boundary is complementary to the existing MO-012 conclusion classes. `Source Fact`, `Deterministic Calculation`, `Derived Insurance Implication`, `Contextual Judgement`, and `Recommendation` classify conclusions after reasoning. The Assertion / Advisory Boundary classifies the **authority requested by the user before reasoning begins**.

## Non-negotiable rules

1. Advisory language must never be silently downgraded to an ordinary factual request.
2. `MIXED` requests retain an advisory obligation even when the factual portion is answerable.
3. `UNRESOLVED` does not default to `ASSERTIVE`.
4. This stage may inspect request language only. It may not access the Knowledge Factory, governed evidence, product documents, model memory, or user financial/medical facts beyond the request text supplied to it.
5. It may not determine whether advice is good, safe, suitable, affordable, or supported.
6. It may not create a recommendation or claim.
7. Classification is deterministic in v1. LLM assistance is not authorized.

## Downstream routing obligations

- `ASSERTIVE` → `STANDARD_ASSERTION_GROUNDING`.
- `ADVISORY` → `ADVISORY_CONTEXT_AND_SAFETY_REQUIRED`.
- `MIXED` → `SPLIT_ASSERTIVE_AND_ADVISORY_WITH_ADVISORY_SAFETY_REQUIRED`.
- `UNRESOLVED` → `CLARIFY_REQUESTED_AUTHORITY` and Intent Analyzer execution is withheld for this first slice.

`ADVISORY` is **not** a recommendation authorization. It is a routing label that raises the downstream context/evidence/safety obligations.

## v1 classification policy

The deterministic classifier uses frozen phrase/pattern registries.

Examples:

| Request | Class |
|---|---|
| “What is a co-pay?” | `ASSERTIVE` |
| “Explain my waiting period.” | `ASSERTIVE` |
| “Compare these two policies.” | `ASSERTIVE` |
| “Should I increase my base cover or buy a super top-up?” | `ADVISORY` |
| “Which plan is better for me?” | `ADVISORY` |
| “Explain the deductible and tell me whether I should choose this plan.” | `MIXED` |
| “And this one?” | `UNRESOLVED` |

The phrase registry is intentionally conservative. Missing a cue produces `UNRESOLVED`; the classifier is not permitted to infer a safe factual default.

## Scope exclusions

This slice does not implement intent changes, Context Builder changes, recommendation logic, suitability scoring, evidence resolution, reasoning, response generation, Motor, Life, frontend, or UI behavior.

## Acceptance criteria

- executable versioned input/output contract;
- deterministic classifier with governed immutable cue registries;
- advisory, assertive, mixed, and unresolved cases covered by tests;
- no imports from `factory_core` or `knowledge_domains`;
- no network or LLM calls;
- output explicitly declares the required downstream guard;
- `UNRESOLVED` blocks intent analysis in this first slice;
- no recommendation authorization is ever emitted.
