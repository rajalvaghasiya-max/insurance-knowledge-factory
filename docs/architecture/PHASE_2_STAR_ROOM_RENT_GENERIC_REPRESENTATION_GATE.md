# Phase 2 — Star Room-Rent Generic Representation Gate

**Status:** CERTIFIED AND FROZEN  
**Date:** 2026-08-15

## Purpose

Exercise the already-governed Star Comprehensive room-rent rule against the generic Health topic-completeness and evidence contracts, with the specific goal of proving that the rule can be represented without product-identity-bearing production reasoning code.

This gate is not a new room-rent extractor, not a new ontology project, and not permission to change claim-adjudication behavior. It is a Phase-2 scaling/de-productization pressure case.

## Why this pressure case

The current Star Comprehensive room-rent certification preserves materially important product semantics:

- covered room/boarding/nursing and room-linked hospitalization expenses;
- categorical limit: Private Single A/C room;
- no separate monetary room-rent cap asserted;
- proportional consideration of room-linked expenses when the occupied room exceeds the permitted category;
- applicability limited to hospitalization expenses that vary based on room rent;
- no claim-payment guarantee.

Those semantics historically lived in `insurance_intelligence/rule_certification/star_health_room_rent.py`, a Star-specific Python certification module.

Phase-2 scaling has established the standing acceptance criterion that normal Health expansion should require:

```text
0 product-identity-bearing production reasoning code
```

The tested question was whether the existing generic contracts can carry the same semantics as governed data/evidence, allowing the Star-specific module to become compatibility/parity scaffolding rather than the production scaling pattern.

## Governed source under pressure

- Insurer: Star Health
- Product: Star Comprehensive
- Entity: `star_health:star_comprehensive`
- Current governed policy-wording SHA-256: `b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f`
- Existing governed room-rent evidence: page 9, section `II.1 In-patient Treatment`
- Existing source semantics include Private Single A/C room eligibility and proportional treatment of room-linked expenses.

No source identity or currentness change is part of this gate.

## Existing generic semantic capacity

The generic `coverage_limit` topic already defines the components required by this rule:

- `covered_subject`
- `limit_value`
- `limit_basis`
- `applicability_scope`
- optional `excess_consequence`

No new room-rent ontology abstraction was required.

## Implemented scaling path

The approved generic path demonstrated by this gate is:

```text
governed certification JSON
-> strict insurer-independent data loader
-> existing RuleCertificationExpectation
   + existing EvidenceResolverOutput
-> unchanged insurer-independent RuleCertificationRunner
```

Implemented artifacts:

- generic loader for governed certification case data;
- governed Star room-rent certification case record;
- parity tests comparing the governed-data-loaded case with the legacy Python case;
- unchanged generic runner.

The loader reuses existing contract builders and `EvidenceResolverOutput` validation and fails closed on unknown/invalid data rather than defining an alternative certification schema.

## Semantic parity result

The governed-data case preserves all certified semantics from the legacy Python case:

1. **Covered subject** — in-patient room, boarding, nursing, and room-linked hospitalization expenses.
2. **Categorical limit value** — Private Single A/C room; no monetary room-rent cap is fabricated.
3. **Limit basis** — policy-stated room category or actuals, whichever is less.
4. **Applicability scope** — hospitalization expenses that vary based on room rent occupied by the insured person.
5. **Excess consequence** — proportional consideration for room-linked expenses when the permitted category is exceeded.
6. **Claim guardrail** — the proportional mechanism does not itself establish claim admissibility or payment.
7. **Lineage** — source path, policy SHA, governed registration record, candidate identity, page 9, section, and evidence identity are preserved.

Parity tests require equality of the expectation and resolver-output contracts and run the governed-data case through the unchanged generic certification runner.

## Regression evidence

Focused migration set:

```text
18 passed
```

Legacy + governed-data + generic-runner parity set:

```text
26 passed
```

Broader closure regressions:

```text
insurance_intelligence : 2903 passed
health                 : 124 passed
factory_core           : 128 passed
regressions            : 0
```

No behavioral divergence was observed between the legacy Python fixture and governed-data-loaded case.

## Legacy module classification decision

`insurance_intelligence/rule_certification/star_health_room_rent.py` is retained as a **legacy compatibility/parity fixture and regression oracle**.

It is not the approved scaling pattern for onboarding future Health products.

The module documentation explicitly states that it must not be copied as the onboarding pattern. Future product semantics should be represented as governed data/evidence against insurer-independent contracts unless real product pressure proves a missing generic abstraction.

Deletion is intentionally deferred while the module remains useful as an independent parity oracle.

## Standing acceptance criterion

```text
Star room-rent governed representation
=
0 new Star-specific production reasoning code
```

Certified result:

```text
new product-identity-bearing production reasoning paths = 0
new room-rent semantic abstractions = 0
legacy Python fixture retained for parity = yes
governed-data scaling path proven = yes
```

## Architecture decision

**Decision: CERTIFY THE GOVERNED-DATA + GENERIC-CONTRACT REPRESENTATION AS THE HEALTH SCALING PATTERN FOR THIS RULE SHAPE.**

This certification is narrow:

- it proves that the Star room-rent certification case can be represented through governed data and existing generic contracts without semantic loss;
- it does not claim that every future room-rent rule will fit without additional generic semantic pressure;
- it does not authorize claim adjudication, publication, or inference of missing monetary limits;
- it does not make the legacy Star-specific module authoritative for new onboarding.

## Guardrails

- Do not change the certified Star source wording or SHA.
- Do not infer a monetary room-rent cap where the source states a room category.
- Do not generalize proportional deduction to expenses not governed by the room-linked scope.
- Do not convert this into claim adjudication.
- Do not weaken evidence authority, currentness, lineage, or completeness requirements.
- Do not add Star/product/source-hash branching to generic production code.
- Do not create a new room-rent ontology abstraction unless generic `coverage_limit` components prove insufficient under future independent pressure.
- Do not use the retained legacy fixture as the template for new product onboarding.
- No frontend, Motor, Life, database migration, or recommendation-productization scope.

## Measurements

Certified measurements:

- all five generic `coverage_limit` components represent the certified room-rent rule;
- material semantic residue not representable by the generic contracts: none observed;
- lineage/evidence parity with legacy case: preserved;
- governed-data certification through generic runner: PASS;
- focused regression sets: 18 passed, then 26 passed;
- broader regressions: 2903 insurance_intelligence, 124 health, 128 factory_core;
- new product-identity-bearing production-code paths: 0;
- existing Star-specific module demoted to compatibility/parity status: yes;
- adjudication behavior changed: no;
- publication behavior changed: no.

## Freeze rule

This gate is closed. Do not reopen it merely to remove the legacy fixture or optimize test structure. Revisit only if an independently governed Health product proves that the generic `coverage_limit` representation cannot preserve materially important room-rent semantics safely.
