# HEALTH-EXPANSION-1 — Bajaj My Health Care Currentness Gate

**Status:** ACTIVE — VERSION TRANSITION REQUIRED  
**Date:** 2026-08-15

## Why this is the next milestone

AR-2.5, AR-3.0 and AFR-N1 are closed. The roadmap therefore returns to Health expansion as governed data rather than new architecture.

Bajaj General Insurance My Health Care Plan is selected as the next product because:

- the product identity is already resolved;
- the registered policy wording is already bound to UIN `BAJHLIP26074V022526`;
- the existing identity overlay deliberately leaves temporal status at `compatibility_unverified`;
- publication eligibility correctly blocks materialized facts while currentness is unresolved;
- the official Bajaj product page exposes My Health Care Plan and links its policy wording;
- the linked policy wording displays UIN `BAJHLIP26074V022526` and title `MY HEALTH CARE PLAN (PLAN 1)`.

This is therefore a currentness/version-governance completion task, not a new product-specific reasoning task.

## Existing safe behavior

The current fact-publication eligibility contract already blocks `compatibility_unverified` documents.

The gate must not be weakened. The task is to determine whether the registered immutable document remains the current official wording or whether the official source has moved to a new immutable document version.

## Fresh byte verification result

Registered / retained June 2026 policy wording SHA-256:

`9479fe6f6ce729f95f75c43e9ef00c76f4aa8917650783fe8f5d7cb37844cade`

Fresh official download on 2026-08-15 SHA-256:

`05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158`

Result:

```text
05dc2913... != 9479fe6f...
        ↓
bytes changed at official source
        ↓
DO NOT mark old registered version current
        ↓
retain changed-byte observation
        ↓
register new immutable document version
        ↓
classify + resolve identity + review currentness
        ↓
only then evaluate fact publication eligibility
```

The mismatch is evidence of a document-version transition. It is not permission to overwrite the old registration or promote existing facts to current status.

## Governed mismatch recording

The repository already provides `SourceObservationRecord`, which compares one observed official PDF against one registered immutable version and emits `bytes_changed_observed` when the hashes differ. The observation record itself does not decide temporal status or publication eligibility.

The reviewed observation specification is:

`docs/architecture/health_expansion_1_bajaj_my_health_care_source_observation_20260815_spec.json`

It binds the fresh hash to the existing registered version for the sole purpose of recording that the official bytes changed.

## Required evidence chain from here

```text
old registered version: 9479fe6f...
        ↓ fresh official observation
new observed bytes: 05dc2913...
        ↓
SourceObservationRecord = bytes_changed_observed
        ↓
retain 05dc2913... PDF as immutable artifact
        ↓
new generic source registration / document version
        ↓
classification + product identity review
        ↓
new-version currentness evidence
        ↓ reviewed temporal decision
        ↓
existing FactPublicationEligibilityContract
```

## Guardrails

- Do not mutate or replace the `9479fe6f...` registration.
- Do not mark the old document `current_observed_reviewed`.
- Do not copy facts from the old version into the new version merely because UIN/title appear unchanged.
- A matching UIN does not prove byte identity or semantic equivalence.
- A working official URL alone is insufficient to prove currentness.
- No fact is published merely by registering the new version.
- No Bajaj-specific reasoning branch is authorized.
- Existing fail-closed publication behavior remains unchanged.

## Immediate next action

1. retain the freshly downloaded `05dc2913...` PDF under the immutable archive path named in the source-observation spec;
2. run `scripts.run_source_observation_record` against the spec;
3. require output `Byte comparison : bytes_changed_observed`;
4. preserve that governed observation record;
5. then onboard the `05dc2913...` artifact as a new immutable document version through existing generic registration/classification/identity contracts.

## Exit criterion

```text
changed-byte official observation retained
+ new document version registered immutably
+ new version identity/classification reviewed
+ new version currentness reviewed
+ publication eligibility behaves through existing generic gate
+ regressions = 0
```
