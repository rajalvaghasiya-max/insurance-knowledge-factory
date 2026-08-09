# MO-028B.G0 — Normative Inventory & Residue Gate Specification

Status: DRAFT FOR CERTIFICATION
Milestone: MO-028B.G0
Scope: Generic insurance knowledge architecture

## 1. Purpose

PolicyScna is moving from product-specific scaffolding toward a generic, product-as-data architecture. This specification defines the safety mechanism that makes that transition acceptable: every publishable insurance fact must be traceable to an independent source-anchored normative inventory, and any materially relevant normative content that cannot be represented must remain visible as residue and block only the affected publishable unit.

The residue gate is not an extraction-confidence check and is not a schema validator. It is an accounting control designed to detect representational inadequacy, relevance misattribution, uncaptured exceptions, uncaptured modifiers, uncaptured relationships, stale source dependencies, and unresolved authority conflicts.

The architecture must prefer NOT_YET_REPRESENTABLE over a well-formed but semantically incomplete fact.

## 2. Architectural doctrine

### 2.1 Product onboarding rule

A new product may add governed data, evidence, reviewed facts, applicability dimensions, and source registrations.

A new insurance behavior may add reusable semantic capability, a reusable relationship type, or a generic ontology/schema extension.

A new product must not add product-identity-bearing reasoning code such as insurer-name, product-name, UIN, or product-reference conditionals inside generic inference, publication, comparison, or decision-support logic.

### 2.2 Publication rule

A publishable unit is publishable only when all of the following are true:

- product identity is resolved;
- applicable source authority is resolved;
- relevant source version is current for the applicability interval;
- normative inventory coverage accounting is complete;
- semantic representation is adequate for that publishable unit;
- relationships affecting that unit are represented or explicitly accounted for;
- material residue for that unit is zero;
- no unresolved equal-authority conflict remains;
- required human/governed review is satisfied;
- ontology, source, regulatory overlay, and review dependencies are version-bound.

## 3. Core principles

1. **Source before schema.** Materiality is determined from source consequences, not from fields currently available in the ontology.
2. **Independent inventory.** The normative inventory path must be independently constructed and higher-recall than the semantic mapper.
3. **No silent disappearance.** Every normative unit in the relevance envelope must end in an explicit accounting state.
4. **Finest publishable unit.** Residue blocks only the smallest unit whose correctness depends on the residue.
5. **Relationships are facts.** WAIVES, MODIFIES, OVERRIDES, DEPENDS_ON, APPLIES_WHEN, INTERACTS_WITH, LIMITED_BY, and future relationship types require evidence and governance equivalent to scalar facts.
6. **Applicability is first-class.** Variant, source version, sum-insured band, geography/zone, effective date, optional-cover state, policy tenure, insured-person state, and other relevant dimensions travel through evidence, semantics, relationships, residue, and publication.
7. **Authority is policy, not metadata.** Source authority must be resolved by governed rules, including regulatory overlays above product documents.
8. **Source and ontology lifecycle are independent.** Source supersession invalidates derived facts even when the ontology is unchanged; ontology evolution may require recertification even when the source is unchanged.

## 4. Definitions

### 4.1 Normative content

Normative content is source text that can change the rights, obligations, eligibility, exclusions, limits, timing, applicability, interaction, modification, waiver, continuity, claim treatment, or interpretation of an insurance concept.

Examples for waiting periods include duration, start point, covered/excluded scope, accident exception, continuity rule, portability credit, sum-insured enhancement treatment, optional reduction, benefit-scoped waiver, longer-wait interaction, renewal behavior, and effective-date constraints.

### 4.2 Normative unit

A `NormativeUnit` is the smallest source-anchored statement or coherent clause fragment that carries one or more normative consequences and can be independently accounted for.

Minimum contract:

```text
NormativeUnit
  normative_unit_id
  concept_relevance[]
  source_reference
  source_document_id
  source_document_version_id
  source_hash
  source_locator
  source_page / structural_locator
  exact_excerpt
  excerpt_hash
  normative_categories[]
  applicability
  authority_class
  effective_interval
  inventory_method
  inventory_confidence
```

`normative_categories` are consequence-oriented rather than schema-oriented. For waiting periods the initial set is:

```text
DURATION
START_BASIS
SCOPE
EXCEPTION
CONTINUITY
PORTABILITY
SUM_INSURED_ENHANCEMENT
WAIVER
REDUCTION
APPLICABILITY
OPTIONAL_COVER_INTERACTION
BENEFIT_SCOPED_OVERRIDE
CROSS_CONCEPT_RELATIONSHIP
RENEWAL_OR_REINSTATEMENT_EFFECT
EFFECTIVE_DATE_OR_VERSION
OTHER_NORMATIVE_EFFECT
```

`OTHER_NORMATIVE_EFFECT` is intentionally retained so the inventory can flag behavior that the current ontology does not yet understand.

### 4.3 Concept relevance envelope

A `ConceptRelevanceEnvelope` defines source locations and search classes that can normatively affect a concept. It must not be limited to the obvious named section.

For waiting periods, the baseline envelope includes:

- standard exclusions;
- definitions referenced by exclusions;
- product benefit tables / schedules;
- optional covers and riders;
- renewal, continuity, portability, migration and reinstatement clauses;
- benefit-specific provisions that waive or modify exclusions;
- endorsements and addenda;
- product-version or variant applicability tables;
- regulatory overlays that can alter enforceability or interpretation.

The envelope is generic concept policy. Product-specific evidence may expand the observed locations but must not shrink the governed baseline envelope without review.

## 5. Independent normative inventory

### 5.1 Separation from semantic mapping

The inventory process and semantic mapping process must not share a single recognition decision whose miss would suppress both mapping and residue.

Required separation:

```text
Source
  ├── High-recall normative inventory path
  └── Structured semantic mapping path
```

The two paths may reuse low-level document parsing and canonical source identifiers, but they must have distinct selection objectives and independently testable outputs.

The inventory asks:

> Could this source statement materially affect the insurance concept or its applicability?

The mapper asks:

> Can this source statement be represented as a certified semantic fact or relationship under the current ontology?

### 5.2 Inventory recall posture

The inventory is intentionally conservative and high-recall. False-positive normative units are acceptable if they are explicitly accounted for as non-applicable, duplicate/corroborating, or non-material after review. False-negative inventory omissions are safety failures.

### 5.3 Inventory evidence class

A normative inventory record is not itself proof of an insurance fact. It is evidence of *source coverage accounting*. It must therefore carry:

- inventory method/version;
- source version/hash;
- deterministic anchors where available;
- review state;
- provenance sufficient to reproduce why the unit entered the inventory.

## 6. Materiality

Materiality must be determined from possible insurance consequence, not current ontology fields.

A normative unit is material to a publishable unit if changing, omitting, or misunderstanding that unit could alter at least one of:

- duration or monetary value;
- start/end condition;
- eligibility;
- exclusion or inclusion scope;
- exception;
- waiver/reduction/override;
- continuity or portability treatment;
- sum-insured treatment;
- variant / geography / band / tenure applicability;
- optional-cover state;
- effective date or version applicability;
- interaction with another concept;
- interpretation of the published statement.

A unit whose consequence is unknown is **not** automatically immaterial. It must enter `OTHER_NORMATIVE_EFFECT` and remain blocking until classified or explicitly reviewed as non-material.

## 7. Applicability model

Applicability is a cross-cutting axis, not a later enrichment step.

Baseline `ApplicabilityKey`:

```text
ApplicabilityKey
  product_reference
  product_version_reference
  variant_reference? 
  uin?
  sum_insured_band?
  geography_or_zone?
  policy_tenure?
  optional_cover_state?
  insured_person_state?
  effective_from?
  effective_to?
  additional_dimensions{}
```

The model must allow partially specified applicability on source evidence and progressively refined applicability after review.

No component may assume that a concept has a single scalar value for the whole product when source evidence proves dimensional variation.

## 8. Semantic facts and relationship facts

### 8.1 SemanticFact

```text
SemanticFact
  semantic_fact_id
  concept
  sub_concept
  mechanic
  applicability
  value / structured_mechanic
  evidence_refs[]
  authority_resolution
  ontology_version
  effective_interval
  review_status
```

### 8.2 RelationshipFact

```text
RelationshipFact
  relationship_fact_id
  relationship_type
  source_concept
  target_concept
  condition
  applicability
  evidence_refs[]
  authority_resolution
  ontology_version
  effective_interval
  review_status
```

Initial relationship vocabulary:

```text
MODIFIES
WAIVES
OVERRIDES
DEPENDS_ON
APPLIES_WHEN
INTERACTS_WITH
LIMITED_BY
```

Relationship vocabulary may expand only as reusable semantic capability, never as product-identity-bearing branching.

Relationships require their own evidence accounting and residue handling. A relationship referenced by multiple concepts is governed once and linked into each affected publishable unit.

## 9. Coverage accounting states

Every normative unit relevant to a publishable unit must resolve to exactly one primary accounting state:

```text
MAPPED
MAPPED_AS_RELATIONSHIP
EXPLICITLY_NON_APPLICABLE
DUPLICATE_OR_CORROBORATING
DEFERRED_WITH_REASON
NOT_YET_REPRESENTABLE
CONFLICTED
SOURCE_STALE
```

### 9.1 State semantics

- `MAPPED`: represented by one or more semantic facts.
- `MAPPED_AS_RELATIONSHIP`: represented by a governed relationship fact.
- `EXPLICITLY_NON_APPLICABLE`: reviewed and proven not applicable to the current publishable unit/cell.
- `DUPLICATE_OR_CORROBORATING`: adds no unique normative consequence and is linked to the primary mapped unit.
- `DEFERRED_WITH_REASON`: intentionally withheld pending bounded review; blocks affected publication unless policy explicitly permits partial publication elsewhere.
- `NOT_YET_REPRESENTABLE`: source consequence is understood but current ontology cannot faithfully encode it.
- `CONFLICTED`: unresolved conflict remains after authority resolution policy.
- `SOURCE_STALE`: source/version dependency is superseded or no longer valid for the target applicability interval.

No unaccounted state exists.

## 10. Residue

A `ResidueRecord` exists when a material normative unit affecting a publishable unit is not in a non-blocking accounting state.

```text
ResidueRecord
  residue_id
  normative_unit_id
  affected_publishable_unit_id
  applicability
  residue_type
  accounting_state
  reason
  detected_by
  ontology_version
  source_version
  review_status
```

Initial `residue_type` taxonomy:

```text
UNMAPPED_NORMATIVE_CONTENT
UNREPRESENTABLE_SEMANTIC
UNRESOLVED_RELATIONSHIP
UNRESOLVED_APPLICABILITY
UNRESOLVED_AUTHORITY_CONFLICT
SOURCE_SUPERSEDED
UNKNOWN_NORMATIVE_EFFECT
```

Residue is not a boolean property of a whole document or whole product.

## 11. Finest publishable unit

Publication gating occurs at the smallest unit for which a statement can be independently correct.

For waiting periods the baseline unit is:

```text
waiting_period_type × applicability_cell × source/effective-version interval
```

Examples:

```text
INITIAL × base variant × 2025 wording
PED × base variant × 2025 wording
SPECIFIC_DISEASE_PROCEDURE × base variant × optional-reduction=OFF × 2025 wording
SPECIFIC_DISEASE_PROCEDURE × base variant × optional-reduction=ON × 2025 wording
```

A residue affecting only the optional-reduction-on cell must not block the base initial waiting-period unit.

Coverage Registry state must distinguish at least:

```text
CERTIFIED
PARTIAL
CONFLICTED
NOT_YET_REPRESENTABLE
SOURCE_STALE
NOT_AUTOMATED
```

`NOT_YET_REPRESENTABLE` must never be collapsed into absence/no-benefit.

## 12. Residue and applicability strategy

The default strategy is source-clause accounting before cell explosion, followed by applicability projection.

Process:

1. inventory normative source clauses once;
2. bind each normative unit to the broadest justified applicability expression;
3. map semantic/relationship representation;
4. project into affected publishable applicability cells;
5. propagate residue only to cells whose correctness depends on that normative unit.

This avoids naive enumeration of the full combinatorial lattice while preserving cell-specific blocking.

If applicability cannot be determined sufficiently to know affected cells, the unit enters `UNRESOLVED_APPLICABILITY` and blocks all plausibly affected cells, not the entire unrelated concept surface.

## 13. Source authority resolution

Authority is governed policy.

Baseline tiers are concept- and jurisdiction-aware but follow this structure:

```text
Binding regulatory / statutory overlay
    ↓
Filed / authoritative policy wording and endorsements
    ↓
Policy schedule / product benefit table where wording delegates value to schedule
    ↓
Customer information sheet / mandated summary
    ↓
Prospectus
    ↓
Brochure / marketing material
    ↓
Unverified secondary material
```

Rules:

- higher authority may override lower authority for effective interpretation;
- contract/source facts are preserved even when a regulatory overlay changes legal effect;
- equal-authority material contradictions fail closed;
- authority resolution is applicability- and date-sensitive;
- no resolver may silently choose a winner among unresolved equal-authority sources.

Published interpretation should be able to preserve:

```text
contract_fact
regulatory_overlay
resulting_effective_interpretation
```

## 14. Source lifecycle and invalidation

Ontology lifecycle and source lifecycle are independent.

A published unit depends on:

```text
ontology_version
source_document_id
source_document_version_id
source_hash
regulatory_overlay_version(s)
review_decision_version
publication_policy_version
```

Source supersession flow:

```text
new authoritative source / endorsement / filing
  → supersession detected
  → affected publication dependencies identified
  → affected units marked SOURCE_STALE
  → re-inventory / remap / re-review
  → republish only after gates pass
```

Historical source versions remain retained for historical-policy / claim-date interpretation.

## 15. Ontology evolution

When residue proves that the current ontology cannot faithfully represent a source consequence:

1. publication remains blocked only for affected units;
2. create a reusable ontology-gap record;
3. implement a product-neutral semantic capability;
4. version the ontology;
5. identify previously published units that may be affected by the new semantics;
6. migrate/revalidate them;
7. recertify comparisons where semantic compatibility changed.

Ontology expansion is legitimate new Python/code when it is reusable semantic capability. Product-identity-bearing branching is not.

## 16. Waiting-period G0 specialization

The first certification target is waiting periods because Star Comprehensive and Activ One NXT already expose:

- base durations;
- schedule-defined duration values;
- accident exceptions;
- portability continuity credits;
- sum-insured enhancement behavior;
- optional reductions;
- benefit-scoped waivers;
- interactions between PED and specific-disease waiting periods.

The waiting-period relevance envelope must inventory at minimum:

```text
D.1.x exclusion clauses
product benefit table / schedule duration rows
optional waiting-period reduction covers
benefit-specific exclusion waivers
renewal / continuity / portability provisions
sum-insured enhancement provisions
cross-references between PED and specific-disease waits
relevant definitions
regulatory overlays where applicable
```

The inventory must not assume that the base exclusion clause contains the duration value; Activ One NXT demonstrates that D.1.1 can delegate duration to the Product Benefit Table.

## 17. Telemetry — collect now, act later

MO-028B.G records telemetry but does not yet implement risk-tiered review.

Capture:

```text
normative_units_total
normative_units_by_category
mapped_units
relationship_mapped_units
residue_count
residue_rate
residue_type_counts
ontology_gap_count
authority_conflict_count
source_stale_count
manual_review_count
review_disagreement_count
concept
insurer
product_family
source_authority_class
inventory_method_version
```

MO-029 may use this evidence to design risk-tiered review.

## 18. Fail-closed rules

Publication of an affected unit must fail closed when any of the following is true:

- a material normative unit has no accounting state;
- material residue exists;
- normative consequence is unknown;
- applicability cannot be narrowed enough to guarantee correctness;
- required relationship cannot be represented;
- equal-authority conflict remains unresolved;
- source dependency is stale;
- regulatory overlay applicability is unresolved where the overlay may materially alter the interpretation;
- ontology migration required by the unit is incomplete;
- human review required by governance has not been satisfied.

Failures must be typed and explainable. They must not be converted to generic `MISSING` or silently omitted from comparison.

## 19. Non-goals for G0

G0 does not:

- automate legal conclusions;
- implement risk-tiered review;
- publish new waiting-period facts;
- promote Star or Activ One Coverage Registry status;
- implement insurer-specific residue rules;
- build a generic rules DSL;
- replace human review for novel semantic residue.

## 20. Certification requirements

G0 architecture is certifiable only if tests/spec checks prove at least the following scenarios.

### 20.1 Independent inventory

A clause omitted by semantic mapping can still appear in the normative inventory and therefore create residue.

### 20.2 Unknown semantic effect

A source clause with a material but unknown consequence is classified `OTHER_NORMATIVE_EFFECT` / `UNKNOWN_NORMATIVE_EFFECT`, not ignored.

### 20.3 Optional modification separation

Base waiting period and optional reduction are separate normative units and separate applicability states.

### 20.4 Benefit-scoped waiver relationship

A chronic-care waiver becomes a governed `WAIVES` relationship and affects only applicable cells.

### 20.5 Schedule-delegated value

A base PED clause delegating duration to a product benefit table is incomplete until the schedule/table normative unit is mapped and authority-resolved.

### 20.6 Fine-grained blocking

Residue in `SPECIFIC_DISEASE_PROCEDURE × optional_cover=ON` does not block a clean `INITIAL × base` publication.

### 20.7 Equal-authority conflict

Two equal-authority contradictory normative units produce `CONFLICTED` residue and no automatic winner.

### 20.8 Regulatory overlay

Contract fact and regulatory overlay are preserved separately and an unresolved date-sensitive overlay blocks effective interpretation.

### 20.9 Source supersession

Superseding a source marks dependent units `SOURCE_STALE` without deleting historical provenance.

### 20.10 Ontology inadequacy

A product that introduces a genuinely new mechanic cannot be forced into an existing scalar field; it produces `NOT_YET_REPRESENTABLE` until reusable ontology support exists.

## 21. Acceptance criterion for scalable onboarding

The scalable onboarding criterion is:

> A new product requires zero product-identity-bearing reasoning code. If its source contains a genuine insurance behavior that the ontology cannot represent, the residue gate must fail closed and trigger reusable ontology work rather than permit lossy data encoding.

For hostile generalization certification, success means:

- product identity added as data;
- sources registered as data;
- no insurer/product branch added to generic logic;
- all material normative units accounted for;
- zero material residue in units declared certified;
- remaining unsupported units explicitly surfaced as `NOT_YET_REPRESENTABLE`, `CONFLICTED`, or `SOURCE_STALE` rather than omitted.

## 22. Immediate implementation sequence after G0 approval

G0 is architecture-first. After certification, implementation proceeds as a set of co-designed cross-cutting contracts rather than a linear product-specific pipeline:

```text
Generic core
  - NormativeUnit / EvidenceCandidate
  - SemanticFact
  - PublicationUnit

Cross-cutting applicability
  - ApplicabilityKey / applicability expressions

Cross-cutting relationships
  - RelationshipFact / governed relationship vocabulary

Cross-cutting residue gate
  - coverage accounting
  - residue propagation
  - typed publication blockers

Authority/lifecycle
  - source authority policy
  - regulatory overlays
  - source supersession
  - ontology version dependencies
```

Only after these contracts are certified should Star and Activ One NXT be migrated to the generic waiting-period pipeline.
