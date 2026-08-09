# PolicyScna Architecture Classification

## Purpose

This record prevents historical prototypes, generated outputs, and superseded
packages from being mistaken for authoritative production components. It is a
control document for development, evaluation, comparison, and future ranking
work.

## Authoritative active components

### `factory_core/`

Status: **AUTHORITATIVE_ACTIVE**

Use for governed Knowledge Factory contracts, evidence processing, publication,
and deterministic factory workflows. Changes require tests and milestone review.

### `insurance_intelligence/`

Status: **AUTHORITATIVE_ACTIVE**

Use for governed insurance reasoning, explanation, terminology, benefit
discovery, eligibility, normalization, factual comparison, orchestration,
explanation projection, and governed downstream handoffs.

Only typed, validated outputs from this package may feed future ranking work.

### `tests/`

Status: **AUTHORITATIVE_CERTIFICATION**

Tests under the active factory and insurance-intelligence suites are the current
executable acceptance record. Passing historical tests alone does not make a
historical component authoritative.

### `docs/architecture/`

Status: **AUTHORITATIVE_GOVERNANCE**

Architecture decisions, publication specifications, and classification records
in this directory govern current implementation boundaries unless explicitly
superseded by a later approved record.

## Historical components requiring review before reuse

### `factory_sdk/`

Status: **HISTORICAL_REVIEW_REQUIRED**

Do not import into new governed comparison or ranking paths without an explicit
architecture review, typed adapter, provenance analysis, and new certification.

### `knowledge_factory/`

Status: **HISTORICAL_REVIEW_REQUIRED**

This package may contain useful prior experiments, but it is not an authoritative
source for current comparison or ranking inputs. Reuse requires explicit review
and migration into active contracts.

## Historical and non-authoritative artifacts

The following are **HISTORICAL_NON_AUTHORITATIVE** regardless of file format:

- previously generated recommendation outputs;
- previously generated comparison outputs;
- previously generated explanation outputs;
- portfolio or suitability outputs from superseded agents;
- ad hoc JSON, CSV, Markdown, text, notebook, or prompt-generated summaries;
- copied console output and manually edited result files;
- objects produced by historical recommendation, comparison, or portfolio code.

They may be retained as evaluation fixtures or known-bad examples. They must not
be consumed as governed facts, governed comparisons, or ranking inputs.

## Enforced pre-ranking boundary

The sole admissible comparison input to future ranking work is:

`GovernedComparisonHandoff`

It accepts only an exact `GovernedComparisonExplanationProjection` with status
`READY` or `READY_WITH_SOURCE_LIMITATIONS`. It rejects blocked projections,
mappings, serialized files, historical agent objects, subclasses, and arbitrary
legacy payloads.

The approved path is:

`governed catalogue -> discovery -> eligibility -> normalization -> factual comparison -> orchestration -> explanation projection -> governed handoff`

No future ranking component may bypass this path or reconstruct comparison facts
from raw documents or historical outputs.

## Change rule

A component changes classification only through an explicit architecture record
that states its new status, migration boundary, accepted input/output contracts,
and certification evidence.
