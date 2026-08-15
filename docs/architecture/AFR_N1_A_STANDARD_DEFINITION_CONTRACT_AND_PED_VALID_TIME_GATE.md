# AFR-N1.A — Standard Definition Contract & PED Valid-Time Gate

**Status:** IMPLEMENTED — VALIDATION PENDING  
**Date:** 2026-08-15

## Why this slice exists

The post-AR-3.0 Architecture Fitness Review identified one remaining Phase-1 exit gate: the canonical ontology/terminology layer must be governed strongly enough to scale Health without turning a convenient glossary into a high-authority semantic poison source.

The existing `insurance_intelligence/terminology/concept_registry.py` remains correct for language routing: canonical IDs, canonical names, aliases and deterministic resolution. It is intentionally not a product-fact or product-applicability layer.

The roadmap requires a stronger and separate contract for standardized definitions:

- primary-source governed text;
- insurance-category namespaces;
- versioned definitions;
- valid-time (`effective_from` / `effective_to`) lookup;
- reference-never-mutate behavior;
- aliases plus false-friend (`not_synonyms`) guards;
- fail-closed behavior when no definition or multiple definitions apply.

AFR-N1.A adds that contract without changing the existing routing registry.

## Source-version pressure that forced the contract

The IRDAI source estate itself demonstrates why a timeless lookup is unsafe:

- the 2020 standardized PED definition uses a 48-month lookback;
- current IRDAI Health Department guidance uses a 36-month lookback and points to the 2024 Health Insurance Business framework;
- therefore a consumer asking about a 2023 contract and a consumer asking about a 2026 contract cannot safely be served by a single mutable `PED = ...` dictionary entry.

The first governed seed intentionally contains those two PED definition versions with non-overlapping valid-time windows. This is a narrow pressure seed, not the completed eleven-term ontology.

## Architecture decision

New module:

`insurance_intelligence/terminology/standard_definitions.py`

New narrow regulatory seed:

`insurance_intelligence/terminology/health_regulatory_definition_seed.py`

The contract is deliberately separate from:

1. canonical language routing (`concept_registry`);
2. product-language/entity resolution;
3. product facts and applicability;
4. comparison and recommendation.

A `GovernedStandardDefinition` carries:

- `definition_id`
- `canonical_concept_id`
- `category`
- `version`
- `standard_definition`
- primary `source`
- `evidence_class`
- `effective_from`
- `effective_to`
- `aliases`
- `not_synonyms`

The registry requires `category + canonical_concept_id + as_of` for consumption. It provides no unqualified "latest" method.

## AFR-N1.A adversarial pressure

The focused tests prove:

1. current PED lookup resolves to the governed 36-month version, not the stale four-year/48-month version;
2. pre-2024 valid-time lookup still resolves the earlier governed version rather than rewriting history;
3. a definition ID cannot be mutated in place — a semantic change requires a new version;
4. canonical concept IDs must be category-namespaced;
5. Health cumulative bonus and Motor NCB can share surface aliases without becoming the same definition identity;
6. overlapping applicable versions fail closed;
7. missing applicable versions fail closed;
8. aliases and `not_synonyms` cannot contradict each other;
9. the standard-definition contract cannot carry product/customer/comparison fields.

## Important non-claim

**AFR-N1 is not yet certified.**

The roadmap requires the complete eleven-term regression set. AFR-N1.A establishes the load-bearing contract and the first real valid-time source pressure only.

In particular, the next slices must still pin the primary-source definitions needed to certify:

- Room Rent, including the associated-medical-expense consequence;
- Health Cumulative Bonus versus Motor NCB category collision;
- co-payment structural meaning versus product-level conditionality;
- restoration versus recharge false-friend/trigger semantics;
- the remaining terms in the approved eleven-term regression set.

Product wording that reproduces standardized wording may help locate/verify text, but it must not be silently promoted to regulatory authority.

## Exit criterion for AFR-N1.A

```text
AFR-N1.A focused standard-definition tests   GREEN
insurance_intelligence                       GREEN
regressions                                      0
```

After this gate is green, continue AFR-N1 by adding only primary-source-backed definition records and the remaining adversarial regression cases. No product-specific reasoning code is authorized.
