# PolicyScna — MO-028C Health Benefit-Limit Generalization

## Status
Final pre-implementation design contract after independent architecture review and CTO adjudication.

## Objective
Generalize governed Health insurance benefit-limit/sub-limit semantics across materially different products without insurer/product-specific reasoning.

MO-028C is the first direct test that PolicyScna's generic knowledge architecture generalizes across semantic families, not merely across waiting-period products.

## Core separation

```text
LIMIT SEMANTICS
!= LIMIT VALUE
!= LIMIT APPLICABILITY
!= COST-SHARING INTERACTION
!= INSTANCE CALCULATION
```

A limit is not semantically complete merely because a currency or percentage value is known.

## Existing manufacturing baseline
The Health Field Registry already defines `currency_sub_limit` as a governed monetary-limit field with required benefit scope, optional Sum Insured-band scope, positive INR validation, extractor support, and production-candidate readiness. MO-028C extends semantics after governed extraction/review; it does not replace the extraction pipeline.

## Blocking design correction 1 — cost-sharing interaction
Two otherwise identical benefit limits may have materially different economic meaning depending on whether copay, deductible, or proportionate deduction applies before, after, independently, or not at all.

Example:

```text
Product A: cataract limit INR 50,000; 20% copay applies after the limit
Product B: cataract limit INR 50,000; copay exempt for that benefit
```

These must never normalize as equivalent.

### Closed interaction contract

```text
CostSharingMechanicType
- COPAY
- DEDUCTIBLE
- PROPORTIONATE_DEDUCTION

CostSharingRelationship
- APPLIES_BEFORE
- APPLIES_AFTER
- APPLIES_INDEPENDENTLY
- EXEMPT
- UNKNOWN

CostSharingInteractionRule
- mechanic_type
- relationship
- evidence reference(s)
```

A `BenefitLimitMechanic` may carry zero or more governed interaction rules.

### Comparison rule

```text
UNKNOWN INTERACTION
-> semantic representation may remain valid
-> direct/equivalent comparison MUST fail closed
```

Likewise, differing interaction rules prevent an equality conclusion even when the raw limit value is identical.

MO-028C represents interaction semantics only. It does not calculate insurer liability.

## Blocking design correction 2 — governed benefit identity
Cross-product comparison requires canonical benefit identity.

```text
raw product label
-> governed canonical benefit concept
```

A minimal governed contract is required before comparison:

```text
BenefitConcept
- concept_id
- canonical_name
- governed aliases
- false-friend / excluded aliases where needed
- governance/version metadata

BenefitConceptResolution
- RESOLVED
- AMBIGUOUS
- NOT_FOUND
```

No fuzzy best guess may enter governed comparison.

```text
AMBIGUOUS BENEFIT IDENTITY
-> COMPARISON BLOCKED
```

MO-028C may initially scope itself to benefits whose canonical identity is governable with this minimal contract. It must not fall back to product-specific name matching.

## Core semantic contract

```text
BenefitLimitMechanic
- benefit_concept_id
- limit_kind
- amount?
- currency?
- percentage?
- percentage_basis?
- floor_amount?
- ceiling_amount?
- period_scope
- sum_insured_band?
- value_domain_reference?
- cost_sharing_interactions[]
- applicability
- evidence
- ontology_version
```

## Limit kinds
Use only genuinely distinct semantic kinds:

```text
LimitKind
- FIXED_CURRENCY
- PERCENTAGE
- NO_LIMIT
- UP_TO_SUM_INSURED
- SCHEDULE_SELECTED
```

Do not encode floor/ceiling combinations into the enum.

### Composable percentage form

```text
kind = PERCENTAGE
percentage = <value>
percentage_basis = SUM_INSURED
floor_amount = optional
ceiling_amount = optional
period_scope = <scope>
```

This supports percentage-only, floor-only, ceiling-only, and floor+ceiling without combinatorial type growth.

## Period scope
Initial closed vocabulary may include only source-required values. Candidate values:

```text
PER_EVENT
PER_CLAIM
PER_DAY
PER_HOSPITALIZATION
PER_POLICY_YEAR
PER_MEMBER_PER_POLICY_YEAR
LIFETIME
AGGREGATE
UNSPECIFIED
```

`UNSPECIFIED` is explicit and must block equivalence against a mechanic whose period is known where period materially affects comparison.

```text
PER_DAY != PER_EVENT != PER_POLICY_YEAR
```

## NO_LIMIT rule

```text
ABSENCE OF EVIDENCE != NO_LIMIT
```

`NO_LIMIT` requires affirmative governed evidence. Missing, unlocated, ambiguous, or unrepresented source text remains unknown/not found/residue as appropriate.

## UP_TO_SUM_INSURED
`UP_TO_SUM_INSURED` is distinct from `NO_LIMIT`: the contract still has a ceiling linked to Sum Insured and may change when Sum Insured changes.

## Sum Insured bands
Band scope is a first-class applicability dimension.

```text
SumInsuredBand
- lower_bound?
- upper_bound?
- lower_inclusive
- upper_inclusive
- currency = INR
```

Raw wording remains in provenance; semantic bands are structured.

### Band-set validation
For the same benefit x variant x semantic role:

- overlapping bands are `VALIDATION_CONFLICT` unless source semantics explicitly permit simultaneous application;
- gaps remain explicit uncovered/NOT_FOUND regions;
- a gap never implies `NO_LIMIT`;
- inclusive/exclusive boundaries are material.

Examples:

```text
<= 10L and > 10L -> valid boundary partition
<= 10L and >= 10L -> overlap at 10L -> VALIDATION_CONFLICT
<= 10L and > 15L -> explicit gap 10L..15L, not unlimited coverage
```

## Schedule-selected limits and generic value domains
C4's schedule-resolution mechanism is reusable across families, but waiting-period-specific `DurationDomainReference` is not the generic abstraction.

MO-028C provides the second-family pressure required to introduce a narrow generic:

```text
ValueDomainReference
- semantic_fact_id / stable semantic identity
- ontology_version
- domain_kind
- applicability identity
- dependency/source version identity
```

The generic invariant from C6.4 remains:

```text
VALUE MODE IS DERIVED FROM DOMAIN-REFERENCE PRESENCE
```

Do not duplicate a `value_source = SCHEDULE_SELECTED` flag on the limit mechanic.

A schedule-selected limit with a valid governed domain is semantically representable but instance-bound until an authenticated instance source supplies the selected value.

## Shared aggregate limits
Shared pools must not be duplicated into each governed benefit.

Preferred future representation:

```text
SharedLimitPool
- pool identity
- governed amount/mechanic
- period/applicability

Benefit -> CONSUMES_FROM -> SharedLimitPool
```

MO-028C may represent the product-level pool and membership relation only. Claim-state remaining-balance accounting is explicitly later work.

Do not build N^2 pairwise `SHARES_LIMIT_WITH` edges if a first-class aggregate pool is needed by actual source pressure.

## Room rent and deductible boundaries

### First MO-028C target
Benefit-specific monetary limits/sub-limits, such as source-supported cataract, ambulance, maternity, organ-donor, modern-treatment, or similar clauses.

### Room rent
Room rent belongs near benefit-limit semantics but is intentionally deferred from the first slice because it combines category eligibility, percentage/fixed limits, per-day scope, and proportionate-deduction interaction. It is a strong later adversarial pressure case.

### Deductible
Deductible remains a separate cost-sharing family. It gates claim liability rather than merely capping one benefit and should follow after the interaction model is proven.

## Member scope
Do not add a generic member-scope axis speculatively. Add only under real source pressure.

## Formula boundary
Do not introduce a generic expression/formula language.

Closed structured fields such as percentage + basis + floor + ceiling are sufficient for the current semantic representation target.

MO-028C does not calculate final claim liability.

## Reuse boundary
Attempt to reuse unchanged:

- Generic Normative Inventory
- Residue Accounting
- Authority Resolution
- Publication Eligibility
- Coverage Registry
- C1 Resolution Status
- C2 dependency principles where a real dependency exists
- C5 Governance Integration
- canonical terminology/entity governance
- comparison safety boundary

Extract/reuse as generic pattern:

- C4 schedule-resolution pattern -> generic `ValueDomainReference`

Do not generalize blindly:

- WaitingPeriodResolutionCell
- WaitingPeriodStartBasis
- WaitingPeriodType
- other waiting-period-only contracts

## Source-first implementation rule

```text
SOURCE
-> high-recall normative inventory
-> atomic/source-sufficient propositions
-> reviewed mappings
-> residue accounting
-> only then semantic extension
```

Do not design every imaginable limit type in advance.

## Revised milestone sequence

### G0 — Source-pressure inventory and product selection
Select authoritative clauses that pressure the smallest useful set of limit semantics.

Target pressure dimensions:
- fixed benefit-specific INR limit;
- period scope;
- SI-band scope;
- percentage + optional bound if source-supported;
- cost-sharing interaction known vs unknown;
- benefit-concept identity variation;
- shared aggregate or schedule-selected only if real source pressure justifies inclusion.

### G1 — Minimal governed benefit-concept identity
Canonical concepts, aliases, ambiguity/not-found fail-closed behavior.

### G2 — Generic benefit-limit contracts
Limit kind, composable value fields, period scope, evidence, applicability.

### G3 — SI-band applicability and band-set validation
Boundary, overlap, gap behavior.

### G4 — Cost-sharing interaction semantics
Closed interaction rules and comparison fail-closed behavior.

### G5 — Generic mapper and residue accounting
Reviewed source-anchored mapping only.

### G6 — Generic value-domain/schedule reuse
Only if source pressure needs schedule-selected limits; otherwise defer.

### G7 — First product migration
Use the simplest sufficiently representative product.

### G8 — Second product migration
Add different source/limit shape.

### G9 — Adversarial product
Pressure identity, bands, interactions, and any unresolved family edge.

### G10 — Health benefit-limit generalization certification
Cross-product representability, governance, comparison safety, and zero product-identity reasoning.

## Core invariants

```text
LIMIT VALUE != LIMIT SEMANTICS
LIMIT != COST-SHARING INTERACTION
UNKNOWN INTERACTION != SAFE EQUIVALENCE
BENEFIT LABEL != BENEFIT IDENTITY
AMBIGUOUS BENEFIT IDENTITY -> COMPARISON BLOCKED
ABSENCE != NO_LIMIT
BAND GAP != NO_LIMIT
BAND OVERLAP -> VALIDATION_CONFLICT
PERCENTAGE + FLOOR + CEILING = COMPOSITION, NOT ENUM COMBINATION
PER DAY != PER EVENT != PER YEAR
SCHEDULE-SELECTED LIMIT -> GOVERNED VALUE DOMAIN -> INSTANCE-BOUND UNTIL RESOLVED
SHARED AGGREGATE != DUPLICATED INDIVIDUAL LIMITS
LIMIT != CLAIM SETTLEMENT
PRODUCT IDENTITY = DATA, NOT REASONING
```

## Explicit non-goals
MO-028C will not:

- calculate final claim settlement;
- determine claim admissibility;
- combine limits/copay/deductible into insurer liability;
- rank or recommend products;
- add customer-specific advice;
- introduce fuzzy benefit matching in governed comparison;
- introduce a generic formula language;
- implement deductible semantics;
- start with room-rent complexity;
- generalize to Motor/Life;
- build UI.

## Completion criterion
MO-028C succeeds when materially different Health benefit-limit clauses can move through source-first inventory, generic semantic representation, explicit applicability, explicit cost-sharing interaction, governed publication, and comparison-safe projection with zero insurer/product-specific reasoning and no silent equality across materially different mechanics.
