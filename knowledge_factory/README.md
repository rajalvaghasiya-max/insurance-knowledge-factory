# Knowledge Factory Core

`knowledge_factory/` contains cross-domain production architecture. It should stay independent of insurer/product-specific rules and of any single insurance domain.

## Core modules

| Area | Responsibility |
|---|---|
| `governance/` | Engineering principles, decisions, evolution register, lessons, milestones, test contract, and asset lifecycle registry. |
| `golden_concept_package/` | Assemble and validate a complete concept package: dependencies, coverage, consistency, gaps, and certification. |
| `gmvs/` | Generic Manufacturing Validation System: validates architecture, readiness, manufacturing, reuse, and governance evidence. |
| `advisor_intelligence/` | Builds/certifies advisor-facing intelligence assets from upstream trusted assets. |
| `decision_intelligence/` | Builds/certifies downstream decision-support assets. |
| `shared/` | Cross-factory asset normalization helpers. |

## Golden Concept Package (GCP)

A GCP is the governed package for one insurance concept, such as Copay or Waiting Period.

```text
foundation/evidence receipts
→ meaning / understanding assets
→ mental models
→ financial outcomes
→ advisor intelligence
→ decision intelligence
→ certification and GMVS
```

A package is not complete merely because a narrative or UI-friendly explanation exists. It needs evidence, lineage, dependency checks, and certification.

## GMVS

GMVS assesses whether the Factory can manufacture a concept through reusable architecture rather than one-off code. It checks architecture, readiness, manufacturing outputs, declared reuse, and governance conditions.

Use:

```powershell
python -m scripts.run_gmvs
```

GMVS status must be operationally truthful. A path mismatch or stale output contract should be treated as a maintenance issue, not hidden.

## Governance

Read `governance/README.md` first. In particular:

- Engineering principles define hard constraints.
- The decision log records why architecture choices were made.
- The evolution register records planned improvements and debt.
- The test contract defines the canonical test layout.

## Boundaries

This folder does not own:

- raw web/PDF capture (`agents/`, `archive/`, `registry/`)
- Health-specific extraction rules (`knowledge_domains/health/`)
- product identity source classification (planned upstream identity layer)
- frontend or workflow applications
