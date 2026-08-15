# HEALTH-EXPANSION-1 — Bajaj My Health Care Currentness Gate

**Status:** ACTIVE — NEW IMMUTABLE VERSION REGISTRATION REQUIRED  
**Date:** 2026-08-15

## Why this is the next milestone

AR-2.5, AR-3.0 and AFR-N1 are closed. The roadmap therefore returns to Health expansion as governed data rather than new architecture.

Bajaj General Insurance My Health Care Plan is selected as the next product because:

- historical product/document identity was already resolved;
- the historical policy wording was bound to UIN `BAJHLIP26074V022526`;
- the historical identity overlay deliberately left temporal status at `compatibility_unverified`;
- publication eligibility correctly blocks materialized facts while currentness is unresolved;
- the official Bajaj product page exposes My Health Care Plan and links its policy wording;
- the linked policy wording displays UIN `BAJHLIP26074V022526` and title `MY HEALTH CARE PLAN (PLAN 1)`.

This is therefore a currentness/version-governance completion task, not a new product-specific reasoning task.

## Existing safe behavior

The current fact-publication eligibility contract already blocks `compatibility_unverified` documents.

The gate must not be weakened. The task is to determine whether the historical registered immutable document remains the current official wording or whether the official source has moved to a new immutable document version.

## Fresh byte verification result

Historical registered / June 2026 policy wording SHA-256:

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
retain 05dc2913... as a new immutable document version
        ↓
classification + identity + currentness review
        ↓
only then evaluate fact publication eligibility
```

## Historical-baseline recovery result

The current `feature/mo-028b-health-waiting-period-coverage` checkout does not contain:

- the historical `9479fe6f...` PDF bytes; or
- the generated historical `policy_wording_registration.json` required by `SourceObservationRecord`.

Git history preserves the historical hash/path references and June source-observation metadata, but not the historical PDF itself or a restorable generated registration artifact.

Therefore the changed-byte observation cannot be replayed through `SourceObservationRecord` in this checkout without fabricating the missing historical baseline. That replay is no longer a prerequisite for forward progress.

The historical version remains metadata-only provenance:

```text
historical identity/hash reference: 9479fe6f...
actual bytes in current checkout:    unavailable
current official bytes:              05dc2913...
```

This is a repository-retention gap, not permission to reconstruct the old bytes or registration.

## New-version registration path

The `05dc2913...` PDF is retained at:

`archive/raw_pdf/bajaj_allianz_general/policy_wording/My-Health-Care-Plan1-PW__05dc29132434.pdf`

The reviewed registration specification is:

`docs/architecture/health_expansion_1_bajaj_my_health_care_current_generic_sources_registration_spec.json`

It uses the same logical document identity (`bajaj_my_health_care_policy_wording_v1`) but a new immutable source hash, producing a new document-version identity through the existing generic registration contract.

The new registration output is versioned rather than overwriting any historical name:

`knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/generic_source_registration/policy_wording_registration_05dc29132434.json`

## Required evidence chain from here

```text
current official PDF: 05dc2913...
        ↓
GenericSourceRegistration
        ↓
new immutable document version
        ↓
new-version classification
        ↓
product identity review
        ↓
currentness evidence + reviewed temporal decision
        ↓
existing FactPublicationEligibilityContract
```

## Guardrails

- Do not recreate or mutate the missing `9479fe6f...` bytes.
- Do not mark the historical version `current_observed_reviewed`.
- Do not overwrite the historical logical references with the new registration output.
- Do not copy facts from the historical version into the new version merely because UIN/title appear unchanged.
- A matching UIN does not prove semantic equivalence.
- A working official URL alone is insufficient to prove currentness.
- No fact is published merely by registering the new version.
- No Bajaj-specific reasoning branch is authorized.
- Existing fail-closed publication behavior remains unchanged.

## Immediate next action

1. run the existing generic source-registration runner against the `05dc2913...` spec;
2. verify a new document-version registration is produced from the retained bytes;
3. inspect the resulting document version and candidate evidence count;
4. only then create/update classification and identity-review specs for that exact new version.

## Exit criterion

```text
new document version registered immutably
+ new version identity/classification reviewed
+ new version currentness reviewed
+ publication eligibility behaves through existing generic gate
+ regressions = 0
```
