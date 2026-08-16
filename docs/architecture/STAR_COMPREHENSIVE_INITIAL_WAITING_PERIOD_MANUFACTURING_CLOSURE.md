# Star Comprehensive Initial Waiting-Period Manufacturing — Closure

Status: **CLOSED PENDING MERGE**

## Purpose

This milestone manufactures only the current-source propositions needed to
certify Star Comprehensive's base 30-day initial waiting period. It follows the
HARM-1A result that `not covered yet` is representable without adding a new
coverage-state architecture.

## Current authoritative source

The governing evidence is the registered Star Comprehensive policy wording:

- UIN `SHAHLIP26044V092526`;
- policy wording `POL / COMP / V.24 / 2025`;
- document SHA-256
  `b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f`;
- Section III.3, source page 32, printed page 31 of 47; and
- page-text SHA-256
  `214466445fab2fd7fec30d951696479d4999bfc74aea13af40a1b80eddef77eb`.

No prospectus, schedule instance, or inferred product variant is used.

## Source-proven rule shape

The current wording establishes:

- a 30-day initial waiting period;
- application to expenses related to treatment of any illness;
- measurement from the first policy commencement date;
- an accident exception only when the claim is otherwise covered;
- non-application when the insured person has Continuous Coverage for more
  than twelve months; and
- fresh application to an enhanced Sum Insured when a higher Sum Insured is
  granted subsequently.

These propositions map exactly to the existing generic `waiting_period` topic's
duration, subject, start basis, applicability, continuity, and exception
components. No new generic component or runtime architecture is required.

## Fail-closed boundary

The phrase `within 30 days from the first policy commencement date` does not by
itself define whether the first active date should use an inclusive or exclusive
calendar-boundary convention. This milestone therefore does **not**:

- calculate an exact first-active date;
- select either existing timeline activation convention;
- update the Activ One-specific waiting-period timeline evidence profile; or
- assert that an accident claim is covered, admissible, approved, or payable.

The manufactured artifact is a governed rule-certification case, not a claim
decision or customer-facing publication.

## Closure decision

Final classification:

**MANUFACTURE WITH EXISTING GENERIC WAITING-PERIOD CONTRACT**

- generic concept fit: **confirmed**;
- new architecture: **not authorized**;
- exact timeline arithmetic: **withheld**;
- accident exception: **preserved as conditional**; and
- policy Schedule, Endorsement, continuity, and claim facts: **still required
  for policy-instance conclusions**.

The next isolated milestone is Bajaj explicit scoped copayment manufacturing.
