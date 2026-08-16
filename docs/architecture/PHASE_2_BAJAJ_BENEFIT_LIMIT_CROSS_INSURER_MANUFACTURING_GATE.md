# Phase 2 — Bajaj Benefit-Limit Cross-Insurer Manufacturing Gate

**Status:** CERTIFIED AND FROZEN  
**Date:** 2026-08-16

## Purpose

Prove that a second insurer's simple benefit-specific monetary limit can travel through PolicyScna's existing generic Health knowledge-manufacturing path without Bajaj-specific production reasoning or a new semantic abstraction.

This gate continues the manufacturing proof after the certified Bajaj initial waiting-period gate. It does not expand product scope or create a new subsystem.

## Why benefit limits now

MO-028C already established the architectural pressure and final design for Health benefit-limit/sub-limit semantics. Its Star Arogya qualification found the semantic family representable after generic hardening, but the committed qualification explicitly did not certify the real-product mapping.

The current generic topic catalogue already provides the insurer-independent `coverage_limit` topic with:

- `covered_subject`
- `limit_value`
- `limit_basis`
- `applicability_scope`
- optional `excess_consequence`

Therefore the correct pressure was manufacturing against a real second-insurer rule, not more ontology design.

## Current governed source

```text
Bajaj General Insurance — My Health Care
UIN: BAJHLIP26074V022526
SHA-256: 05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158
state: current_observed_reviewed
```

Only this current immutable source is factual authority for this gate.

## Candidate qualification result

### Family Visit — rejected for bounded certification

Page 52 establishes:

```text
Family Visit
SI up to INR 10 lakh     -> up to INR 25,000
SI more than INR 10 lakh -> up to INR 50,000
```

This is not enough for generic `coverage_limit` certification because the reviewed current-source excerpt does not establish the required `limit_basis` — e.g. per visit, per policy year, aggregate, or another basis.

Therefore:

```text
Family Visit -> REJECTED_FOR_BOUNDED_CERTIFICATION
reason       -> required limit_basis unresolved
```

The gate does not guess the missing basis.

### Cataract surgery — selected bounded pressure case

Page 38 states:

```text
surgeries for cataracts
(after expiry of waiting period specified in Policy Schedule)

For SI up to 10 Lac -> 20% of SI, maximum INR 1 Lac per eye
For SI above 10 Lac -> Actual
```

To avoid semantic leakage, the certified/publication case is deliberately atomic and covers only:

```text
subject       = cataract surgery
SI scope      = up to INR 10 lakh
limit value   = 20% of Sum Insured
ceiling       = INR 1 lakh
limit basis   = per eye
applicability = after expiry of waiting period specified in Policy Schedule
```

The `SI above INR 10 lakh -> Actual` branch is not folded into this rule and remains separate residue.

The schedule-selected waiting-period duration is also not resolved by this coverage-limit gate. The dependency is preserved as applicability context only.

## Governed qualification record

Materialized at:

```text
knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/governance/benefit_limit_current_source_qualification.json
```

The record preserves both:

- the failed Family Visit qualification; and
- the selected bounded cataract rule.

This is intentional evidence that candidate qualification fails closed when required semantics are absent.

## Generic certification case

Materialized at:

```text
knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/generic_rule_certification/cataract_si_up_to_10_lakh_coverage_limit_certification_case.json
```

The case uses the unchanged generic `coverage_limit` topic and requires:

- `covered_subject` -> SATISFIED
- `limit_value` -> SATISFIED
- `limit_basis` -> SATISFIED
- `applicability_scope` -> SATISFIED

Optional `excess_consequence` is not asserted because the bounded source proposition does not independently establish one.

Certification result:

```text
outcome      = PASS
completeness = COMPLETE
explanation  = permitted
```

## Publication decision and authoritative publication

A bounded data-only publication case was materialized at:

```text
knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/generic_rule_certification/cataract_si_up_to_10_lakh_coverage_limit_publication_case.json
```

The same certified governed-data case was passed through the existing generic publication-decision evaluator and generic authoritative-publication gate.

No Bajaj-specific production publication module was added.

The bounded cataract rule successfully reached authoritative publication while preserving certification limitations and evidence traces.

This publication applies only to the SI <= INR 10 lakh cataract branch described above. It does not resolve or publish the separate `Actual` branch or schedule-selected waiting-period duration.

## Existing architecture reused

The gate used only existing generic contracts:

1. current governed source identity/currentness;
2. generic evidence representation;
3. `coverage_limit` topic completeness;
4. generic rule-certification case loader and runner;
5. generic publication-decision evaluation;
6. generic authoritative-publication gate.

No Bajaj-specific production reasoning was added.

## Explicit residue

This gate does not resolve or publish:

- Family Visit limit basis;
- cataract waiting-period duration from Policy Schedule;
- the `SI above INR 10 lakh -> Actual` cataract branch;
- other page-52 benefit limits such as Home Nursing, Airlift, maternity, OPD or external medical aid;
- whole-product benefit-limit completeness;
- whole-product governed readiness.

## Regression evidence

Focused certification + publication suite:

```text
5 passed
```

Broader regressions:

```text
insurance_intelligence : 2914 passed
factory_core            : 148 passed
health                  : 124 passed
failures                : 0
```

## Acceptance criteria closure

- current immutable source SHA `05dc...` is the only current factual authority — PASS;
- historical mappings are not promoted as current truth — PASS;
- candidate qualification is fail closed — PASS;
- Family Visit missing basis remains unresolved — PASS;
- selected rule is genuinely benefit-specific and bounded — PASS;
- covered subject, value, basis and applicability are explicitly evidenced — PASS;
- no table-order guessing or schedule/band inference — PASS;
- no scalar flattening across the >INR 10 lakh branch — PASS;
- waiting-period schedule value remains unresolved — PASS;
- zero Bajaj-specific production reasoning code — PASS;
- no new semantic abstraction — PASS;
- generic `coverage_limit` contract reused — PASS;
- generic certification execution — PASS;
- generic publication decision — PASS;
- generic authoritative publication — PASS;
- unrelated benefit-limit residue remains unresolved — PASS;
- no whole-product governed-readiness inference — PASS;
- regressions green — PASS.

## What this gate proves

This gate establishes a second-insurer, second-semantic-family manufacturing proof:

```text
current governed source
-> fail-closed candidate qualification
-> governed coverage-limit evidence
-> generic rule certification
-> generic publication decision
-> generic authoritative publication
```

The pipeline handled a bounded Bajaj benefit limit without a new ontology abstraction and without Bajaj-specific production reasoning.

It also demonstrated that an apparently easy candidate can be rejected safely when a required semantic component is missing. Passing the cataract case therefore reflects disciplined manufacturing rather than metric-driven completion.

## Final conclusion

**CERTIFIED AND FROZEN.**

The Bajaj cataract SI-up-to-INR-10-lakh pressure case demonstrates cross-insurer reuse beyond the waiting-period semantic family through the existing generic Health certification/publication architecture.

No further tuning of this gate is justified. Future work should continue applying the manufacturing pattern to additional consequential Health knowledge pressure, and architecture should change only when real source pressure proves a generic gap.