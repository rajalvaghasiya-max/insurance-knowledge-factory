# AR-3.0.G0 — Star Comprehensive Commercial Pressure Qualification

## Status

**QUALIFICATION PROPOSED — requires focused local certification before closure.**

Audit / implementation ref:

`feature/mo-028b-health-waiting-period-coverage`

## Objective

Use a real commercial Health product to pressure the certified PolicyScna architecture after AR-2.4 certified the knowledge-consumption boundary and AR-2.5 certified repository succession/cleanup.

The purpose is not to add another product-specific reasoning path. The purpose is to determine whether the current shared governed architecture survives materially richer product semantics than the standardized Arogya Sanjeevani pressure case.

## Qualified product

- Insurer: `star_health`
- Product: `star_comprehensive`
- Product name: Star Comprehensive Insurance Policy
- Product reference: `star_health:star_comprehensive`

## Why this product qualifies

Star Comprehensive already has two independent governed/current anchors inside the authoritative architecture:

1. **Conditional copayment** — a reviewed generic legal-condition chain with source registration, document identity/classification, legal binding, canonical projection, publication decision, and authoritative publication. The current `StarKnowledgeBuildResult` certifies this chain and explicitly limits the snapshot to the conditional co-payment topic.
2. **Automatic restoration** — an approved and published `ProductBenefitImplementation` with dense mechanics: percentage, count, exhaustion trigger, trigger timing, same-hospitalization restriction, subsequent-hospitalization use, same-illness use, covered-section scope, relapse window, policy-year reset, non-carry-over, and floater behavior.

These pressure different architecture concerns: conditional rules and multi-dimensional benefit mechanics.

## Explicitly excluded as current truth

`knowledge/health/coverage_audits/star_health_star_comprehensive_coverage_audit.json` is a historical/transitional coverage artifact and must not be used as a current governed coverage statement. It reports an old `INCOMPLETE` state that predates later governed source-registration/publication work.

No AR-3.0 implementation may infer missing waiting-period, limit, or applicability facts from that artifact.

## G0 pressure units

### P1 — Conditional copayment

Existing governed chain must preserve:

- percentage financial effect;
- age-at-entry trigger;
- continuous-renewal exception;
- explicit policy-section scope;
- evidence lineage;
- publication state.

### P2 — Automatic restoration

Existing governed benefit implementation must preserve at minimum:

- `restoration_percentage`;
- `restoration_count_per_policy_period`;
- `trigger_requirement`;
- `trigger_timing`;
- `same_hospitalization_use`;
- `subsequent_hospitalization_use`;
- `same_illness_use`;
- `covered_section_scope`;
- `relapse_window_days`;
- `policy_year_reset`;
- `carry_over_between_policy_years`;
- `floater_operation`.

The pressure gate must not flatten those mechanics into a single scalar or generic “restoration available” flag.

## Next-stage evidence rule

Waiting-period and benefit-limit propositions may be added to AR-3.0 only after exact evidence inventory and reviewed proposition binding. Existing historical extraction JSON, old comparison artifacts, webpages, or general product knowledge cannot be promoted directly into certified generic knowledge.

The required progression is:

`real source/evidence -> atomic normative unit -> reviewed proposition -> generic semantic family -> applicability/relationships -> residue/accounting -> comparison readiness -> governed consumption`

## Architecture invariants under pressure

1. Product identity remains data, never reasoning logic.
2. Star-specific facts may enter governed data/evidence/applicability but no Star-specific semantic branch may be added to generic runtime code.
3. `MAPPED` must not imply comparison-ready.
4. Unknown or unresolved scope/ordering/applicability must fail closed.
5. Cross-family interactions must remain explicit rather than being collapsed into independent feature scores.
6. Historical/transitional outputs remain non-authoritative.
7. No product winner, rank, or recommendation is produced by the pressure gate.

## G0 exit criteria

G0 may be certified only when focused tests prove:

- the conditional-copayment governed snapshot chain is currently certifiable from repository artifacts;
- the restoration implementation is approved/published and retains all listed mechanics;
- the pressure qualification explicitly rejects the stale historical coverage audit as current truth;
- no new product-specific reasoning implementation is introduced.

## Planned AR-3.0 sequence

- **G0** — Commercial-product qualification and governed-anchor verification.
- **G1** — Real source/evidence inventory for additional waiting-period and limit propositions.
- **G2** — Atomic normative-unit and residue pressure mapping.
- **G3** — Generic-family mapping without product-specific semantic logic.
- **G4** — Cross-family interaction and comparison-readiness pressure.
- **G5** — End-to-end education/decision-support pressure with unresolved-state preservation.

A new abstraction is permitted only if a real G1–G4 pressure unit proves the current architecture cannot represent the fact safely.