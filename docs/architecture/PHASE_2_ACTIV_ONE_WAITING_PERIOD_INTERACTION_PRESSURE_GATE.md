# Phase 2 — Activ One Waiting-Period Interaction Pressure Gate

**Status:** ACTIVE — SEMANTIC PRESSURE COMPLETE; REGRESSION CLOSURE PENDING  
**Date:** 2026-08-15

## Purpose

Exercise the current governed Aditya Birla Activ One policy wording against the existing generic Health waiting-period extraction and semantic contracts, with particular pressure on interactions between base waiting periods, optional reductions, schedule-selected alternatives, and benefit-specific waivers.

This is not a new waiting-period subsystem and is not a legacy Activ One/NXT migration exercise.

## Governed source under pressure

- Insurer: Aditya Birla Health Insurance
- Product: Activ One
- Entity: `aditya_birla_health:activ_one`
- UIN: `ADIHLIP24097V012324`
- Current governed policy-wording SHA-256: `38bb879030d905bd6f90915915f1c2e22e27ebe5bc980bba766c69c7ecd90a16`
- Archive path: `archive/raw_pdf/aditya_birla_health/policy_wording/activ_one_current_20260815.pdf`
- Canonical parsed artifact: `processed/pdf_parse/38bb879030d905bd6f90915915f1c2e22e27ebe5bc980bba766c69c7ecd90a16.json`

The historical missing Activ One policy wording SHA `d772...` and the historical Activ One NXT intelligence artifacts are not authority for this gate and must not be imported as current truth.

## Why this pressure case

The three-product review-scaling replication checkpoint closed the cross-insurer empirical review-routing gap. The next useful Health pressure should therefore exercise a materially different semantic interaction rather than repeat currency extraction.

The current Health intelligence coverage review still identifies Activ One waiting periods as not automated, while the current governed wording contains multiple interacting waiting-period structures. Existing generic waiting-period contracts already model base waits, reductions, waivers, schedule/table delegation, continuity, and selected alternatives, so the correct test is whether current Activ One can be represented by those contracts without product-specific runtime logic.

## Existing generic path

The starting evidence path is:

`current governed parsed wording -> waiting-period duration candidates -> evidence consolidation -> human semantic review against existing waiting-period contracts`

Existing primitives:

- `WaitingPeriodDurationParser`
- `WaitingPeriodCandidateConsolidator`
- `insurance_intelligence.concepts.waiting_periods.policy`

The extraction/consolidation stages are evidence-only and do not establish applicability or publication.

## Standing acceptance criterion

```text
current Activ One waiting-period pressure
=
0 product-identity-bearing production code
```

A new generic abstraction is allowed only if the current governed wording proves that the existing waiting-period contract cannot safely represent a real semantic interaction.

## Measured extraction pressure

### Baseline

The original generic duration primitive returned:

```text
Candidates: 0
Consolidated groups: 0
```

This was not absence of waiting-period evidence. The current native PDF text exposed two generic extraction limitations:

1. duration-first initial-wait wording: `30-day Waiting Period (Code-Excl03)`;
2. a specified-disease duration appearing later in the same normative exclusion clause rather than immediately after the waiting-period label.

The native PDF also retained the `ﬁ` ligature in `Speciﬁed`, which prevented an ASCII-only pattern from matching the real clause.

### Generic extraction corrections

The parser was extended generically to:

- recognize duration-first `Code-Excl03` initial-wait headings;
- recognize an explicit duration later in the same specified-disease/procedure exclusion clause;
- normalize common PDF ligatures while retaining source-character provenance;
- continue refusing unrelated downstream durations;
- continue refusing schedule/table-delegated waiting-period values.

No insurer identity, product identity, source hash, or Activ One-specific branch was introduced.

### Post-correction workload

The current governed source produced:

```text
Duration candidates: 4
Consolidated groups: 2
```

#### Group 1 — initial waiting period

```text
Category: initial
Duration: 30 days
Occurrences: 3
Pages: 11, 20, 38
Flags: repeated_same_duration, repeated_across_pages
```

The three occurrences are semantically different contexts and therefore MUST NOT be flattened into three independent base facts:

- page 11: base `30-day Waiting Period (Code-Excl03)` exclusion;
- page 20: language re-applying D.1.1/D.1.2/D.1.3 as first-year waiting periods for the relevant insured person/context;
- page 38: language stating D.1.1 and D.1.3 shall not apply to the extent of a benefit.

The repeated duration therefore proves that a scalar-only model would lose material interaction semantics.

#### Group 2 — specified disease/procedure waiting period

```text
Category: specified_disease_or_procedure
Duration: 24 months
Occurrences: 1
Page: 10
Flags: schedule_or_option_layout_possible
```

The bounded clause explicitly states exclusion until expiry of 24 months of continuous coverage and continues into sum-insured-enhancement/applicability language. The duration is a review candidate only; the extraction stage does not establish a published product fact.

## Explicit unresolved residue

### PED base duration

The current policy wording does not safely yield a numeric PED duration from the normative clause alone. It delegates the duration to the Policy Schedule / Product Benefit Table.

Therefore:

```text
PED numeric duration from policy wording alone = UNRESOLVED
```

No historical Activ One value may be substituted and no table value may be bound by reading-order guesswork.

### Optional reductions / selected alternatives

The current wording contains optional waiting-period reduction structures, including PED and specified-disease reduction concepts, but schedule-selected alternatives require explicit applicability/binding evidence. They remain review-residue unless that binding is governed.

### Benefit-scoped waiver / override

The page-38 evidence demonstrates that waiting-period exclusions can be non-applicable to the extent of a benefit. This is not a second base duration. It is a relationship/override semantic that must remain scoped to the relevant benefit.

## Existing semantic model fitness

No new waiting-period abstraction is required.

The existing generic policy already declares the semantic effects required by this pressure case:

- `DURATION`
- `START_BASIS`
- `SCOPE`
- `EXCEPTION`
- `CONTINUITY`
- `PORTABILITY`
- `SUM_INSURED_ENHANCEMENT`
- `WAIVER`
- `REDUCTION`
- `APPLICABILITY`
- `OPTIONAL_COVER_INTERACTION`
- `BENEFIT_SCOPED_OVERRIDE`
- `CROSS_CONCEPT_RELATIONSHIP`
- `RENEWAL_OR_REINSTATEMENT_EFFECT`
- `EFFECTIVE_DATE_OR_VERSION`

The existing relationship vocabulary also already permits `MODIFIES`, `WAIVES`, `OVERRIDES`, `DEPENDS_ON`, `APPLIES_WHEN`, `INTERACTS_WITH`, `LIMITED_BY`, and in v2 `DERIVES_FROM`.

Accordingly, this pressure case exposed an extraction-coverage defect, not a semantic-representation defect.

## Architecture decision

**Decision: EXISTING WAITING-PERIOD SEMANTIC MODEL IS SUFFICIENT.**

Do not create a new interaction abstraction from Activ One pressure.

Do not flatten:

- base duration;
- reapplication/reset behavior;
- optional reduction;
- benefit-scoped waiver;
- schedule-selected alternative;
- sum-insured-enhancement behavior

into one product-level waiting-period scalar.

## Product-specific production code

```text
0 product-identity-bearing production code
```

The production changes are generic parser/normalization improvements forced by real current-product evidence.

## Adjudication / publication

```text
Adjudication: none
Publication: none
```

Candidate extraction and consolidation remain evidence-review stages only.

## Guardrails

- Use only the current governed `38bb...` wording for current semantic evidence.
- Do not copy values from historical Activ One NXT intelligence as facts.
- Do not flatten optional reductions, waivers, or benefit-scoped waits into one scalar product waiting period.
- Do not infer a schedule-selected option unless the governed evidence binds it.
- Preserve benefit scope and interaction semantics explicitly.
- Unknown schedule/table binding remains unresolved and fail-closed.
- No automatic adjudication or publication.
- No insurer/product-specific production branch, source-hash branch, or threshold change.
- No frontend, Motor, Life, database migration, recommendation-productization, or public-launch scope.

## Measurements

Measured at this checkpoint:

- duration candidates: 4;
- consolidated groups: 2;
- initial 30-day group: 3 occurrences across pages 11, 20, 38;
- specified-disease/procedure 24-month group: 1 occurrence on page 10;
- PED numeric duration: unresolved because delegated to schedule/product-benefit table;
- optional/schedule-selected reductions: unresolved until applicability binding is governed;
- benefit-scoped waiver/override: representable by existing semantic contract, not flattened into duration;
- new generic semantic abstraction: 0;
- product-identity-bearing production-code changes: 0;
- adjudication side effects: 0;
- publication side effects: 0.

## Exit condition

Semantic pressure and architecture mapping are complete. The gate closes when relevant regressions are green and this measured result is certified without resolving schedule/table applicability by guesswork.
