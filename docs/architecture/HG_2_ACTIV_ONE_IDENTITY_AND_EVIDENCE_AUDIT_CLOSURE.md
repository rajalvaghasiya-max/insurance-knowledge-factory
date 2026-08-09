# HG-2 — Activ One Identity and Evidence Audit Closure

## Status

**CLOSED**

## Purpose

HG-2 establishes the governed identity and source-evidence boundary for the Aditya Birla Health Activ One NXT Super Reload generalization pilot. The objective is to prove that the second-product pilot can start from an explicitly approved product identity and byte-verified source documents, without treating historical intelligence outputs as authoritative runtime facts.

## Governed product identity

Approved by the CTO in the PolicyScna project conversation on 2026-08-09:

- Entity ID: `aditya_birla_health:activ_one`
- Canonical product name: `Activ One`
- UIN: `ADIHLIP24097V012324`

Executable reference:

- `docs/architecture/aditya_birla_activ_one_product_identity_reference_spec.json`

Certification:

- `tests/insurance_intelligence/test_activ_one_governed_identity_reference.py`
- focused identity suite: **32 passed**

The older automated identity audit remains corroborating evidence only and is not the human approval of record.

## Byte-verified source documents

The local source files were independently hashed in PowerShell and matched the later governed evidence identities exactly.

### Policy wording

Repository source path:

`knowledge/health/aditya_birla_health/activ_one/documents/policy_wording.pdf`

Verified SHA-256:

`d7726811cfdf2c3c31c3750eb0bd4a55203b20cf79d44fc6849dbc77ba556451`

Authoritative Super Reload locations previously isolated on the governed later line:

- Activ One NXT — Section C.8 `Super Reload`, policy wording page 30
- Annexure III Product Benefit Table, policy wording page 46

### Prospectus

Repository source path:

`knowledge/health/aditya_birla_health/activ_one/documents/prospectus.pdf`

Verified SHA-256:

`8923d6457d368c9d80d097032a7b784c65b30ba07ae68ea7474af7569332fa56`

Supporting locations previously isolated on the governed later line:

- Section C.10 `Super Reload`, prospectus page 3
- Super Reload Illustration — NXT Plan, prospectus page 10

## Evidence boundary

The generalization pilot may rely on the byte-verified source identities and the exact section/page locators above as the starting evidence boundary.

Historical artifacts such as:

- `knowledge/health/aditya_birla_health/activ_one/intelligence/product_intelligence.json`
- `knowledge/health/aditya_birla_health/activ_one/intelligence/policy_intelligence.json`
- legacy validation outputs

remain **corroborating/non-authoritative** for the active governed reasoning path. They may help locate source text but may not substitute for source-backed governed evidence.

## Reuse rule

Later MO-025 work may be inspected for already-proven semantic structure and evidence identities, but its implementation stack must not be merged wholesale into this branch. Any reused structure must be selectively introduced and recertified against the current Health Generalization baseline.

## Exit criteria satisfied

- second product identity explicitly human-approved;
- governed `product_identity_reference_v1` created;
- runtime identity resolution certified;
- exact policy wording and prospectus hashes verified locally;
- Super Reload source locations isolated;
- historical output authority boundary explicitly preserved.

HG-2 is therefore closed. The next phase is **HG-3 — Restoration topic and semantic contract**.
