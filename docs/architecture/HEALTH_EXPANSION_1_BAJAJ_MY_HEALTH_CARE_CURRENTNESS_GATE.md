# HEALTH-EXPANSION-1 — Bajaj My Health Care Currentness Gate

**Status:** CERTIFIED  
**Date:** 2026-08-15

## Certification result

HEALTH-EXPANSION-1 is certified for Bajaj General Insurance My Health Care Plan.

Validated on the current branch:

```text
focused Bajaj publication gate      3 passed
publication eligibility combined   10 passed
Health subsystem                  109 passed
regressions                         0
```

The certified current immutable policy wording is:

- product: `bajaj_allianz_general:my_health_care`
- logical document id: `bajaj_my_health_care_policy_wording_v1`
- document version id: `docver_bajaj_my_health_care_policy_wording_v1_05dc291324340d52`
- SHA-256: `05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158`
- UIN: `BAJHLIP26074V022526`
- temporal status: `current_observed_reviewed`
- evidence review: `eligible_for_evidence_review`
- current entitlement: `eligible`

## Why this milestone mattered

The historical Bajaj policy wording reference used SHA-256:

`9479fe6f6ce729f95f75c43e9ef00c76f4aa8917650783fe8f5d7cb37844cade`

A fresh official download on 2026-08-15 produced:

`05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158`

The system did not overwrite or silently promote the historical version. Instead it followed the governed version-transition path:

```text
historical hash differs from fresh official bytes
        ↓
retain new bytes as immutable source
        ↓
GenericSourceRegistration
        ↓
reviewed classification
        ↓
resolved product/document identity
        ↓
byte-identical official source observation
        ↓
structured currentness evidence
        ↓
human-reviewed temporal decision
        ↓
current_observed_reviewed
        ↓
existing FactPublicationEligibilityContract
```

No product-specific reasoning code was introduced.

## Historical-baseline retention note

The current checkout does not retain the historical `9479fe6f...` PDF bytes or the generated historical `policy_wording_registration.json`.

Git history retains the historical hash/path references and earlier observation metadata. The historical version therefore remains metadata-only provenance in this checkout. It was not reconstructed, fabricated, or silently replaced.

This retention gap did not justify weakening any hash, identity, currentness, or publication guard.

## Certified governance behavior

### 1. New immutable version registration

The fresh official `05dc2913...` PDF was registered through the existing generic registration contract as a distinct immutable document version.

Result:

```text
source registration  generic_sources_registered_evidence_review_required
evidence candidates  53
authority role        primary_legal
```

### 2. Classification and identity

The new version passed the existing generic governance path:

```text
classification       reviewed_document_classifications_recorded_not_published
product identity     resolved
document resolution  resolved
```

The initial new-version overlay correctly remained:

```text
temporal             compatibility_unverified
current entitlement  blocked
```

### 3. Currentness evidence

The exact immutable version was re-observed from the official source and produced:

```text
byte comparison      byte_identical_observed
currentness evidence sufficient_for_current_observed_review
positive evidence    1
```

The evidence record remained evidence-only and did not itself make a temporal decision.

### 4. Reviewed temporal transition

The reviewed identity-resolution overlay then moved the exact version to:

```text
resolution           resolved
temporal             current_observed_reviewed
evidence review      eligible_for_evidence_review
current entitlement  eligible
```

This transition was accepted only because the existing identity-resolution contract could bind:

- the same registration/document version;
- a human-reviewed byte-identical source observation; and
- validated structured currentness evidence.

### 5. Publication eligibility pressure

The final adversarial test proved the generic publication contract behaves correctly for the Bajaj version:

```text
compatibility_unverified
        → blocked for publication review

current_observed_reviewed
        → eligible_for_publication_review
```

In both states:

```text
publication_state = not_published
```

Currentness therefore removes only the currentness blocker. It does not publish a product fact.

## Architecture conclusion

HEALTH-EXPANSION-1 proves the post-fitness architecture can absorb a real insurer document-version transition without introducing a new abstraction or product-specific runtime logic.

The architecture correctly preserved:

- immutable document versions;
- source provenance;
- classification boundaries;
- product/document identity separation;
- currentness as a reviewed decision;
- fail-closed publication behavior;
- separation between eligibility and publication.

## Guardrails retained

- Do not recreate or mutate the missing historical `9479fe6f...` bytes.
- Do not infer semantic equivalence solely from matching UIN/title.
- A working official URL alone is insufficient for currentness.
- Currentness eligibility is not fact publication.
- No Bajaj-specific reasoning branch is authorized.
- Product expansion continues as governed data unless real product pressure proves a generic architecture defect.

## Exit criterion — PASSED

```text
new document version registered immutably               PASS
new version identity/classification reviewed            PASS
new version currentness reviewed                        PASS
publication eligibility through existing generic gate   PASS
focused Bajaj pressure                                  3 passed
combined publication pressure                          10 passed
Health subsystem                                      109 passed
regressions                                             0
```

**HEALTH-EXPANSION-1: CERTIFIED.**
