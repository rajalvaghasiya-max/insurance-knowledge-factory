# MO-028A — Insurance Intelligence Coverage Registry

## Decision

PolicyScna will maintain a governed, machine-readable coverage registry that answers a simple operational question:

> What insurance intelligence do we currently know, for which insurer/product/version, with what lifecycle and readiness status?

The registry is internal governance infrastructure. It is not a customer ranking system and it is not a replacement for the existing product identity, evidence, publication, assessment, comparison, or decision-support contracts.

## Why now

The Health intelligence baseline through MO-027 is certified. The next phase expands across more insurance concepts, products, and insurers. Before breadth increases, PolicyScna needs one authoritative inventory that makes coverage and gaps reviewable.

## Authority boundaries

1. Product identity remains governed by the existing entity-resolution/product-identity references. MO-028A consumes canonical insurer/product/UIN identifiers; it does not independently resolve product identity.
2. Product lifecycle status is evidence-backed and time-aware. Unknown is preferred over guessing.
3. Concept coverage records describe what the system can safely use; they do not manufacture product facts.
4. A discontinued/withdrawn product may still have valid historical knowledge for an existing policyholder.
5. Readiness is local to a concept/product version. It must not imply overall product quality or suitability.
6. The dashboard/report is generated from registry records. It must not become a manually maintained parallel source of truth.

## Registry hierarchy

```text
Insurance domain
  ↓
Insurer
  ↓
Product / governed version
  ├── canonical identity / UIN
  ├── lifecycle status
  ├── lifecycle evidence + last verified time
  ├── evidence coverage
  └── concept coverage
        ├── coverage/governance status
        ├── evidence references
        ├── comparison readiness
        ├── decision-support readiness
        └── limitations
```

## Product lifecycle statuses

- `ACTIVE`
- `CLOSED_TO_NEW_BUSINESS`
- `DISCONTINUED`
- `WITHDRAWN`
- `REPLACED`
- `MIGRATED`
- `STATUS_UNKNOWN`

Lifecycle status is not inferred from absence of a webpage or document. Non-unknown lifecycle states require explicit evidence references and a verification timestamp.

Where relevant, lifecycle records may preserve:

- `status_effective_from`
- `status_effective_to`
- `replacement_product_reference`
- `status_evidence_reference_ids`
- `status_last_verified_at`

## Evidence coverage statuses

- `MISSING`
- `PARTIAL`
- `AVAILABLE`
- `COMPLETE`

This describes evidence availability for the governed product/version inventory; it is separate from whether a particular concept is certified.

## Concept coverage statuses

- `NOT_COVERED`
- `DISCOVERED`
- `EVIDENCE_AVAILABLE`
- `NORMALIZED`
- `GOVERNED`
- `CERTIFIED`
- `PARTIAL`
- `SOURCE_LIMITED`
- `BLOCKED`
- `NOT_AUTOMATED`

`CERTIFIED` is the strongest default state. `comparison_ready` and `decision_support_ready` are explicit flags because certification of a local mechanic does not automatically imply readiness for every downstream use.

## Initial review outputs

MO-028A will eventually generate four deterministic review views from the registry:

1. **Insurer Coverage** — insurers and products present in the registry.
2. **Product Coverage** — identity/UIN, lifecycle status, evidence coverage, concept counts and downstream readiness.
3. **Concept Coverage Matrix** — concepts across products, exposing certified/partial/source-limited/missing coverage.
4. **Gap Report** — missing, blocked, source-limited and not-automated areas that should drive future onboarding work.

## First implementation slice

MO-028A.1 establishes only the immutable contracts and registry validation:

- `ProductLifecycleStatus`
- `EvidenceCoverageStatus`
- `ConceptCoverageStatus`
- `ConceptCoverageRecord`
- `ProductCoverageRecord`
- `InsuranceIntelligenceCoverageRegistry`

The first seeded records and reports will follow only after these contracts are certified.

## Explicit non-goals

MO-028A does not:

- discover insurer products from the web;
- decide whether a product is good or bad;
- rank products;
- make recommendations;
- alter MO-025/MO-026/MO-027 reasoning;
- infer lifecycle status from missing evidence;
- replace authoritative product identity or evidence publication systems.
