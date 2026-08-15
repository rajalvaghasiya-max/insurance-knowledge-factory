# AR-3.0.G0 — Star Comprehensive Commercial Pressure Qualification

## Status

**CERTIFIED — 2026-08-15**

Audit / implementation ref:

`feature/mo-028b-health-waiting-period-coverage`

Certification evidence:

- G0 focused: `3 passed`
- Star combined anchors: `49 passed`
- `tests/insurance_intelligence`: `2839 passed`
- regressions: `0`

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

1. **Conditional copayment** — the current rule-certification path consumes the reviewed Star Comprehensive conditional-copayment binding, routes the reviewed statement through production conditional-obligation extraction, preserves the obligation value, age-at-entry trigger, continuous-renewal exception, applicability scope and calculation basis, and passes the product-specific completeness profile. AR-3.0.G0 deliberately certifies this current rule path rather than requiring historical/generated orchestration outputs to be committed in the repository.
2. **Automatic restoration** — an approved and published `ProductBenefitImplementation` with dense mechanics: percentage, count, exhaustion trigger, trigger timing, same-hospitalization restriction, subsequent-hospitalization use, same-illness use, covered-section scope, relapse window, policy-year reset, non-carry-over, and floater behavior.

These pressure different architecture concerns: conditional rules and multi-dimensional benefit mechanics.

## DEFECT-01 closure — certification anchor/runtime-output boundary

The first G0 focused run failed because the proposed test invoked `build_star_comprehensive_copay_snapshot(repository_root=Path("."))`. That older snapshot pilot expects a materialized document-identity overlay, while the Star migration manifest correctly defines that overlay as a generated governed migration output rather than a committed repository source artifact.

The failure therefore exposed a test-fixture/certification-anchor defect, not a Star semantic defect and not a production architecture defect.

Disposition:

- no generated identity-resolution artifact was committed;
- no fail-closed behavior was weakened;
- no generic governance contract was changed;
- no production orchestration was changed;
- G0 was corrected to exercise the current certified conditional-copayment rule path directly.

DEFECT-01 is **CLOSED** by the green certification results above.

## Explicitly excluded as current truth

`knowledge/health/coverage_audits/star_health_star_comprehensive_coverage_audit.json` is a historical/transitional coverage artifact and must not be used as a current governed coverage statement. It reports an old `INCOMPLETE` state that predates later governed source-registration/publication work.

No AR-3.0 implementation may infer missing waiting-period, limit, or applicability facts from that artifact.

Historical extraction/intelligence artifacts may be used in G1 only as search/index hints for locating candidate source text. They are not evidence authority and cannot be promoted merely because they contain a value or a `validated` flag from the transitional pipeline.

## G0 pressure units

### P1 — Conditional copayment

Existing governed certification must preserve:

- percentage financial effect;
- age-at-entry trigger;
- continuous-renewal exception;
- explicit policy-section scope;
- evidence lineage;
- certification/completeness boundary.

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

## G0 exit criteria — certified

G0 is certified because focused and subsystem tests prove:

- the current Star Comprehensive conditional-copayment rule-certification path passes through governed evidence, production semantic extraction and the product-specific completeness profile;
- the restoration implementation is approved/published and retains all listed mechanics;
- the pressure qualification explicitly rejects the stale historical coverage audit as current truth;
- no new product-specific reasoning implementation was introduced;
- the generated-runtime-output versus committed-repository-source boundary remains intact.

## Planned AR-3.0 sequence

- **G0** — Commercial-product qualification and governed-anchor verification. **CERTIFIED.**
- **G1** — Real source/evidence inventory for additional waiting-period and limit propositions. **ACTIVE.**
- **G2** — Atomic normative-unit and residue pressure mapping.
- **G3** — Generic-family mapping without product-specific semantic logic.
- **G4** — Cross-family interaction and comparison-readiness pressure.
- **G5** — End-to-end education/decision-support pressure with unresolved-state preservation.

A new abstraction is permitted only if a real G1–G4 pressure unit proves the current architecture cannot represent the fact safely.
