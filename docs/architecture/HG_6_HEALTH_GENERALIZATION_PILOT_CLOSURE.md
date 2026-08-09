# HG-6 — Health Generalization Pilot Closure

## Status

**CLOSED**

Certified branch: `feature/health-generalization-pilot`

Final full-repository regression result: **2392 passed**.

## Objective

Prove that the governed PolicyScna architecture generalizes beyond the original Star Health Star Comprehensive conditional co-payment pilot to a second insurer/product and a materially different insurance-rule family, without introducing product-specific hacks or importing the later MO-025 comparison/ranking stack.

## Certified pilots

### Pilot A — Star Health Star Comprehensive conditional co-payment

Semantic family: cost-sharing obligation.

Key governed semantics:
- percentage obligation;
- trigger;
- exception;
- applicability scope;
- case-specific clarification when trigger status is unresolved;
- deterministic evidence-preserving explanation.

### Pilot B — Aditya Birla Health Activ One NXT Super Reload

Semantic family: restoration / coverage-capacity benefit.

Governed product identity:
- entity ID: `aditya_birla_health:activ_one`;
- canonical product name: `Activ One`;
- UIN: `ADIHLIP24097V012324`.

Key governed restoration semantics:
- restoration amount;
- restoration frequency;
- exhaustion/insufficiency trigger;
- same-hospitalization use;
- first-claim and subsequent-claim use;
- partial restoration use where governed evidence supports it;
- maximum liability per claim;
- covered-section scope;
- utilization sequence;
- policy-year reset;
- floater operation.

Authoritative source identities verified during HG-2:
- policy wording SHA-256: `d7726811cfdf2c3c31c3750eb0bd4a55203b20cf79d44fc6849dbc77ba556451`;
- prospectus SHA-256: `8923d6457d368c9d80d097032a7b784c65b30ba07ae68ea7474af7569332fa56`.

Bounded evidence locations:
- policy wording: Activ One NXT, Section C.8 Super Reload, page 30; Annexure III Product Benefit Table, page 46;
- prospectus: Section C.10 Super Reload, page 3; Super Reload Illustration (NXT Plan), page 10.

## HG stages completed

### HG-1 — Pilot selection

Selected Activ One NXT Super Reload because it provides a second insurer/product and a materially different semantic rule family from conditional co-payment.

### HG-2 — Product identity and evidence audit

Closed with:
- explicit human approval of the governed product identity;
- a `product_identity_reference_v1` runtime source;
- focused identity certification;
- byte-level verification of the policy wording and prospectus against previously identified governed source hashes;
- explicit separation of authoritative source evidence from historical intelligence outputs.

Focused identity gate: **32 passed**.

### HG-3 — Restoration semantic contract

Confirmed the current architecture already contained an appropriate product-neutral restoration concept and generic typed benefit contracts. No new contract framework was introduced.

Certified:
- terminology routing to the restoration topic;
- product-neutral canonical restoration concept;
- mechanic vocabulary required by the Activ One pilot;
- absence of comparison, ranking, recommendation, suitability, entitlement, and claim-outcome semantics from the canonical concept.

Focused gate: **23 passed**.

### HG-4 — Evidence to typed finding

Certified the chain:

`approved product identity -> byte-verified source evidence -> bounded Super Reload evidence -> typed ProductBenefitImplementation`

Also certified fail-closed treatment of unsupported semantics rather than invented mechanic values.

Focused gate: **31 passed**.

### HG-5 — End-to-end restoration explanation

Certified that the existing generic explanation stack can render a restoration `COVERAGE_EFFECT` finding while preserving:
- approved effect and trigger;
- evidence lineage;
- limitation identity and limitation status;
- no recommendation semantics;
- no claim-payment guarantee.

The renderer intentionally preserves governed limitation IDs and emits a limitation notice rather than silently copying limitation prose that was not separately approved for rendering.

Focused gate: **35 passed**.

### HG-6 — Cross-pilot generalization certification

Certified that the Star conditional co-payment pilot and Activ One restoration pilot coexist under shared architecture while preserving materially different semantics.

Cross-pilot invariants include:
- separate canonical topics;
- shared generic reasoning contracts;
- distinct finding/rule semantics;
- independent product evidence lineage;
- generic explanation capability;
- no cross-product semantic leakage;
- no comparison, ranking, recommendation, or suitability behavior introduced by this milestone.

Focused cross-pilot gate: **61 passed**.

## Final regression gate

Full repository:

`2392 passed`

This is the authoritative regression baseline for closure of the Health generalization pilot.

## Generalization conclusion

The milestone proves that the governed architecture is no longer supported only by one Star conditional co-payment example. It supports at least two materially different Health insurance semantic families across different insurers/products through the same architectural boundaries:

1. human language / canonical terminology;
2. governed product identity;
3. governed source and evidence identity;
4. product-specific typed semantics;
5. generic reasoning finding contract;
6. decision / safety boundary;
7. evidence-preserving deterministic explanation.

The proof was achieved without introducing a generic agent framework, vector or graph database dependency, comparison/ranking machinery, recommendation behavior, or a second product-specific explanation framework.

## Deferred defect retained

`CD-1` remains open and explicitly deferred:

`unless / except` style legal exceptions may be merged into trigger semantics rather than failing closed in some broader rule-family parsing paths.

Classification for this closure:
- it does not invalidate the two certified pilot paths above;
- it remains a blocker before broader rule-family certification where such exception language is in scope;
- it must not be forgotten or silently treated as resolved by this milestone.

## Closure decision

**Multi-product / Multi-rule Health Generalization Pilot: CLOSED.**

Next roadmap milestone may proceed from this certified baseline. The next planned capability is MO-025 Product-Benefit Discovery and Comparison, but later repository history must remain reference material only until intentionally reconciled with this certified branch baseline.
