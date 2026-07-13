# Health Domain Manufacturing

`knowledge_domains/health/` contains Health-specific evidence routing, field extraction, document processing, knowledge manufacturing, understanding, mental-model, financial-outcome, and timeline capabilities.

Health is the active production domain. The architecture is designed so later Motor and Life domains can reuse Factory contracts while implementing their own domain rules.

## Major areas

| Area | Responsibility |
|---|---|
| `field_registry/` | Canonical Health field definitions and maturity/readiness contracts. |
| `evidence/` | Health evidence registry utilities. |
| `routing/` | Evidence router: selects candidate sources for a requested entity/field. |
| `extractors/` | Field-specific deterministic extractors, such as Copay, Room Rent, PED wait, and Initial Wait. |
| `validators/` | Domain validation for extracted facts and support rules. |
| `processing/` | Controlled document processing into components, clauses, sections, tables, and quality outputs. |
| `knowledge_manufacturing/` | Component scanning, normalization, classification, concept recognition, knowledge blocks, and topic composition. |
| `knowledge_distillation/` | Observations, relationships, opportunities, and distillation outputs. |
| `understanding/` | Understanding asset builder and certification. |
| `understanding_manufacturing/` | Learning primitive/path/understanding manufacturing lines. |
| `mental_model_transformation/` | Model detection, gap identification, target model, transformation plan, and verification. |
| `financial_outcome/` | Financial outcome models, scenario construction, adjudication, shock analysis, quality, and certification. |
| `waiting_period_timeline/` | Evidence-backed timeline simulation requiring runtime dates and product evidence profile. |
| `factory/` | Health Factory manager and pipeline status. |

## Field extraction rule

A field extractor is not a general-language summariser. It must:

```text
accept evidence context
→ locate supported source material
→ extract structured candidate fact
→ validate domain constraints
→ preserve source/provenance
→ return unknown/unresolved when support is absent
```

Do not add product-specific facts or aliases into Health core logic. Product/insurer registration belongs in governed data or identity/evidence configuration.

## Health data flow

```text
product-specific source asset
→ identity resolution (planned upstream hard gate)
→ evidence routing
→ Health field extractor
→ Health validator
→ evidence-backed fact
→ knowledge/understanding/future recommendation assets
```

## Current Health milestones

- Core fields registered: Copay, Room Rent, PED wait, specified disease wait, restoration, initial wait.
- Copay: Golden Concept baseline established.
- Waiting Period: timeline capability built and tested; GCP/GMVS contract alignment remains a maintenance task.
- Next: Product Signal Safety Contract and Product Identity Resolution before expansion to more Health fields.
