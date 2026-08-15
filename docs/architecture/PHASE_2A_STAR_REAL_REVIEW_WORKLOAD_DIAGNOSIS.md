# Phase-2A — Star Comprehensive Real Review Workload Diagnosis

Status: **ACTIVE DIAGNOSTIC CHECKPOINT — REVIEW SCALING NOT YET PROVEN**

## Purpose

Record the first real Phase-2A extraction-to-review-to-MO-029 workload result from the governed Star Comprehensive policy wording and identify the demonstrated upstream bottleneck without weakening review-risk governance.

## Governed source

- Entity: `star_health:star_comprehensive`
- Registered immutable policy wording SHA-256: `b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f`
- Parsed artifact: `processed/pdf_parse/b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f.json`
- Parse result observed locally: 48 pages, 48 pages with text.

## Real workload result

The existing generic pipeline was executed on the real governed source:

`registered source -> parsed PDF -> currency candidates -> reviewer-ready groups -> MO-029 review-risk routing`

Observed results:

- Currency candidates: **12**
- Reviewer-ready groups: **12**
- Grouping compression: **0%**
- MO-029 Critical: **0**
- MO-029 High: **12**
- MO-029 Medium: **0**
- MO-029 Low: **0**
- Adjudication created: **none**
- Publication created: **none**

The Phase-2A onboarding batch audit subsequently reported:

- Products: **3**
- Products with missing data: **0**
- Missing/undeclared artifacts: **0**
- Review routing records: **12**
- Review routing N/A because no review input: **2**
- Risk tiers: `critical=0, high=12, medium=0, low=0`
- Product-specific production-code changes: **0**

Star is now correctly declared `required_when_review_input_exists` for review-risk routing. Bajaj My Health Care and Activ One remain `not_applicable_no_review_input` until reviewer-ready inputs actually exist.

## Flag diagnosis

Observed review flags across the 12 real Star groups:

- `benefit_scope_unresolved`: **12 / 12**
- `role_selection_required`: **12 / 12** — structural/neutral by itself in MO-029
- `table_layout_binding_possible`: **2 / 12**
- `unresolved_role_hint`: **1 / 12**

Therefore the universal High routing is driven by the universal `benefit_scope_unresolved` flag. The sparse table-layout and role-hint ambiguities do not explain the 12/12 High result.

## Architecture interpretation

This checkpoint does **not** prove sub-linear review scaling. The first real sample shows no grouping compression and no reduction in senior-review demand.

It also does **not** demonstrate that all 12 monetary clauses are inherently high-risk. The current currency review scope helper intentionally recognizes only a small deterministic vocabulary. Product pressure has now demonstrated that this limited vocabulary may itself be the upstream bottleneck.

The next diagnostic question is therefore narrow:

> For each unresolved monetary occurrence, does the already-bounded local evidence contain a reusable, deterministic benefit/section cue that can safely be represented as a review-only scope hint?

Only real evidence may justify extending the generic scope resolver.

## Guardrails

1. Do **not** lower MO-029 risk thresholds merely to improve workload metrics.
2. Do **not** reclassify `benefit_scope_unresolved` as lower risk while the scope is genuinely unresolved.
3. Do **not** add Star-specific labels, branches, hashes, product IDs, or reasoning to production scope-resolution code.
4. Any new scope cue must be generic, evidence-bounded, deterministic, review-only, and demonstrated by real product pressure.
5. Scope inference must remain distinct from applicability, entitlement, fact acceptance, and publication.
6. Table/column binding must remain unresolved when layout evidence is insufficient.
7. The Phase-2A parent gate remains **ACTIVE** until real review-effort scaling evidence and broader regression validation support closure.
