# PHASE-2A — Onboarding Path & MO-029 Review-Scaling Audit

**Status:** AUDIT COMPLETE — GENERIC REVIEW ROUTING GAP CONFIRMED  
**Date:** 2026-08-15

## Scope

This audit is intentionally product-neutral. Its purpose is to determine whether normal Health onboarding can scale as governed data with zero product-identity-bearing production code, and whether the current review path already satisfies the roadmap's MO-029 risk-tiered-review direction.

## Standing rule

```text
normal new Health product onboarding
=
0 product-identity-bearing production code
```

Product-specific source paths, hashes, identity, version/currentness, evidence, facts, rules, mechanics and residue belong in governed data/spec artifacts.

## A. Current onboarding path

The Bajaj HEALTH-EXPANSION-1 exercise provides a concrete, architecture-correct baseline:

| Step | Current mechanism | Classification | Phase-2A assessment |
|---|---|---|---|
| retain immutable source | archive path + SHA-256 | governed data / operational step | acceptable; still manual acquisition |
| generic source registration | `GenericSourceRegistration` + JSON spec | automated generic code + governed spec | reusable as-is |
| document classification | `DocumentClassificationPolicy` + JSON spec | automated generic code + human-reviewed spec | reusable as-is |
| product identity reference | `ProductIdentityReference` + JSON spec | automated generic code + human-reviewed spec | reusable as-is |
| document identity/version overlay | `DocumentIdentityResolutionOverlay` + JSON spec | automated generic code + human review | reusable as-is |
| official source observation | `SourceObservationRecord` + JSON spec | automated generic code + retained source evidence | reusable as-is |
| currentness evidence | `DocumentCurrentnessEvidenceRecord` + JSON spec | automated generic code + evidence-only artifact | reusable as-is |
| reviewed temporal decision | identity overlay review | human review + generic contract | reusable as-is |
| candidate extraction | generic extraction primitives | automated generic code | reusable where concept supported |
| candidate grouping/review preparation | review-layer contracts | automated generic code | reusable where primitive supported |
| reviewer decision | per-review-group explicit decision | human review | safe but linear-scaling bottleneck |
| fact selection/materialization | generic contracts | automated generic code after review | reusable as-is |
| publication eligibility | generic contract | automated generic code | reusable as-is |

### Onboarding-path conclusion

The source/identity/currentness side already supports data-only onboarding. HEALTH-EXPANSION-1 demonstrated this without Bajaj-specific runtime logic.

The principal Phase-2A scaling risk is not product identity or currentness plumbing. It is repeated manual construction/review work and, especially, mandatory one-by-one evidence-group review downstream of extraction.

No normal onboarding step identified here justifies a product-specific Python module.

## B. Existing prioritisation is not MO-029

`factory_core/canonical/coverage_gap_prioritization.py` supports explicit `critical/high/medium/low` priority tiers for a reviewed research backlog.

That component is useful but it is not risk-tiered review routing:

- priorities are supplied explicitly by a human-reviewed spec;
- it prioritizes evidence-research gaps rather than evidence-review groups;
- it does not determine review depth or reviewer routing;
- it does not change downstream fact acceptance;
- it deliberately does not calculate opaque business-importance scores.

Therefore Phase 2A must not claim MO-029 is operational merely because priority-tier vocabulary exists.

## C. Review pipeline scaling finding

The current Health currency-review path is correctly fail-closed:

1. deterministic extraction candidates are grouped into reviewer-ready evidence groups;
2. review flags expose unresolved/conflicting scope and role cues;
3. `ReviewerDecisionRecordContract` creates one pending decision per review group;
4. a human must explicitly record `accept`, `reject`, `split_further`, or `defer`;
5. only accepted records may proceed to later governed selection/materialization;
6. publication remains separately gated.

This is safe, but it implies review work grows approximately with review-group count.

### Important non-goal

MO-029 must **not** solve this by auto-accepting a fact based on a risk score.

Risk tiering is review orchestration, not evidence adjudication.

## D. Smallest generic MO-029 step

Introduce one generic, deterministic, read-only **review-risk routing contract** between review-group generation and reviewer decision recording.

The contract may:

- consume existing deterministic `review_flags`, role hints, condition hints and bounded-evidence metadata;
- assign a transparent risk tier;
- assign a review route/intensity;
- expose the exact reasons for the tier;
- aggregate workload counts by tier;
- remain source-hash-bound;
- fail closed on unknown flags where required.

The contract must not:

- accept/reject evidence;
- populate selected role or benefit scope;
- create a canonical fact;
- modify a reviewer decision;
- infer product applicability;
- infer document currentness;
- publish knowledge;
- contain insurer/product identity logic.

## E. Initial deterministic routing policy

The first routing policy should be deliberately conservative:

- **critical** — contradictory/misclassification signals that can materially change the meaning of a monetary amount;
- **high** — unresolved role/scope, schedule/band binding uncertainty, or table-layout binding risk;
- **medium** — repeated evidence or deterministic inferred scope requiring confirmation but without critical/high ambiguity;
- **low** — bounded evidence with one role hint, resolved/inferred scope and no material ambiguity flags.

Suggested routes:

- critical → `dual_or_senior_review`
- high → `senior_review`
- medium → `standard_review`
- low → `light_review`

Every route remains review-only. No tier is publication authorization.

## F. What this does and does not prove

This routing layer alone does **not** prove sub-linear human review throughput. It creates the measurable control plane required to identify how much work is genuinely low/medium/high/critical before any safe reduction in review intensity is attempted.

Phase 2A should collect actual batch metrics first. Any future sampling or reduced-review policy must be separately governed and demonstrated not to weaken fact/publication safety.

## G. Next execution sequence

```text
1. implement generic review-risk routing contract
2. certify it cannot create/accept/publish facts
3. produce workload counts from representative review groups
4. select diverse multi-insurer Health batch
5. onboard batch as governed data only
6. measure tier distribution + review decisions + residue
7. decide whether a safe additional review-efficiency step is justified by evidence
```

## Acceptance guardrail

If any normal product in the Phase-2A batch requires a new `insurance_intelligence/.../<product>.py` reasoning implementation merely to onboard its ordinary mechanics, onboarding stops and the case is treated as a generic-model gap rather than normal product work.
