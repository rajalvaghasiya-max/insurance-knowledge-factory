# PolicyScna — Architecture Fitness Review

**Status:** REVIEW COMPLETE — 2026-08-15

**Reviewed baseline:** `feature/mo-028b-health-waiting-period-coverage`

## Purpose

This checkpoint follows two completed architecture gates:

- **AR-2.5 — Repository Cleanup & Succession Closure — CERTIFIED**
- **AR-3.0 — Hostile Commercial Health-Product Pressure Gate — CERTIFIED**

The objective is not to generate new architecture. It is to decide, from executed evidence, whether the current governed architecture should be extended, repaired, replaced, or re-platformed before the next Health milestone.

## Executive decision

**Decision: EXTEND the current architecture. Do not replace it. Do not perform a large topology consolidation. Do not migrate to a database yet.**

The next implementation milestone should close the remaining **canonical ontology / terminology fitness gate** before broad Health scaling.

The evidence supports a narrow sequence:

1. preserve `factory_core/` + `insurance_intelligence/` as the authoritative active architecture;
2. keep `knowledge_domains/` transitional and migration-only;
3. keep `factory_sdk/` and `knowledge_factory/` historical/review-required;
4. retain current governed file/JSON storage until a measured serving/storage trigger fires;
5. certify the canonical terminology/ontology layer against the roadmap's adversarial term set;
6. only then begin Phase-2 Health product/insurer expansion.

## 1. What is now empirically proven

### 1.1 Authoritative ownership is clear enough to proceed

`ACTIVE_AND_HISTORICAL_ARCHITECTURE_CLASSIFICATION.md` already defines:

- `factory_core/` — **AUTHORITATIVE_ACTIVE** for governed Knowledge Factory contracts, evidence processing, identity, publication and provenance;
- `insurance_intelligence/` — **AUTHORITATIVE_ACTIVE** for governed semantics, terminology, generic knowledge, comparison, assessment and decision support;
- `knowledge_domains/` — **TRANSITIONAL_REVIEW_REQUIRED**;
- `factory_sdk/` and `knowledge_factory/` — **HISTORICAL_REVIEW_REQUIRED**.

AR-2.5 reinforced that boundary with an executable succession firewall: authoritative production Python under `factory_core/` and `insurance_intelligence/` must not import `knowledge_domains/`.

**Fitness finding:** repository topology is not aesthetically consolidated, but authority is sufficiently explicit and enforced for continued governed development. A large physical merge of the three historical/current factory roots would add churn without evidence of a capability failure.

### 1.2 Legacy recommendation/comparison paths are no longer an architectural blocker

AR-2.5 C4 classifies the legacy recommendation/comparison scripts as **HISTORICAL_NON_AUTHORITATIVE** and firewalls them from authoritative production code. AR-2.5 C6 retains only three historical generated artifacts because they serve bypass/firewall certification.

**Fitness finding:** the old recommendation-capable tree remains repository history, not a live runtime alternative. No further cleanup is required before the next Health knowledge milestone.

### 1.3 Commercial-product generalization is proven for the tested pressure shape

AR-3.0 forced a dense Star Comprehensive Delivery/New Born clause through:

- authoritative source inventory;
- atomic normative decomposition;
- generic semantic-family mapping;
- residue accounting;
- comparison-readiness blocking;
- education/decision-support propagation.

The architecture preserved waiting-period duration, start basis, renewal continuity, a post-claim reset trigger/effect pair, benefit limits, expense exclusions and benefit interactions without Star-specific runtime reasoning.

**Fitness finding:** no generic semantic rewrite is justified by the hostile Health evidence reviewed so far.

### 1.4 Residue and unknown propagation are working as intended

AR-3.0 deliberately left unresolved limit-table rows and surrounding clause mechanics as material residue. That residue blocked publication/comparison readiness and propagated into the existing decision-support path as:

`NOT_SCORABLE -> UNRESOLVED -> BLOCKED_BY_PRODUCT_UNKNOWN -> ACTION_REQUIRED`

**Fitness finding:** the architecture does not need a new uncertainty mechanism before Health expansion. Existing residue, blocker and decision-sufficiency contracts are sufficient for the tested case.

## 2. What remains a real weakness versus merely unfinished evidence

### 2.1 Real architectural blocker: canonical ontology exit gate is not yet evidenced as closed

The repository contains a real canonical terminology architecture under `insurance_intelligence/terminology/`, including:

- `concept_registry.py`
- `concept_resolver.py`
- `alias_resolver.py`
- `context_resolver.py`
- `governed_concept_aliases.py`
- `health_seed.py`

The contracts are correctly scoped: the canonical concept registry sits before product-specific terminology mapping and deliberately does not infer product applicability, retrieve evidence, compare products or recommend. The Health seed also explicitly defines language-routing assets rather than product facts.

However, the validated roadmap's Phase-1 exit gate is stronger than mere existence of these modules. It requires the canonical ontology to be seeded from governed standardized definitions, versioned/effective-dated as required, and to pass the adversarial terminology regression set — including rejection of stale PED wording and separation of same-name concepts across insurance categories.

**Fitness finding:** before declaring Phase 1 complete and scaling Health, this ontology/terminology gate needs a focused certification pass. This is the highest-value next milestone because it closes a named roadmap gate rather than creating new scope.

### 2.2 Unreviewed Star mechanics are product-evidence backlog, not architecture defects

The unresolved Delivery/New Born table rows, surrounding Section II.14 conditions, PED buy-back, bariatric interaction and remaining G1 waiting-period candidates are not evidence of architectural failure. AR-3.0 demonstrated that the system can safely preserve them as unresolved.

**Fitness finding:** do not reopen AR-3.0 solely to make Star Comprehensive "complete". Review these facts later as part of normal governed product onboarding or when a customer/comparison use case requires them.

## 3. Repository topology decision

### Current ownership

| Root | Fitness disposition |
|---|---|
| `factory_core/` | Keep — authoritative governed factory foundation |
| `insurance_intelligence/` | Keep — authoritative semantics/intelligence |
| `knowledge_domains/` | Keep transitional — migrate reusable upstream pieces only when demanded |
| `factory_sdk/` | Keep historical/review-required; no new governed development |
| `knowledge_factory/` | Keep historical/review-required; no new governed development |

`knowledge_factory/README.md` describes an older cross-domain production architecture and `factory_sdk/README.md` describes older shared production-line contracts. Those capabilities may still have historical learning value, but current architecture classification already prevents them from silently becoming authoritative.

### Decision

**No large consolidation/refactor now.**

A future topology refactor is justified only if one of these events occurs:

1. an authoritative capability must duplicate a historical module because no migration path exists;
2. an active import crosses a forbidden succession boundary;
3. repository ownership becomes ambiguous in a way not caught by current classification/firewall tests;
4. Motor/Life pressure proves that an ownership boundary itself blocks reuse.

None of those triggers was established by AR-3.0.

## 4. Storage / database fitness decision

### Decision

**DEFER database migration. Continue with governed file/JSON artifacts as source of truth.**

The validated roadmap defines database adoption as trigger-driven, not milestone-driven. Named triggers include:

- measured concurrent-read latency on serving/coverage registries;
- multi-writer contention;
- query patterns the filesystem cannot serve safely or efficiently.

AR-3.0 revealed semantic and governance complexity but no measured persistence or retrieval bottleneck.

Therefore:

- no Postgres migration is authorized by this checkpoint;
- no vector database is justified for governed evidence retrieval;
- no graph database is justified;
- when a serving trigger eventually fires, migrate the read/serving path first while preserving governed artifacts and lineage as authoritative source records.

## 5. Extend / refactor / replace verdict

| Choice | Decision | Reason |
|---|---|---|
| EXTEND | **YES** | Current generic contracts survived hostile commercial Health pressure without product-specific branching |
| TARGETED REFACTOR | **ONLY WHEN TRIGGERED** | No current ownership/storage defect requires one before the next gate |
| REPLACE | **NO** | No evidence of a foundational semantic/governance failure |
| DATABASE MIGRATION | **NO, DEFER** | No measured storage trigger |

## 6. Next milestone

### AFR-N1 — Canonical Ontology / Terminology Fitness Gate

**Objective:** certify that the existing canonical terminology architecture is strong enough to serve as the semantic backbone for Phase-2 Health scaling.

This is a certification-and-gap-repair milestone, not a redesign.

Minimum scope:

1. inventory the canonical Health concept seed and governing terminology contracts;
2. identify the exact authority/source basis for standardized definitions where the roadmap requires it;
3. build the adversarial regression corpus from the previously identified terminology examples;
4. prove category scoping and alias/entity-resolution separation;
5. prove stale or consequentially wrong definitions cannot become canonical truth;
6. preserve the distinction between canonical concept meaning, product-language mapping and product-specific fact/applicability;
7. add only the smallest contract/data changes that a failing real test forces.

### Explicit non-goals

AFR-N1 will not:

- add more Star product facts;
- start broad insurer onboarding;
- add a database;
- add frontend/API work;
- add recommendation logic;
- begin Motor or Life;
- rewrite `factory_core` or `insurance_intelligence`.

### Exit gate

AFR-N1 closes when:

- focused ontology/terminology adversarial tests are green;
- canonical definitions/aliases are source-governed to the level required by the roadmap;
- category-scoping tests prevent semantic collisions across insurance domains;
- wrong/stale definition regression cases fail closed or resolve to the governed definition;
- `tests/insurance_intelligence` remains green;
- regressions = 0.

After that gate, the architecture review authorizes **Phase 2 — expand and scale Health** as governed data, with zero product-identity-bearing reasoning code.

## 7. Checkpoint conclusion

PolicyScna is at a materially different point than before AR-2.5 and AR-3.0.

The question is no longer whether the architecture can represent a difficult commercial Health clause. It can, for the pressure shape tested, and it can preserve uncertainty without silently manufacturing readiness.

The next risk is semantic consistency at scale: every new product must map onto the same governed concept backbone. That makes canonical ontology/terminology certification the correct next gate.

**Architecture Fitness Review: CLOSED**

**Next action: AFR-N1 — Canonical Ontology / Terminology Fitness Gate.**
