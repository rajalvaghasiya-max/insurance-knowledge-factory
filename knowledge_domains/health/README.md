# Health Domain Manufacturing — Transitional Architecture

`knowledge_domains/health/` contains a prior Health-specific manufacturing and intelligence generation. It includes evidence routing, field extraction, document processing, knowledge manufacturing, understanding, mental-model, financial-outcome, and timeline capabilities.

## Current status

Status: **TRANSITIONAL_REVIEW_REQUIRED**

This package is not the canonical location for new PolicyScna insurance-intelligence architecture. The authoritative current architecture is `factory_core/` + `insurance_intelligence/` on the declared certified architecture ref.

Rules:

- Do not add new architectural capability here.
- `factory_core/` and `insurance_intelligence/` production code must not import `knowledge_domains`.
- Outputs from this package are not governed insurance truth merely because they are structured or evidence-backed.
- Reusable upstream capabilities may be migrated selectively after explicit review and new certification.
- Downstream intelligence such as answering, financial-outcome reasoning, recommendation-like logic, and timeline simulation must be rebuilt/adapted to consume certified current knowledge before authoritative use.
- Historical tests and fixtures may remain for migration analysis and regression evidence.

## Major areas and AR-2.2 disposition

| Area | Current disposition |
|---|---|
| `field_registry/` | KEEP as supporting candidate; migrate ownership later if needed. |
| `evidence/` | KEEP as upstream/support candidate; governed output boundary required. |
| `routing/` | KEEP capability; candidate evidence routing only. |
| `extractors/` | KEEP deterministic extraction capability; output is candidate data, not authoritative truth. |
| `validators/` | KEEP where limited to evidence/domain validation. |
| `processing/` | KEEP/VERIFY for migration behind current factory governance. |
| `batch/` | KEEP/VERIFY registry/factory bridge capability. |
| `factory/` | VERIFY; do not extend as a second Factory architecture. |
| `knowledge_manufacturing/` | PORT useful algorithms selectively; do not reuse historical trust semantics. |
| `knowledge_distillation/` | PORT selectively or retain historically. |
| `conditional_rule_publisher.py` | SUPERSEDED for new authoritative publication; retain historically until migration/coverage equivalence is verified. |
| `waiting_period_timeline/` | FUTURE CONSUMER CANDIDATE; adapt later to certified waiting-period knowledge. |
| `customer_document_intelligence/` | SUPERSEDED intelligence path. |
| `understanding/` | DEFER / research asset. |
| `understanding_manufacturing/` | DEFER / research asset. |
| `mental_model_transformation/` | DEFER / research asset. |
| `financial_outcome/` | DEFER; potential future consumer of certified semantics. |
| copay/room-rent harnesses | HISTORICAL / evaluation fixtures. |
| product identity utilities | VERIFY against current `factory_core` product/source identity governance before reuse. |

## Extraction rule retained for reusable upstream capability

A field extractor is not a general-language summariser. It must:

```text
accept evidence context
→ locate supported source material
→ extract structured candidate fact
→ validate domain constraints
→ preserve source/provenance
→ return unknown/unresolved when support is absent
```

A successful extraction still does **not** establish authoritative insurance truth. Candidate output must cross the current governed lifecycle before it can be consumed as certified knowledge:

```text
source / candidate evidence
→ identity / provenance / authority governance
→ atomic normative inventory / reviewed interpretation
→ semantic representation
→ applicability / relationships
→ validation / residue accounting
→ publication / certification
→ governed consumption
```

## Succession rule

New Health, Motor, or Life semantics belong in the current governed architecture. Domain-specific extraction may remain specialized, but insurance truth must be governed through shared current contracts.
