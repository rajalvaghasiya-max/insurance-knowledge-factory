# PolicyScna Execution Ledger

Status: C5.4 Product #10 three-gate cold start — CLOSED / UNSCORED AT GATE B
Verified against: `ba637b84704105f0de6d04dabaa2e324f3f68f01` plus frozen Gate B abort `docs/architecture/health_product10_gate_b_blind_path_discovery_abort_2026-08-26.json`

This ledger defines the current authorized execution path. It exists to prevent scope drift, accidental rebuilding of existing capability, and architecture work that is not justified by observed evidence.

## Current phase

**Health repeatability — Product #10 is immutably closed unscored at Gate B. No new cold-start product experiment is authorized.**

Motor, Life and frontend work remain outside the current authorized phase.

## Immediate objective

Perform a bounded C5.5 repair of the observed Gate B harness mismatch **prospectively only**. Existing `SourceDiscoveryRunner` already provides the precise `insurer_directory` classification needed at the regulator layer, while the frozen C5.3B `BlindDiscoveryLinkProjector` does not authorize that class. Product #10 must not be reopened, retried or repaired.

Frozen baselines remain:
- semantic scoring baseline: `f05ca07283f53f2882ed5da3ca27875ba7253318`
- Product #10 experiment-harness baseline: `edf344b34196258b04041f2fda2caa07d06d1f72`

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

Closed outcome:
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

Gate B corrected evidence:
- first disposable smoke `d3814624...` is retained as historical lineage but is not authoritative because its runner assumed candidate insurer origins had to be direct external links on the root page;
- corrected disposable smoke commit `89bbc88e48f1839742a372f3c97141acbc2ffa42`, workflow run `32939927843`, job `98088633929`;
- corrected run captured 30 regulator pages and produced 7,620 generic blind `regulatory` projections, but resolved 0 / 4 preregistered insurer origins;
- full repository suite after corrected smoke: **3054 passed**;
- all raw URL/text/title/screenshot exposure counters remained zero;
- product screening did not start; Product #10 remained unselected; target-clause reads remained zero.

Attribution diagnostic:
- disposable machine-only diagnostic commit `89941b776d5d0f1b6e46b67467b50969a4e1a362`, workflow run `32940356432`, job `98089899312`;
- existing `SourceDiscoveryRunner.classify_source_url()` identified **36 `insurer_directory` links** across the two passing IRDAI roots, 18 per root;
- therefore regulator-directory paths are **not absent**;
- generic `DiscoveryAgent` regulator classification is too broad for this bounded routing use case because IRDAI-host links collapse into the generic `regulatory` class;
- frozen C5.3B `BlindDiscoveryLinkProjector` does **not** authorize the existing `insurer_directory` class.

Gate B decision:
- **FAIL**;
- exact reason: `FROZEN_BLIND_PROJECTION_CONTRACT_EXCLUDES_EXISTING_INSURER_DIRECTORY_CLASS`;
- protocol outcome remains `CLOSE_PRODUCT10_UNSCORED_BLIND_PATH_DISCOVERY_FAILURE`;
- Gate C never became authorized.

Interpretation:

**Product #10 did not test semantic repeatability.** Root transport passed and precise regulator-directory classification already exists in the repository. The falsified assumption is narrower: the frozen Gate B harness could not carry the existing `insurer_directory` classification across the blind projection boundary. This is a harness contract mismatch, not a semantic `REPRESENTATION_GAP`, `KNOWLEDGE_GAP`, or proof that directory paths are absent.

**Product #10 is immutable. Adding `insurer_directory` to the blind projector now would change the frozen harness after the experiment began and is therefore prohibited as a Product #10 repair.**

## Next authorized work

### C5.5 — Prospective regulator-directory blind projection repair

Status: **REUSE + SMALL EXTEND ONLY — NO NEW PRODUCT EXPERIMENT**

Evidence-earned classification:
- **REUSE:** `SourceDiscoveryRunner`, including `classify_source_url`, IRDAI pagination/noise filtering, domain boundaries and `insurer_directory` classification;
- **REUSE:** existing `BlindDiscoveryLinkProjector` information-firewall pattern;
- **SMALL EXTEND:** prospectively authorize an opaque blind representation of the already-existing `insurer_directory` page type, with adversarial leakage tests;
- **WIRE:** regulator source-specific classification → blind discovery projection.

Required before any future Product #11 preregistration:
- direct contract tests that `insurer_directory` can cross only as opaque/nonsemantic metadata;
- raw URL, anchor text, title/body text and screenshots remain prohibited across the selector/operator boundary;
- product-detail/policy-wording types remain rejected;
- source-specific `insurer_directory` classification, not generic IRDAI-host `regulatory`, is the authority for regulator-directory traversal;
- deterministic offline integration proof of SourceDiscoveryRunner classification → blind projection;
- full CI green and ledger freeze.

Not allowed:
- Product #10 Gate B retry or Gate C;
- Product #11 preregistration or screening before C5.5 closes;
- live candidate/product exploration;
- broad search-engine fallback;
- new crawler/agent family;
- broad rewrite of discovery architecture.

Motor gate remains **CLOSED**.

## Known defects / risks currently tracked

1. Generic `DiscoveryAgent` regulator classification is too broad for IRDAI-internal routing because host text can dominate the `regulatory` classification.
2. `BlindDiscoveryLinkProjector` currently omits the existing source-specific `insurer_directory` page type; this is the exact C5.5 evidence-earned extension.
3. Root transport capability can change over time; historical observations remain experiment-specific.
4. Legacy certifiers emit `EvidencePackage.version_status="CURRENT_APPLICABLE"`; this remains non-authoritative metadata pending a versioned evidence-contract migration.
5. Generic copay shadow migration remains non-authoritative.
6. Product #7, Product #8, Product #9 and Product #10 are immutable unscored experiment closures and must not be repaired retroactively.

## Explicitly not authorized now

- Product #10 Gate B retry or Gate C
- Product #10 insurer/product screening or selection
- Product #11 preregistration or screening
- extending the projector and then re-running Product #10
- alternate post-result parsing/traversal to rescue Product #10
- search-engine candidate screening or fallback
- merging disposable Product #10 smoke/diagnostic branches
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
