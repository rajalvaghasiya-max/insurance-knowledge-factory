# PolicyScna — MO-028C.G1.1 Existing Terminology Capability Audit

## Purpose

Determine whether the existing MO-024 terminology stack can serve as the governed identity layer for MO-028C benefit concepts, or whether a separate subsystem is required.

## Audit conclusion

**Reuse the existing terminology stack. Do not create a second resolver/ontology subsystem.**

The existing architecture already provides the core mechanism we need:

- stable canonical concept IDs via `CanonicalConceptFamily` / `CanonicalConceptDefinition`;
- exact normalised matching only;
- explicit `RESOLVED`, `AMBIGUOUS`, and unresolved states;
- immutable registry snapshots;
- evidence-bearing product terms and governed product-scoped alias records;
- deterministic resolution with no fuzzy ranking, embeddings, LLM inference, or runtime self-learning.

However, the current concept-language surface is **not sufficient as-is** for G1 because canonical concept definitions still carry `aliases`, `customer_phrases`, and `insurer_terms` as bare strings. Those strings have no per-alias evidence reference, review-decision binding, governance version, or independent recertification identity.

The existing `GovernedTerminologyAlias` does carry evidence/review/publication state, but it resolves a product-scoped alias to an `InsurerMarketingTerm`. It is therefore the right precedent/mechanism, not the final contract for canonical benefit-concept alias membership.

## Requirement-by-requirement result

### 1. Stable benefit concept IDs

**SUPPORTED.**

`CanonicalConceptFamily.concept_family_id` already provides stable governed concept identity. G1 should extend the existing canonical concept catalogue with Health benefit concepts rather than introduce another identity namespace subsystem.

Preferred IDs remain domain-scoped, e.g.:

- `health:benefit:cataract`
- `health:benefit:road_ambulance`
- `health:benefit:air_ambulance`
- `health:benefit:ayush`
- `health:benefit:modern_treatment_group`

No new concept-ID mechanism is required.

### 2. Per-alias governed provenance

**NOT SUPPORTED FOR CANONICAL CONCEPT LANGUAGE MEMBERSHIP.**

`CanonicalConceptDefinition.aliases`, `.customer_phrases`, and `.insurer_terms` are tuples of strings. The registry validates normalised uniqueness/ambiguity but does not prove that a particular label legitimately belongs to a concept.

This is the principal G1 gap.

A wrong string can currently enter a concept language surface without its own evidence/review binding. That is acceptable for explanation-oriented terminology seeds, but not for a comparison-critical semantic identity layer.

### 3. Alias-level review-decision binding

**PARTIALLY SUPPORTED IN THE PRODUCT-TERM ALIAS PATH, NOT IN THE CANONICAL-CONCEPT ALIAS PATH.**

`GovernedTerminologyAlias` carries:

- alias identity;
- source/product scope;
- evidence spans;
- review status;
- publication status;
- effective dates.

But it has no explicit `review_decision_id` / `governance_version`, and its target is a governed marketing term rather than a canonical concept.

G1 should reuse this pattern and evidence contract rather than invent a parallel alias resolver.

### 4. Explicit AMBIGUOUS state

**SUPPORTED.**

`CanonicalConceptResolver` already exposes `AMBIGUOUS` and requires at least two candidates. `CanonicalConceptRegistry` already supports intentional shared terminology only through an explicit `ambiguity_group`.

G1 should preserve this state. Broad labels such as `Ambulance` must not be collapsed into `NOT_FOUND` when the governed concept space contains both road and air ambulance.

### 5. Registry/version dependency

**PARTIALLY SUPPORTED.**

`TerminologyRegistrySnapshot.snapshot_id` is deterministic and immutable-by-interface, so snapshot identity exists.

But concept language membership itself does not yet have a stable per-alias governance identity/version. Therefore a dependent product fact cannot currently say exactly which governed alias decision justified its benefit identity.

G1 needs that alias-level dependency edge before benefit identity becomes safe for cross-product comparison.

## Architectural decision

### Reuse

Reuse unchanged where possible:

- `CanonicalConceptFamily`
- `CanonicalConceptDefinition` as the concept container
- `CanonicalConceptRegistry`
- `CanonicalConceptResolver`
- `EvidenceSpan`
- normalisation from `terminology.resolver`
- immutable snapshot pattern
- `AMBIGUOUS` behaviour

### Extend narrowly

Add a governed canonical-concept alias membership record, conceptually:

```text
GovernedConceptAlias
    alias_id
    alias_text
    concept_id
    evidence_spans
    review_decision_id
    governance_version
    review_status
    publication_status
    effective_from?
    effective_to?
    source_scope?
```

Important: `source_scope` is evidence/document scoped if later needed. Do not key semantics on insurer/product identity.

The authoritative benefit-identity resolver may use only published/eligible governed concept aliases.

### Do not create

Do not create:

- a second `BenefitConceptResolver` subsystem;
- fuzzy authoritative matching;
- embedding/LLM identity decisions;
- insurer/product-specific alias branches;
- runtime alias self-learning;
- a new ontology framework.

## Compatibility boundary

Existing bare-string concept language surfaces remain valid for their current explanation-oriented MO-024 behaviour.

MO-028C must **not silently reinterpret every existing `aliases/customer_phrases/insurer_terms` string as comparison-authoritative governed identity**.

Instead, the G1 governed identity path should be opt-in through `GovernedConceptAlias` records. This avoids breaking existing terminology behaviour and avoids retroactively certifying unreviewed strings as semantic joins.

## Resolution contract for MO-028C

The G1 adapter/result should expose:

```text
RESOLVED
AMBIGUOUS
NOT_FOUND
```

Mapping from existing resolver states:

- existing exact governed concept alias membership, one eligible match -> `RESOLVED`;
- broad exact label intentionally shared across an ambiguity group -> `AMBIGUOUS`;
- no eligible governed concept-alias membership -> `NOT_FOUND`.

`INVALID_INPUT` may remain an internal validation outcome and must never publish a concept identity.

## Comparison safety

Cross-product benefit comparison may join facts only when:

1. both sides are `RESOLVED`;
2. the stable concept ID is the same;
3. each side retains the specific governed alias membership identity that justified the mapping;
4. the alias memberships are compatible under the certification policy.

For G1 v1, require the same governed alias registry/snapshot version for comparison eligibility. Cross-version alias compatibility is deferred until an explicit migration/compatibility contract exists.

This is intentionally stricter than concept-ID equality alone.

## Alias collision and ambiguity rules

- one governed alias must not resolve to two concepts unless the shared label is intentionally registered under one explicit ambiguity group;
- intentional ambiguity produces `AMBIGUOUS`, never insertion-order selection;
- a broad label such as `Ambulance` can be registered as ambiguity metadata without being made a positive alias of road or air ambulance individually;
- exact road/air aliases must remain distinct.

## G1 implementation recommendation

Implement G1 as a **thin governed identity extension over the existing terminology stack**:

1. add `GovernedConceptAlias` contract;
2. add immutable governed-alias registry validation/indexing around `CanonicalConceptRegistry`;
3. add a narrow resolution adapter that reuses normalisation and canonical concept objects;
4. preserve `RESOLVED / AMBIGUOUS / NOT_FOUND`;
5. retain alias evidence, review-decision identity, governance version, and snapshot identity in every resolved result;
6. add Arogya G0 concepts only as the minimum Health benefit seed needed for this milestone.

## G1 seed concepts

Initial source-pressure concepts only:

- cataract;
- road ambulance;
- air ambulance (false-friend guard even if not used by Arogya limit inventory);
- AYUSH;
- modern treatment group;
- room rent;
- ICU.

Do not broaden the benefit ontology beyond source/test pressure.

## Required certification checks

- governed exact alias resolves;
- raw label and matched alias identity retained;
- per-alias evidence required;
- per-alias review-decision ID required;
- governance version retained;
- unpublished/unreviewed alias cannot resolve authoritatively;
- `Ambulance` -> `AMBIGUOUS` when intentionally registered as a shared ambiguity label;
- road ambulance != air ambulance;
- unknown label -> `NOT_FOUND`;
- no fuzzy match;
- canonical concept bare-string aliases are not automatically comparison-authoritative;
- same concept ID without compatible alias governance is insufficient for comparison join;
- product identity does not change resolution;
- existing terminology tests remain green.

## Final audit decision

```text
EXISTING TERMINOLOGY MECHANISM: REUSE
EXISTING CANONICAL ALIAS GOVERNANCE: INSUFFICIENT
NEW PARALLEL TERMINOLOGY SYSTEM: REJECT
REQUIRED CHANGE: THIN GOVERNED CONCEPT-ALIAS EXTENSION
G1 READY FOR IMPLEMENTATION: YES
```
