# Phase 2 — Star Room-Rent Generic Representation Gate

**Status:** ACTIVE — DATA-DRIVEN SEMANTIC MIGRATION PRESSURE STARTED  
**Date:** 2026-08-15

## Purpose

Exercise the already-governed Star Comprehensive room-rent rule against the generic Health topic-completeness and evidence contracts, with the specific goal of proving that the rule can be represented without product-identity-bearing production reasoning code.

This gate is not a new room-rent extractor, not a new ontology project, and not permission to change claim-adjudication behavior. It is a Phase-2 scaling/de-productization pressure case.

## Why this pressure case

The current Star Comprehensive room-rent certification already preserves materially important product semantics:

- covered room/boarding/nursing and room-linked hospitalization expenses;
- categorical limit: Private Single A/C room;
- no separate monetary room-rent cap asserted;
- proportional consideration of room-linked expenses when the occupied room exceeds the permitted category;
- applicability limited to hospitalization expenses that vary based on room rent;
- no claim-payment guarantee.

However, those semantics currently live in `insurance_intelligence/rule_certification/star_health_room_rent.py`, a Star-specific production module.

Phase-2 scaling has established the standing acceptance criterion that normal Health expansion should require:

```text
0 product-identity-bearing production reasoning code
```

The correct next test is therefore whether the existing generic contracts can carry the same semantics as governed data/evidence, allowing the Star-specific module to become compatibility/audit scaffolding rather than the production scaling pattern.

## Governed source under pressure

- Insurer: Star Health
- Product: Star Comprehensive
- Entity: `star_health:star_comprehensive`
- Current governed policy-wording SHA-256: `b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f`
- Existing governed room-rent evidence: page 9, section `II.1 In-patient Treatment`
- Existing source semantics include Private Single A/C room eligibility and proportional treatment of room-linked expenses.

No source identity or currentness change is part of this gate.

## Existing generic semantic capacity

The generic `coverage_limit` topic already defines the components needed for this rule:

- `covered_subject`
- `limit_value`
- `limit_basis`
- `applicability_scope`
- optional `excess_consequence`

The gate must first attempt to express the Star room-rent rule entirely through these existing generic components and existing evidence/lineage contracts.

A new abstraction is allowed only if real semantics cannot be represented without material loss.

## Standing acceptance criterion

```text
Star room-rent governed representation
=
0 new Star-specific production reasoning code
```

The existing Star-specific certification module may be retained temporarily for regression parity, but it must not be treated as the future onboarding template.

## Semantic parity target

A generic/data-driven representation must preserve at minimum:

1. **Covered subject** — room, boarding, nursing, and room-linked hospitalization expenses.
2. **Categorical limit value** — Private Single A/C room; do not fabricate a monetary room cap.
3. **Limit basis** — policy-stated room category or actuals, whichever is less, as expressed by the governed wording.
4. **Applicability scope** — hospitalization expenses that vary based on room rent occupied by the insured person.
5. **Excess consequence** — proportional consideration for room-linked expenses when the permitted room category is exceeded.
6. **Claim guardrail** — this rule does not itself establish claim admissibility or payment.
7. **Lineage** — source/page/section/hash/evidence identity must remain traceable.

## Guardrails

- Do not change the certified Star source wording or SHA.
- Do not infer a monetary room-rent cap where the source states a room category.
- Do not generalize proportional deduction to expenses not governed by the room-linked scope.
- Do not convert this into claim adjudication.
- Do not weaken evidence authority, currentness, lineage, or completeness requirements.
- Do not add Star/product/source-hash branching to generic production code.
- Do not create a new room-rent ontology abstraction unless generic `coverage_limit` components prove insufficient.
- No frontend, Motor, Life, database migration, or recommendation-productization scope.

## Measurements

Record at minimum:

- whether all five generic `coverage_limit` components can represent the existing certified rule;
- any semantic residue not representable by the existing contracts;
- lineage/evidence parity with the current certification case;
- completeness outcome under the generic topic definition;
- number of new product-identity-bearing production-code paths;
- whether the existing Star-specific module can be demoted to compatibility/audit status;
- regressions across `tests/insurance_intelligence`, `tests/health`, and relevant `tests/factory_core` coverage.

## Exit condition

This gate closes when the existing certified Star room-rent semantics have been represented through generic/data-driven contracts with no material semantic loss, lineage remains governed, no product-specific production path is introduced, relevant regressions are green, and the future scaling status of the old Star-specific certification module is explicitly decided.
