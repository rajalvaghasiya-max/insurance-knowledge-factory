# PolicyScna Architecture Classification

## Purpose

This record prevents historical prototypes, generated outputs, transitional packages, and
supporting acquisition code from being mistaken for authoritative insurance intelligence.
It is a control document for development, evaluation, comparison, future ranking work, and
repository cleanup.

## Audit / certification baseline

Current architecture review and certification baseline:

`feature/mo-028b-health-waiting-period-coverage`

Architecture reviews must declare the exact Git ref being reviewed. The default `main` branch
may lag the currently certified architecture and must not be substituted silently.

## Classification vocabulary

- **AUTHORITATIVE_ACTIVE** — canonical production architecture for new governed capability.
- **AUTHORITATIVE_SUPPORTING** — active upstream/support infrastructure; outputs are not
  automatically governed insurance truth.
- **AUTHORITATIVE_CERTIFICATION** — executable certification of active architecture.
- **AUTHORITATIVE_GOVERNANCE** — architecture and governance control records.
- **TRANSITIONAL_REVIEW_REQUIRED** — prior generation containing potentially reusable
  capability; no new architecture should be added there without explicit review.
- **HISTORICAL_REVIEW_REQUIRED** — non-authoritative legacy package; reuse requires migration
  into current contracts and new certification.
- **HISTORICAL_NON_AUTHORITATIVE** — retained only for history, fixtures, anti-patterns, or
  evaluation; must never feed governed runtime decisions.
- **OPERATIONAL_MIXED** — scripts/entrypoints whose authority depends on the component they invoke.

## Authoritative active components

### `factory_core/`

Status: **AUTHORITATIVE_ACTIVE**

Use for governed Knowledge Factory contracts, evidence processing, publication, identity,
provenance, deterministic factory workflows, and cross-domain governance foundations.
Changes require tests and milestone review.

### `insurance_intelligence/`

Status: **AUTHORITATIVE_ACTIVE**

Use for governed insurance semantics, terminology, generic knowledge, comparison,
education-first assessment, decision support, explanation, and governed downstream handoffs.

New insurance semantics belong here. New products add governed data/evidence/applicability;
they must not add product-specific runtime reasoning branches.

Only typed, validated outputs from this package may feed future ranking work.

### `docs/architecture/`

Status: **AUTHORITATIVE_GOVERNANCE**

Architecture decisions, publication specifications, review records, certification artifacts,
and classification records govern current implementation boundaries unless explicitly
superseded by a later approved record.

## Authoritative supporting components

### `collectors/`

Status: **AUTHORITATIVE_SUPPORTING**

Source acquisition/capture infrastructure. It may create immutable source assets and metadata,
but acquisition output is evidence/candidate material, not governed insurance truth.

### selected `agents/`

Status: **AUTHORITATIVE_SUPPORTING + LEGACY_MIXED**

Current acquisition-oriented agents (for example discovery, preservation, PDF/source capture)
may remain supporting infrastructure. Older knowledge extraction, consolidation, recommendation,
or intelligence-producing agents require module-level review before reuse.

No agent output is authoritative merely because it was produced by an active capture workflow.

### `config/` and `storage/`

Status: **AUTHORITATIVE_SUPPORTING**

Operational configuration/storage infrastructure where used by active acquisition/factory paths.
These components do not define insurance semantics or ranking truth.

## Transitional architecture

### `knowledge_domains/`

Status: **TRANSITIONAL_REVIEW_REQUIRED**

This package contains a prior Health manufacturing/intelligence generation. Its historical README
may describe Health as the active production domain, but newer governed architecture supersedes
that claim.

Rules:

- **NO NEW ARCHITECTURAL DEVELOPMENT** should be added here.
- Current `insurance_intelligence` must not consume historical `knowledge_domains` extraction
  outputs as governed facts.
- Reusable upstream capabilities such as routing, deterministic extraction, validation, field
  registry, parsing/factory bridges, or product-identity utilities may be migrated selectively.
- Downstream answering, recommendation-like reasoning, customer-document intelligence,
  financial-outcome logic, timeline simulation, or other intelligence capability must be rebuilt
  or adapted to consume certified current knowledge before becoming authoritative.
- Every module requires explicit disposition before deletion or migration.

## Historical components requiring review before reuse

### `factory_sdk/`

Status: **HISTORICAL_REVIEW_REQUIRED**

Do not import into new governed comparison or ranking paths without an explicit architecture
review, typed adapter, provenance analysis, and new certification.

### `knowledge_factory/`

Status: **HISTORICAL_REVIEW_REQUIRED**

This package may contain useful prior experiments, but it is not an authoritative source for
current comparison or ranking inputs. Reuse requires explicit review and migration into active
contracts.

## Operationally mixed paths

### `scripts/`

Status: **OPERATIONAL_MIXED**

A script is not authoritative because it exists under `scripts/`. Its status derives from the
contracts it invokes.

Scripts that consume arbitrary historical JSON/comparison payloads or reconstruct recommendation
signals outside governed handoffs are **HISTORICAL_NON_AUTHORITATIVE** and must not be used as a
current runtime path.

In particular, legacy recommendation paths such as `scripts/recommend_products.py` are
inadmissible for governed recommendation/ranking because they can bypass certified knowledge and
`GovernedComparisonHandoff`.

### `main.py`

Status: **AUTHORITATIVE_SUPPORTING_ENTRYPOINT / NOT_CANONICAL_APPLICATION_ENTRYPOINT**

`main.py` currently represents a capture/preservation workflow. It must not be interpreted as the
canonical PolicyScna insurance-intelligence application architecture.

## Certification tiers

### `tests/insurance_intelligence/`

Status: **AUTHORITATIVE_CERTIFICATION**

Focused semantic/milestone tests plus the full `insurance_intelligence` suite are authoritative
certification evidence for the active intelligence architecture.

### broader `tests/`

Status: **MIXED_CERTIFICATION_AND_COMPATIBILITY**

The full repository test count is valid regression evidence, but it combines authoritative active,
supporting, transitional, and historical-compatibility tests. Report results in tiers:

1. focused capability certification;
2. authoritative subsystem regression (`factory_core` / `insurance_intelligence` as applicable);
3. supporting/transitional regression;
4. full repository compatibility/regression.

Passing a historical test does not promote the tested component to authoritative status.

## Historical and non-authoritative artifacts

The following are **HISTORICAL_NON_AUTHORITATIVE** regardless of file format:

- previously generated recommendation outputs;
- previously generated comparison outputs;
- previously generated explanation outputs;
- portfolio or suitability outputs from superseded agents;
- ad hoc JSON, CSV, Markdown, text, notebook, or prompt-generated summaries;
- copied console output and manually edited result files;
- objects produced by historical recommendation, comparison, or portfolio code;
- obvious backup/source-copy files retained only during development.

They may be retained as evaluation fixtures or known-bad examples. They must not be consumed as
governed facts, governed comparisons, or ranking inputs.

## Enforced certified-knowledge consumption boundary

Current semantic producers must project certified knowledge through typed comparison-readiness
contracts before it reaches assessment/comparison consumers. Unresolved states must remain
unresolved; `UNKNOWN` must never become `ABSENT` or `FAVORABLE`.

The sole admissible factual comparison input to future ranking work remains:

`GovernedComparisonHandoff`

It accepts only an exact `GovernedComparisonExplanationProjection` with status `READY` or
`READY_WITH_SOURCE_LIMITATIONS`. It rejects blocked projections, mappings, serialized files,
historical agent objects, personalized decision projections, subclasses, and arbitrary legacy
payloads.

No future ranking component may bypass this path or reconstruct comparison facts from raw
documents or historical outputs.

## Cleanup rule

A component/file may be physically removed only when all of the following are established:

1. no authoritative active import/runtime dependency;
2. no unique certification or migration value;
3. no unique source/provenance artifact that must be retained;
4. no reusable capability awaiting explicit disposition;
5. deletion leaves focused, subsystem, and full-repository regression green.

Old age alone is not a deletion criterion.

## Change rule

A component changes classification only through an explicit architecture record that states its
new status, migration boundary, accepted input/output contracts, and certification evidence.
