# Insurance Intelligence — Authority × Intent Reconciliation v1

**Status:** implementation contract for the second post-C5.36 Insurance Intelligence slice.

## Purpose

Authority and intent are independent governed classifications over the same request. This component reconciles those two outputs into the **minimum downstream safety obligation** that later stages may not weaken.

It does not answer the question, retrieve evidence, determine context sufficiency, reason, assess suitability, approve a recommendation, generate prose, or replace the Decision and Safety Gate.

## Monotonic safety rule

> Intent may raise the authority guard, but may never lower it.

Examples:

- `ASSERTIVE + TERM_EXPLANATION` -> standard assertion grounding.
- `ADVISORY + PRODUCT_EXPLANATION` -> advisory obligations remain mandatory even though the intent itself is non-advisory.
- `ASSERTIVE + RECOMMENDATION` -> raise to advisory guard and record a reconciliation conflict; do not vote between classifiers.
- `MIXED + POLICY_COMPARISON` -> retain the mixed/advisory safety guard.
- `UNRESOLVED + POLICY_FACT_LOOKUP` -> retain advisory hold and authority clarification; the resolved factual intent does not release the hold.

## Advisory intent signals

For v1, only the already-governed intent labels below are treated as intrinsically advisory signals for reconciliation:

- `RECOMMENDATION`
- `SUITABILITY_ASSESSMENT`

Comparison intents are not intrinsically advisory. `PRODUCT_COMPARISON`, `POLICY_COMPARISON`, and `QUOTE_COMPARISON` remain assertive unless the independent authority classification establishes advisory or mixed requested authority, or another governed advisory intent appears as a secondary label.

This list is not a new intent taxonomy. It is a reconciliation policy over the existing taxonomy.

## Reconciliation statuses

- `CONSISTENT_ASSERTIVE`
- `CONSISTENT_ADVISORY`
- `CONSISTENT_MIXED`
- `AUTHORITY_STRICTER_THAN_INTENT`
- `INTENT_RAISES_TO_ADVISORY`
- `AUTHORITY_UNRESOLVED`
- `INTENT_EXIT_REQUIRED`
- `OUT_OF_SCOPE`

A disagreement is never silently normalized away. The structured status remains available to downstream audit and evaluation.

## Minimum guards

- `STANDARD_ASSERTION_GROUNDING`
- `ADVISORY_CONTEXT_AND_SAFETY_REQUIRED`
- `SPLIT_ASSERTIVE_AND_ADVISORY_WITH_ADVISORY_SAFETY_REQUIRED`
- `ADVISORY_HOLD_AND_CLARIFY_AUTHORITY`
- `INTENT_EXIT_BEFORE_REASONING`
- `OUT_OF_SCOPE_EXIT`

The output is a minimum obligation, not permission to answer. Context Builder, Reasoning Planner, Evidence Resolver, Reasoning Engine, and Decision/Safety Gate continue to enforce their existing contracts.

## Conflict handling

`ASSERTIVE` authority paired with `RECOMMENDATION` or `SUITABILITY_ASSESSMENT` is treated as a safety-significant classifier disagreement:

- advisory safety obligation becomes mandatory;
- ordinary assertion path is prohibited;
- `reconciliation_clarification_required = true`;
- recommendation remains unauthorized.

This milestone does not implement a statistical arbitration policy, majority vote, model-confidence override, or LLM tie-breaker.

## Exit handling

Intent states that already require an exit (`CLARIFICATION_REQUIRED`, `INVALID_REQUEST`, `OUT_OF_SCOPE`) remain exits. Reconciliation does not convert them into executable reasoning plans.

Authority metadata is preserved on the reconciliation output even when the intent exits, so the independent safety signal is not erased.

## Relationship to Decision and Safety Gate

The existing Decision and Safety Gate remains the stage that decides whether a reasoning result may be surfaced. It already carries governed safety issues such as `RECOMMENDATION_WITHOUT_SUITABILITY`, missing context/evidence, conflicts, unsupported inference, and human review requirements.

This reconciliation layer acts earlier and more narrowly: it ensures a request that asks for, may ask for, or is classified into advisory authority cannot enter downstream processing under an ordinary factual safety posture.

## Non-goals

This slice does not:

- modify the governed 19-intent taxonomy;
- change the Intent Analyzer implementation;
- change Context Builder requirements;
- perform evidence access;
- implement recommendation or suitability logic;
- change the Reasoning Engine;
- change the Decision and Safety Gate;
- add an LLM, network call, or model confidence policy;
- add Motor, Life, frontend, or UI behavior.

## Acceptance criteria

- consumes validated `RequestAuthorityOutput` and `IntentAnalyzerOutput` with the same request ID;
- deterministic and side-effect free;
- intent can raise but never lower the authority safety obligation;
- `UNRESOLVED` authority always retains advisory hold and authority clarification;
- advisory/mixed authority cannot enter the ordinary assertion path through a non-advisory intent;
- `ASSERTIVE + advisory intent` is surfaced as a conflict and upgraded to advisory safety;
- intent exit states remain exits;
- no recommendation authorization is emitted;
- no evidence, Knowledge Factory, LLM, or network dependency is introduced.
