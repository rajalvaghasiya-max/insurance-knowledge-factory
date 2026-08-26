# PolicyScna Execution Ledger

Status: C5.5 prospective regulator-directory blind projection repair — CLOSED / FROZEN
Verified against: `784602b79d976873216f297ab296836e91cfa1ec`

This ledger defines the current authorized execution path. It exists to prevent scope drift, accidental rebuilding of existing capability, and architecture work that is not justified by observed evidence.

## Current phase

**Health repeatability — C5.5 is closed. The next neutral Health attempt requires a fresh Product #11 preregistration before any live root probing, insurer screening, product lookup or semantic inspection.**

Motor, Life and frontend work remain outside the current authorized phase.

## Immediate objective

Prepare and freeze the next neutral Health cold-start protocol using the repaired blind discovery harness. **Only Product #11 preregistration is authorized now.** No live root execution, insurer screening, product selection, target-mechanic inspection or Gate A/B/C execution is authorized until that preregistration merges with full CI green.

Frozen baselines:
- semantic scoring baseline: `f05ca07283f53f2882ed5da3ca27875ba7253318`
- prior Product #10 experiment-harness baseline: `edf344b34196258b04041f2fda2caa07d06d1f72`
- next-experiment prospective harness baseline after C5.5: `784602b79d976873216f297ab296836e91cfa1ec`

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

Later observations do not reopen, repair or reinterpret Product #9.

### C5.3A — Discovery classifier blindness-boundary proof
Status: **CLOSED**

Merge baseline:
- `2d3dd02ab92abcc8f3df9e3111cf90730874ffc1`

Closed outcome:
- direct positive/negative tests prove metadata/index classifications stay separated from product-detail/policy-wording destinations;
- semantic anchor text and semantic URL slugs do not promote product-detail destinations into the metadata class.

### C5.3B — Blind discovery-link projection
Status: **CLOSED**

Merge baseline:
- `addca46a88c104394a37bc6513c22e2556e3acf4`

Closed outcome:
- raw discovered URLs, anchor text, titles, body text, screenshots and semantic evidence remain machine-side;
- selector/operator receive opaque destination and record hashes plus governed metadata only.

### C5.3C — Root transport fitness gate
Status: **CLOSED / HARNESS BASELINE FROZEN**

Merge baseline:
- `edf344b34196258b04041f2fda2caa07d06d1f72`

Closed outcome:
- root transport is separate from insurer/product screening;
- allowed transport sequence is frozen to `static_http → playwright_headless → playwright_visible`;
- browser fallback is an explicit preregistered transport capability, not a silent upgrade.

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
- corrected disposable smoke commit `89bbc88e48f1839742a372f3c97141acbc2ffa42`, workflow run `32939927843`, job `98088633929`;
- corrected run captured 30 regulator pages and produced 7,620 generic blind `regulatory` projections, but resolved 0 / 4 preregistered insurer origins;
- full repository suite after corrected smoke: **3054 passed**;
- all raw URL/text/title/screenshot exposure counters remained zero;
- product screening did not start; Product #10 remained unselected; target-clause reads remained zero.

Attribution diagnostic:
- disposable machine-only diagnostic commit `89941b776d5d0f1b6e46b67467b50969a4e1a362`, workflow run `32940356432`, job `98089899312`;
- existing `SourceDiscoveryRunner.classify_source_url()` identified **36 `insurer_directory` links** across the two passing IRDAI roots, 18 per root;
- regulator-directory paths were therefore not absent;
- generic `DiscoveryAgent` regulator classification was too broad for the bounded routing use case;
- the frozen C5.3B blind projector did not authorize the already-existing `insurer_directory` class.

Gate B decision:
- **FAIL**;
- exact reason: `FROZEN_BLIND_PROJECTION_CONTRACT_EXCLUDES_EXISTING_INSURER_DIRECTORY_CLASS`;
- protocol outcome: `CLOSE_PRODUCT10_UNSCORED_BLIND_PATH_DISCOVERY_FAILURE`;
- Gate C never became authorized.

Immutable closure:
- `docs/architecture/health_product10_gate_b_blind_path_discovery_abort_2026-08-26.json`
- merge: `bc92794a31e670c0fa21706be49cfe8fe72c2aeb`
- canonical CI: **3060 passed in 10.12s**.

**Product #10 did not test semantic repeatability. Product #10 is immutable and may not be retried, repaired, rescored or advanced to Gate C.**

### C5.5 — Prospective regulator-directory blind projection repair
Status: **CLOSED / FROZEN**

Merge baseline:
- `784602b79d976873216f297ab296836e91cfa1ec`

Canonical CI:
- **3062 passed in 9.22s**

Evidence-earned implementation classification:
- **REUSE:** `SourceDiscoveryRunner`, including `classify_source_url`, IRDAI pagination/noise filtering, domain boundaries and its existing `insurer_directory` page type;
- **REUSE:** the existing `BlindDiscoveryLinkProjector` information-firewall design;
- **WIRE:** source-specific regulator classification → blind discovery projection;
- **SMALL EXTEND:** prospectively add `insurer_directory` to the blind projector's authorized metadata page types.

Closed outcomes:
- `insurer_directory` may now cross the blind boundary only as opaque/nonsemantic metadata;
- raw destination URL/path, semantic-bearing URL slug, anchor text, body excerpt, title and screenshot remain excluded;
- direct adversarial regression proves a semantic-laden insurer-directory URL and anchor project without semantic leakage;
- regulator-hosted product-detail content remains `regulatory_source_page` under `SourceDiscoveryRunner` and is rejected by the blind projector;
- policy-wording and product-detail rejection remains intact;
- no crawler, transport, new agent family or generic classifier rewrite was added;
- no live Product #10 rerun occurred and Product #10 remains immutable.

Authority rule for future neutral runs:

**Regulator-directory traversal must use the source-specific `SourceDiscoveryRunner` classification for `insurer_directory`; generic IRDAI-host `DiscoveryAgent` `regulatory` classification is not the authority for regulator-directory routing.**

`784602b79d976873216f297ab296836e91cfa1ec` is the prospective experiment-harness baseline for the next neutral Health preregistration.

## Next authorized work

### C5.6 — Product #11 neutral Health cold-start preregistration

Status: **PREREGISTRATION ONLY — NO LIVE EXECUTION OR SCREENING AUTHORIZED**

The Product #11 protocol must be merged with full CI green before Gate A or any live source access begins.

The preregistration must freeze:

1. **Baselines**
   - HC-1.5 semantic scoring baseline remains `f05ca07283f53f2882ed5da3ca27875ba7253318`;
   - prospective experiment-harness baseline is `784602b79d976873216f297ab296836e91cfa1ec`.

2. **Gate A — Root transport fitness**
   - exact regulator roots must be named before execution;
   - allowed transport sequence remains the frozen C5.3C order;
   - root fitness result must be recorded separately before Gate B begins.

3. **Gate B — Blind regulator-directory and metadata-path discovery**
   - machine-side raw capture/discovery is allowed;
   - source-specific `SourceDiscoveryRunner` is the regulator-directory classification authority;
   - `insurer_directory` may cross only through the blind projector as opaque metadata;
   - raw URLs, anchor/title/body text, screenshots and semantic evidence remain forbidden to selector/operator;
   - product-detail/policy-wording destinations remain prohibited;
   - Gate B must have a preregistered pass/fail condition independent of Gate C.

4. **Gate C — Neutral insurer/product selection**
   - begins only after Gate A and Gate B pass and are frozen;
   - deterministic candidate pool/order and prior-exposure rules must be frozen before screening;
   - selector consumes only governed blind projections;
   - semantic fit may not influence selection;
   - no manual selection override or post-selection product/version substitution.

5. **Post-selection evidence gate**
   - exact product/UIN/version identity;
   - exact retained source bytes and SHA lineage;
   - reviewed currentness/identity resolution;
   - v4.2 current-product evidence eligibility;
   - target-clause semantic inspection only after those gates pass.

Product #11 remains **unselected** until the protocol itself authorizes Gate C after successful Gate A/B execution.

Motor gate remains **CLOSED**.

## Known defects / risks currently tracked

1. Generic `DiscoveryAgent` regulator classification remains too broad for IRDAI-internal directory routing; future regulator-directory traversal must use the source-specific `SourceDiscoveryRunner` authority.
2. Live regulator/insurer site structures and transport behavior can change; each experiment must record its own root fitness and cannot reuse a historical live observation as proof of current reachability.
3. Blind projection authorization of `insurer_directory` is now covered prospectively, but unknown/new page types must continue to fail closed.
4. Legacy certifiers emit `EvidencePackage.version_status="CURRENT_APPLICABLE"`; this remains non-authoritative metadata pending a versioned evidence-contract migration.
5. Generic copay shadow migration remains non-authoritative.
6. Product #7, Product #8, Product #9 and Product #10 are immutable unscored experiment closures and must not be repaired retroactively.

## Explicitly not authorized now

- Product #10 Gate B retry or Gate C
- Product #10 insurer/product screening or selection
- Product #11 Gate A/B/C execution before Product #11 preregistration merges green
- Product #11 insurer/product screening or selection before Gate A and Gate B pass under the frozen protocol
- live root probing while drafting Product #11 preregistration
- search-engine candidate screening or fallback unless a future preregistration explicitly and safely changes that rule before execution
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
