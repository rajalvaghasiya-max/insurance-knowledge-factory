# PolicyScna Execution Ledger

Status: C5.4 Product #10 three-gate cold start — CLOSED / UNSCORED AT GATE B
Verified against: `ba637b84704105f0de6d04dabaa2e324f3f68f01` plus frozen Gate B abort `docs/architecture/health_product10_gate_b_blind_path_discovery_abort_2026-08-26.json`

This ledger defines the current authorized execution path. It exists to prevent scope drift, accidental rebuilding of existing capability, and architecture work that is not justified by observed evidence.

## Current phase

**Health repeatability — Product #10 is immutably closed unscored at Gate B. No new cold-start product experiment is authorized.**

Motor, Life and frontend work remain outside the current authorized phase.

## Immediate objective

Perform a bounded **REUSE/WIRE archaeology of regulator-root → insurer-origin identity routing** before considering another neutral Health preregistration. Product #10 must not be reopened, retried or repaired. The review may inspect existing repository capabilities and historical experiment evidence, but it may not run a new product selection experiment or alter Product #10's result.

Frozen baselines remain:
- semantic scoring baseline: `f05ca07283f53f2882ed5da3ca27875ba7253318`
- experiment-harness baseline: `edf344b34196258b04041f2fda2caa07d06d1f72`

## Authorized work sequence

### C1 — Capability registry / architecture map / execution ledger

Status: **CLOSED**

### C2 — Restore acquisition foundation

Status: **CLOSED**

### C3 — Reconnect acquisition to currentness governance

Status: **CLOSED / REVIEWED / FROZEN**

### C4 — Current-product repeatability evidence eligibility

Status: **CLOSED**

### C5 — Product #8 neutral cold-start

Status: **CLOSED / UNSCORED BEFORE SELECTION**

Protocol:
- `docs/architecture/health_post_hc1_neutral_cold_start_protocol_v5_product8.json`

Closure:
- `docs/architecture/health_product8_selection_abort_2026-08-25.json`

Finding:
- broad/exact-UIN search screening was too contamination-prone;
- no semantic repeatability result was produced;
- Product #8 does not authorize Motor.

### C5.1 — Blind direct-source preselection method

Status: **CLOSED**

Merge baseline:
- `d7dc909696670f77d0db565fc8855820775e53f2`

Closed outcomes:
- `BlindPreselectionMetadataProjector` exposes identity/UIN/source metadata only;
- semantic content cannot reach or influence the selector through this boundary.

### C5.2 — Product #9 blind direct-source cold-start

Status: **CLOSED / UNSCORED BEFORE SELECTION**

Protocol:
- `docs/architecture/health_post_hc1_neutral_cold_start_protocol_v6_product9.json`

Closure:
- `docs/architecture/health_product9_preselection_abort_2026-08-26.json`

Observed result:
- Product #9 remained unselected and unscored;
- the then-observed IRDAI root access returned 403 with no search fallback;
- Bima Bharosa exposed bare insurer origins under the then-active pre-render operator guardrail;
- zero insurer origins rendered, zero product documents opened, zero target-clause reads and zero search fallbacks occurred.

**No Product #9 candidate screening is authorized now or in any future run. Product #9 is an immutable closed experiment.**

Later Product #10 transport observations do not reopen, repair or reinterpret Product #9.

### C5.3A — Discovery classifier blindness-boundary proof

Status: **CLOSED**

Merge baseline:
- `2d3dd02ab92abcc8f3df9e3111cf90730874ffc1`

### C5.3B — Blind discovery-link projection

Status: **CLOSED**

Merge baseline:
- `addca46a88c104394a37bc6513c22e2556e3acf4`

### C5.3C — Root transport fitness gate

Status: **CLOSED / HARNESS BASELINE FROZEN**

Merge baseline:
- `edf344b34196258b04041f2fda2caa07d06d1f72`

### C5.4 — Product #10 three-gate blind cold-start

Status: **CLOSED / EXPERIMENT_UNSCORED AT GATE B**

Protocol:
- `docs/architecture/health_post_hc1_neutral_cold_start_protocol_v7_product10.json`

Preregistration merge:
- `8d6f0c763333f75ecd5edab2181db23a41783a99`

Gate A result:
- `docs/architecture/health_product10_gate_a_root_transport_fitness_2026-08-26.json`
- merge: `ba637b84704105f0de6d04dabaa2e324f3f68f01`
- result: **PASS**
- IRDAI non-life root → `DIRECT_HTTP_AVAILABLE`;
- IRDAI Health root → `DIRECT_HTTP_AVAILABLE`;
- Bima Bharosa root → `ALL_ALLOWED_TRANSPORTS_FAILED`;
- search fallbacks and ad-hoc transports remained zero.

Gate B closure:
- `docs/architecture/health_product10_gate_b_blind_path_discovery_abort_2026-08-26.json`
- passing IRDAI roots were machine-captured successfully;
- preregistered candidate insurer identities: Chola, Magma, Navi, Shriram;
- eligible insurer origins resolved from those passing root captures: **0 / 4**;
- insurer-origin machine captures: **0**;
- authorized `blind_discovery_link_metadata_v1` projections: **0**;
- raw origin/discovered URLs crossing blindness boundary: **0**;
- anchor/body/title/screenshot exposure: **0**;
- product screening: not started;
- Product #10 selected: false;
- target-clause reads: 0;
- Gate B decision: **FAIL**;
- protocol outcome: `CLOSE_PRODUCT10_UNSCORED_BLIND_PATH_DISCOVERY_FAILURE`;
- Gate C never became authorized.

Execution lineage:
- disposable non-merged branch: `product10-gate-b-live-smoke`;
- smoke commit: `d3814624f757e727c13ec50da643b7d1bddae050`;
- workflow run: `32938825521`;
- workflow job: `98085376730`;
- smoke suite: `3054 passed`;
- smoke branch is not merge-authorized.

Interpretation:

**Product #10 did not test semantic repeatability.** It falsified the locked v7 assumption that the passing regulator-root captures could yield at least one preregistered eligible insurer origin and then an authorized blind metadata destination through the frozen discovery method. This is a path/identity-routing method failure, not a semantic `REPRESENTATION_GAP` or `KNOWLEDGE_GAP`.

**Product #10 is immutable. No alternate parser, forced-browser retry, search fallback, hostname guess, product substitution, Gate C execution or semantic inspection may be used to repair it.**

## Next authorized work

### C5.5 — Regulator-root to insurer-origin routing archaeology

Status: **REUSE/WIRE REVIEW ONLY — NO NEW PRODUCT EXPERIMENT**

Objective:
- determine whether an existing repository capability can deterministically derive regulator-listed insurer identity/origin records from captured regulator pages without exposing semantic-bearing raw content to selector/operator;
- distinguish an existing disconnected capability from a genuine missing capability;
- inspect discovery, preservation, source registry, insurer registry, identity-resolution, sitemap/link and structured-page parsing code before authorizing any extension.

Allowed:
- repository archaeology;
- deterministic offline fixtures/tests against already-known synthetic or retained non-target examples;
- capability classification as `REUSE`, `WIRE`, `REPAIR`, or evidence-earned small `EXTEND`;
- documentation of the exact observed Product #10 gap.

Not allowed:
- Product #11 preregistration or screening;
- live candidate/product exploration;
- retroactive Product #10 retry;
- broad search-engine fallback;
- new crawler/agent family before archaeology proves existing capabilities insufficient.

Motor gate remains **CLOSED**.

## Known defects / risks currently tracked

1. Passing regulator root transport does not by itself prove the captured representation exposes insurer-origin identity links consumable by the current routing method.
2. Root transport capability can change over time; historical observations remain experiment-specific.
3. Discovery classification is proven for C5.3 boundary cases, but regulator-directory identity extraction/routing is not yet proven.
4. Legacy certifiers emit `EvidencePackage.version_status="CURRENT_APPLICABLE"`; this remains non-authoritative metadata pending a versioned evidence-contract migration.
5. Generic copay shadow migration remains non-authoritative.
6. Product #7, Product #8, Product #9 and Product #10 are immutable unscored experiment closures and must not be repaired retroactively.

## Explicitly not authorized now

- Product #10 Gate B retry or Gate C
- Product #10 insurer/product screening or selection
- Product #11 preregistration or screening
- alternate post-result parsing/traversal to rescue Product #10
- search-engine candidate screening or fallback
- merging disposable `product10-gate-a-live-smoke` or `product10-gate-b-live-smoke` branches
- reopening, retrying, repairing, rescoring or reselecting Product #7, Product #8, Product #9 or Product #10
- Motor implementation or expansion
- Life implementation or investment-comparison logic
- frontend / consumer app / advisor UI
- recommendation-engine expansion
- claims application
- quote-comparison UX
- database migration for scale
- broad ingestion scale-up
- new agent families without evidence-earned authorization
- generic copay shadow authority switch
- architecture redesign without an observed falsification
- vocabulary expansion merely to increase concept count

## Pre-build decision rule

Every material PR must first classify its work against the Capability Registry:

`REUSE` → use existing capability unchanged.

`WIRE` → connect existing capabilities without duplicating semantics.

`REPAIR` → restore a broken existing capability while preserving its contract.

`EXTEND` → add evidence-earned capability only after recording the observed gap.

`REPLACE` → allowed only with explicit proof that the existing path is unsafe or irreparable.

`NEW` → allowed only after repository search confirms no suitable implementation/contract exists.

If a PR cannot map to an authorized ledger item, stop and review before implementation.

## Project memory rule

**GitHub is the authoritative project memory.** Chat threads, external AI reviews and local-only files are supporting evidence, not the source of truth for current architecture or capability status.

External reviews may challenge this ledger, but changes must be reconciled against tracked code/tests/artifacts before the ledger is updated.
