# Star Comprehensive Restoration Source-Shape Inspection — Closure

Status: **CLOSED PENDING MERGE**

## Purpose

This milestone inspected the current Star Comprehensive restoration clause
before authorizing any manufacturing. It did not assume that the existing
Activ One restoration shape was universal, and it did not pre-authorize a new
contract, evaluator, comparison rule, or runtime path.

## Discovery

Star restoration is not an unimplemented capability. The repository already
contains an approved, published `ProductBenefitImplementation` used by the
governed restoration comparison and assessment paths.

The correct question was therefore:

> Does the existing Star implementation match the currently registered primary
> policy wording, and is every retained assertion backed by qualified evidence?

## Current authoritative source

The registered primary source is:

- Star Comprehensive Insurance Policy;
- UIN `SHAHLIP26044V092526`;
- policy wording `POL / COMP / V.24 / 2025`;
- SHA-256
  `b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f`;
- Section II.13 on source page 13, printed page 12 of 47; and
- Important Note 28 on source page 45, printed page 44 of 47.

The repository-backed source registration preserves the exact page excerpts
and their page-level hashes. The source PDF itself remains an external,
gitignored archive input, consistent with the existing foundation contract.

## Proven Star shape

The current clause explicitly establishes:

- 100% restoration of Basic Sum Insured;
- one activation during the Policy Period;
- immediate activation only after exhaustion of Basic Sum Insured and accrued
  Cumulative Bonus, if any;
- use only for a subsequent hospitalization;
- use for the same illness/disease, subject to the `Any One Illness` boundary;
- relapse within 45 days is treated as the same hospitalization;
- exact scope to Sections II.1, II.3, II.5, II.6, II.7, II.8 and II.11;
- separate availability for each policy year of a multi-year policy;
- no carry-over between policy years; and
- floater operation through Important Note 28(ii)'s related-benefits context.

The existing generic restoration concept and typed mechanic vocabulary preserve
this shape without adding product-specific architecture.

## Fail-closed boundaries

The source does not establish a separate reusable proposition for:

- partial use of the restored amount;
- maximum restoration liability per claim; or
- a detailed utilization sequence beyond the exhaustion trigger.

Those mechanics remain absent. They must not be copied from Activ One or inferred
from generic restoration behavior.

Policy-specific applicability also remains subject to the Policy Schedule and
any Endorsement. The implementation now preserves that limitation explicitly.

## Evidence-governance correction

The existing implementation cited both policy wording and prospectus. The
policy wording is registered and byte-bound. The prospectus is not present in
the approved registered source bundle, has no repository-backed registration,
and was already documented as unqualified in the Star identity record.

Because the registered policy wording independently supports every retained
mechanic, the smallest fail-closed correction is to:

- remove the unverified prospectus from governed restoration evidence;
- bind every retained mechanic to the registered policy wording only; and
- leave the benefit semantics otherwise unchanged.

No new mechanic was manufactured and no comparison, ranking, recommendation,
suitability, entitlement, claim-admissibility, or payment behavior was added.

## Closure decision

Final classification:

**REUSE EXISTING IMPLEMENTATION WITH BOUNDED GOVERNANCE CORRECTION**

- generic concept fit: **confirmed**;
- new restoration implementation: **not required**;
- new runtime architecture: **not authorized**;
- unverified secondary evidence: **removed**; and
- unsupported mechanics: **withheld**.

The next isolated milestone is Star Comprehensive initial waiting-period
current-source manufacturing.
