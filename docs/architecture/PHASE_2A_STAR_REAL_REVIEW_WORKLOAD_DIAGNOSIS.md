# Phase-2A — Star Comprehensive Real Review Workload Diagnosis

Status: **STAR REVIEW-SCALING CHECKPOINT COMPLETE — SENIOR-REVIEW DEMAND REDUCED 50%; PHASE-2A PARENT GATE REMAINS ACTIVE**

## Purpose

Record the first real Phase-2A extraction-to-review-to-MO-029 workload result from the governed Star Comprehensive policy wording, the evidence-backed generic scope-resolution improvement that followed, and the measured effect on review routing without weakening review-risk governance.

## Governed source

- Entity: `star_health:star_comprehensive`
- Registered immutable policy wording SHA-256: `b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f`
- Parsed artifact: `processed/pdf_parse/b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f.json`
- Parse result observed locally: 48 pages, 48 pages with text.

## Real workload baseline

The generic pipeline was executed on the real governed source:

`registered source -> parsed PDF -> currency candidates -> reviewer-ready groups -> MO-029 review-risk routing`

Initial observed results:

- Currency candidates: **12**
- Reviewer-ready groups: **12**
- Grouping compression: **0%**
- MO-029 Critical: **0**
- MO-029 High: **12**
- MO-029 Medium: **0**
- MO-029 Low: **0**
- Adjudication created: **none**
- Publication created: **none**

Initial flag diagnosis:

- `benefit_scope_unresolved`: **12 / 12**
- `role_selection_required`: **12 / 12** — structural/neutral by itself in MO-029
- `table_layout_binding_possible`: **2 / 12**
- `unresolved_role_hint`: **1 / 12**

The universal High routing was therefore driven by the universal `benefit_scope_unresolved` flag.

## Evidence-backed generic improvement

The 12 bounded Star evidence windows were inspected. They demonstrated reusable review-only scope cues for cases including:

- Air Ambulance
- Home Care Treatment
- Cumulative Bonus
- Bariatric Surgery
- Delivery / New Born
- per-consultation limits

The generic currency review scope helper was extended only for reusable evidence cues demonstrated by real product pressure. No Star identity, hash, product branch, entitlement decision, or publication logic was added.

Table-bound ambiguity and unresolved-role ambiguity remain fail-closed.

## Measured post-improvement result

After regenerating the reviewer-ready groups and rerunning MO-029 on the same 12 real candidates, the Phase-2A batch audit reported:

- Products: **3**
- Products with missing data: **0**
- Missing/undeclared artifacts: **0**
- Review routing records: **12**
- Review routing N/A because no review input: **2**
- MO-029 Critical: **0**
- MO-029 High: **6**
- MO-029 Medium: **6**
- MO-029 Low: **0**
- Product-specific production-code changes: **0**

Therefore:

- Senior-review demand changed from **12 / 12** to **6 / 12**.
- Standard-review routing increased from **0 / 12** to **6 / 12**.
- Measured reduction in senior-review demand: **50%**.
- The reduction was achieved by improving deterministic upstream context, not by weakening MO-029 risk thresholds.
- Grouping compression remains **0%**; the demonstrated efficiency gain is review-tier routing, not candidate-count reduction.

## Residual High-risk classification

The six remaining High groups were inspected against their bounded evidence rather than optimized mechanically.

They fall into legitimate residual ambiguity classes:

1. **Bariatric table-bound amount** — scope is recognized as `bariatric_surgery`, but the evidence explicitly points to limits in a table. `table_layout_binding_possible` remains a valid High-risk reason.
2. **Second bariatric amount with clipped local context** — the bounded evidence starts after enough of the preceding phrase has been lost that automatically borrowing the neighboring amount's bariatric scope would be unsafe. It remains unresolved and High.
3. **Dense treatment/procedure table row — first occurrence** — the amount is embedded in a flattened sequence of Sum Insured and per-treatment limits. Safe row/column binding is unavailable in the bounded evidence, so scope remains unresolved.
4. **Delivery / New Born table amount** — `new_born_cover` scope is recognized, but the monetary role remains unresolved across a multi-column table. `unresolved_role_hint` correctly retains High routing.
5. **Dense treatment/procedure table row — second occurrence** — as above, flattened row/column structure prevents safe scope binding.
6. **Section-bound Sum Insured limit** — the evidence says the amount applies “under this Section,” but the governing section heading is not present in the bounded candidate. Inferring the missing section from product knowledge would cross the evidence boundary.

These six groups are therefore treated as legitimate senior-review work for this checkpoint. No further Star-specific or keyword-only optimization is justified.

## Architecture interpretation

This is the first real evidence that the Phase-2A architecture can reduce expensive review effort through reusable upstream context resolution while preserving fail-closed governance.

It is not yet sufficient to claim that overall Phase-2A review throughput scales sub-linearly across products or insurers. The evidence currently proves one real product sample and one monetary extraction primitive.

The Star diagnostic itself is complete. Further reduction in these six High groups would require new generic structural capabilities such as table row/column binding or section-heading propagation, and those capabilities should only be built when additional real product pressure proves they are broadly necessary.

The remaining Phase-2A work is therefore not more Star optimization. It is regression/certification evidence and broader review-scaling evidence where real reviewer-ready inputs exist.

## Guardrails

1. Do **not** lower MO-029 risk thresholds merely to improve workload metrics.
2. Do **not** reclassify `benefit_scope_unresolved` as lower risk while scope is genuinely unresolved.
3. Do **not** add Star-specific labels, branches, hashes, product IDs, or reasoning to production scope-resolution code.
4. Any new scope cue must be generic, evidence-bounded, deterministic, review-only, and demonstrated by real product pressure.
5. Scope inference remains distinct from applicability, entitlement, fact acceptance, and publication.
6. Table/column binding remains unresolved when layout evidence is insufficient.
7. Grouping compression and review-tier reduction are separate metrics and must not be conflated.
8. Missing governing section context must not be reconstructed from product identity or external knowledge inside the review layer.
9. The Phase-2A parent gate remains **ACTIVE** until broader real-product review evidence and regression validation support closure.
