# PolicyScna — Insurance Knowledge Factory & Intelligence

This repository contains multiple architectural generations. Do not infer authority from folder
names or age alone.

## Current architecture baseline

Architecture review and current certification are being performed on:

`feature/mo-028b-health-waiting-period-coverage`

The default `main` branch may lag this certified architecture. External reviews must declare the
exact Git ref being inspected.

## Canonical development areas

- `factory_core/` — authoritative Knowledge Factory governance, provenance, identity and
  deterministic publication foundations.
- `insurance_intelligence/` — authoritative insurance semantics, terminology, generic knowledge,
  comparison, education-first assessment, decision support and governed explanation/handoff.
- `docs/architecture/` — authoritative architecture/governance records.
- `tests/insurance_intelligence/` — authoritative certification for the active intelligence layer.

## Supporting acquisition / infrastructure

- `collectors/` — source capture/acquisition.
- selected `agents/` — discovery, preservation and source/PDF capture only; the package also
  contains legacy intelligence code, so module-level classification applies.
- `config/`, `storage/` — supporting operational infrastructure where used by active paths.

Supporting acquisition outputs are evidence/candidate material. They are not governed insurance
truth until they pass the current governance/semantic lifecycle.

## Transitional / historical areas

- `knowledge_domains/` — transitional prior Health manufacturing/intelligence generation. No new
  architecture should be added here. Reusable upstream capabilities may be migrated only after
  review.
- `factory_sdk/` — historical, review required before reuse.
- `knowledge_factory/` — historical, review required before reuse.
- legacy recommendation/comparison scripts and generated outputs — non-authoritative.

See:

`docs/architecture/ACTIVE_AND_HISTORICAL_ARCHITECTURE_CLASSIFICATION.md`

for the complete classification and cleanup rules.

## Current governed knowledge lifecycle

```text
Authoritative source
    -> atomic normative inventory
    -> governed concept identity
    -> reviewed source-sufficient proposition
    -> generic semantic contract
    -> applicability / relationships
    -> authority / validation
    -> residue accounting
    -> publication / certification
    -> fail-closed comparison projection
    -> assessment / comparison / decision support
```

Core rule: **UNKNOWN != ABSENT != FAVORABLE**.

## Development rule

- New insurance semantic -> `insurance_intelligence/generic_knowledge` and its certified semantic
  family contracts.
- New product -> governed data/evidence/applicability, not product-specific runtime reasoning.
- New acquisition/extraction behavior -> supporting acquisition/factory boundary; outputs remain
  candidate evidence until governed.
- New downstream decision capability -> consume certified knowledge through typed governed
  boundaries; never reconstruct truth from arbitrary JSON or historical outputs.

## Testing

Report evidence in tiers rather than treating the full repository test count as one architecture
certification number:

1. focused capability certification;
2. authoritative subsystem regression;
3. supporting/transitional regression where relevant;
4. full repository regression.
