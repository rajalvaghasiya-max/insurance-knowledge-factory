# HEALTH-EXPANSION-1 — Bajaj My Health Care Certification Closure

**Status:** IMPLEMENTED — VALIDATION PENDING  
**Date:** 2026-08-15

## Scope

This closure certifies the first post-Architecture-Fitness Health expansion case using Bajaj General Insurance My Health Care Plan.

The milestone intentionally uses the existing governed architecture without adding insurer-specific production reasoning.

## Governing immutable document version

Current observed policy wording SHA-256:

`05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158`

Registered document version:

`docver_bajaj_my_health_care_policy_wording_v1_05dc291324340d52`

Product identity:

`bajaj_allianz_general:my_health_care`

UIN:

`BAJHLIP26074V022526`

## Proven execution chain

The local governed runs have established the following chain for the exact immutable 05dc version:

```text
fresh official retrieval
    -> SHA-256 05dc2913...
    -> generic source registration
       status: generic_sources_registered_evidence_review_required
       primary_legal sources: 1
       evidence candidates: 53
    -> reviewed document classification
    -> reviewed product identity
       resolution: resolved
    -> initial document identity resolution
       temporal: compatibility_unverified
       current entitlement: blocked
    -> retained official source observation
       byte comparison: byte_identical_observed
    -> document currentness evidence
       conclusion: sufficient_for_current_observed_review
       positive evidence: 1
    -> reviewed document identity resolution
       temporal: current_observed_reviewed
       current entitlement: eligible
```

No fact is published by any stage above.

## Historical version handling

The earlier registered/source-observed version was identified by SHA-256:

`9479fe6f6ce729f95f75c43e9ef00c76f4aa8917650783fe8f5d7cb37844cade`

Its raw PDF and generated registration artifact are not retained in the current checkout. The project therefore preserves that version as metadata-only historical provenance and does not reconstruct, overwrite, or falsely certify it.

The 05dc version was onboarded as a new immutable document version rather than mutating the historical identity.

## Publication-gate pressure

`tests/health/test_health_expansion_1_bajaj_currentness_publication_gate.py` exercises the existing generic `FactPublicationEligibilityContract` against the exact Bajaj 05dc source identity.

Required behavior:

```text
compatibility_unverified + blocked current entitlement
    -> blocked for publication review

current_observed_reviewed + eligible current entitlement
    -> eligible_for_publication_review

both states
    -> publication_state remains not_published
```

This distinction is the milestone's central certification result: reviewed currentness removes only the currentness blocker. It does not publish a product fact and does not bypass evidence review, human review, selection, materialization, or publication governance.

## Architecture result

The existing architecture supported the entire version-transition and currentness path without new production abstractions:

- immutable generic source registration;
- version-specific document classification;
- product identity resolution;
- source observation with byte comparison;
- structured currentness evidence;
- reviewed temporal decision;
- fail-closed fact publication eligibility.

No Bajaj-specific reasoning branch, database migration, knowledge-graph change, or publication bypass was required.

## Validation required for certification

Focused:

```powershell
python -m pytest -q tests/health/test_health_expansion_1_bajaj_currentness_publication_gate.py
```

Expected:

```text
3 passed
```

Then run the existing publication-gate regression together with the focused pressure:

```powershell
python -m pytest -q `
  tests/health/test_fact_publication_eligibility.py `
  tests/health/test_health_expansion_1_bajaj_currentness_publication_gate.py
```

Expected:

```text
10 passed
```

Then run the Health test subsystem or the repository's established broader regression command before changing this document to CERTIFIED.

## Certification rule

HEALTH-EXPANSION-1 is CERTIFIED only when:

- the focused Bajaj currentness/publication pressure is green;
- existing generic publication-eligibility regressions remain green;
- broader Health/repository regressions remain green;
- no production-code bypass is introduced.
