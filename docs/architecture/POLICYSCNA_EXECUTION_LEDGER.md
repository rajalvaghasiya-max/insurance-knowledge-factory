# PolicyScna Execution Ledger

Status: C5.4 Product #10 three-gate cold start — Gate A CLOSED / PASS; Gate B authorized
Verified against: `b173dafe76ea95f1028ababb5b1f4aeb008d7493` plus frozen Gate A result `docs/architecture/health_product10_gate_a_root_transport_fitness_2026-08-26.json`

This ledger defines the current authorized execution path. It exists to prevent scope drift, accidental rebuilding of existing capability, and architecture work that is not justified by observed evidence.

## Current phase

**Health repeatability — Product #10 Gate A is closed PASS; Gate B blind metadata-path discovery fitness is the only authorized live experiment step.**

Motor, Life and frontend work remain outside the current authorized phase.

## Immediate objective

Execute Product #10 **Gate B only** using the passing preregistered regulator roots and the frozen C5.3 machine-only capture/discovery path. Selector/operator exposure remains limited to `blind_discovery_link_metadata_v1`. Do not begin Gate C insurer/product screening until Gate B passes and its outcome is frozen.

Authoritative Product #10 protocol:
- `docs/architecture/health_post_hc1_neutral_cold_start_protocol_v7_product10.json`

Frozen Gate A result:
- `docs/architecture/health_product10_gate_a_root_transport_fitness_2026-08-26.json`

Frozen baselines:
- semantic scoring baseline: `f05ca07283f53f2882ed5da3ca27875ba7253318`
- experiment-harness baseline: `edf344b34196258b04041f2fda2caa07d06d1f72`
- Product #10 preregistration merge: `8d6f0c763333f75ecd5edab2181db23a41783a99`
- Gate A authorization merge: `b173dafe76ea95f1028ababb5b1f4aeb008d7493`

## Authorized work sequence

### C1 — Capability registry / architecture map / execution ledger

Status: **CLOSED**

Authoritative artifacts:
- `docs/architecture/POLICYSCNA_CAPABILITY_REGISTRY.md`
- `docs/architecture/POLICYSCNA_ARCHITECTURE_MAP.md`
- `docs/architecture/POLICYSCNA_EXECUTION_LEDGER.md`

### C2 — Restore acquisition foundation

Status: **CLOSED**

Closed outcomes:
- governed source-asset classification restored;
- existing acquisition and `ProductSignalExtractor` clean-checkout execution restored;
- PDF validation / SHA / immutable-storage boundary covered;
- browser-assisted protected-PDF transport remains behind the same validation boundary;
- document-role classification hardened;
- deterministic offline acquisition fitness covers preservation → sections → product signals/UIN → PDF discovery.

### C3 — Reconnect acquisition to currentness governance

Status: **CLOSED / REVIEWED / FROZEN**

Closed outcomes:
- acquisition observations bridge into `SourceObservationRecord`;
- exact bytes and source-page artifacts are hash-bound before governance handoff;
- changed bytes cannot become positive currentness evidence;
- temporal/currentness authority remains in `DocumentIdentityResolutionOverlay`.

### C4 — Current-product repeatability evidence eligibility

Status: **CLOSED**

Closed outcomes:
- Product #7 remains immutable `CURRENTNESS_SELECTION_INVALIDATED / UNSCORED`;
- `CurrentProductRepeatabilityEvidenceEligibility` requires exact entity, document version, SHA-256, document role, resolved identity, evidence-review eligibility, `current_observed_reviewed`, and current-entitlement eligibility;
- semantic certification can remain valid for historical/replaced documents without proving present-tense applicability;
- legacy certifier `EvidencePackage.version_status="CURRENT_APPLICABLE"` is non-authoritative for temporal currentness;
- v4.2 is frozen.

### C5 — Product #8 neutral cold-start

Status: **CLOSED / UNSCORED BEFORE SELECTION**

Protocol:
- `docs/architecture/health_post_hc1_neutral_cold_start_protocol_v5_product8.json`

Closure:
- `docs/architecture/health_product8_selection_abort_2026-08-25.json`

Observed result:
- no Product #8 selected;
- Product #8 closed `SELECTION_UNIVERSE_EXHAUSTED_NO_ELIGIBLE_UNCONTAMINATED_CURRENTNESS_CORROBORATED_PRODUCT / UNSCORED`;
- broad/exact-UIN search screening was found too contamination-prone;
- Product #8 does not prove or falsify semantic repeatability and does not authorize Motor.

### C5.1 — Blind direct-source preselection method

Status: **CLOSED**

Merge baseline:
- `d7dc909696670f77d0db565fc8855820775e53f2`

Closed outcomes:
- existing acquisition / product-signal capabilities reused;
- `BlindPreselectionMetadataProjector` exposes only identity/UIN/source metadata;
- semantic content cannot influence the selector through the projection;
- broad search-result screening remains prohibited for locked runs unless prospectively preregistered otherwise.

### C5.2 — Product #9 blind direct-source cold-start

Status: **CLOSED / UNSCORED BEFORE SELECTION**

Protocol:
- `docs/architecture/health_post_hc1_neutral_cold_start_protocol_v6_product9.json`

Closure:
- `docs/architecture/health_product9_preselection_abort_2026-08-26.json`

Observed result:
- Product #9 remained unselected and unscored;
- the then-observed IRDAI root access returned 403 and no search fallback was used;
- Bima Bharosa exposed only bare insurer origins under the then-active pre-render operator guardrail;
- zero insurer origins rendered, zero product documents opened, zero target-clause reads and zero search fallbacks occurred;
- Product #9 closed `EXPERIMENT_UNSCORED / PRE_RENDER_METADATA_PATH_UNAVAILABLE_FOR_ALL_PREREGISTERED_RETRY_INSURERS`.

**No Product #9 candidate screening is authorized now or in any future run. Product #9 is an immutable closed experiment.**

Later Product #10 transport observations do not reopen, repair or reinterpret Product #9.

### C5.3A — Discovery classifier blindness-boundary proof

Status: **CLOSED**

Merge baseline:
- `2d3dd02ab92abcc8f3df9e3111cf90730874ffc1`

Closed outcomes:
- existing `DiscoveryAgent` reused unchanged;
- positive metadata/index and negative product-detail cases are directly regression-covered;
- semantic anchor text and semantic URL slugs do not promote product-detail destinations into the metadata-class set.

### C5.3B — Blind discovery-link projection

Status: **CLOSED**

Merge baseline:
- `addca46a88c104394a37bc6513c22e2556e3acf4`

Closed outcomes:
- raw discovered URL/path, anchor text, titles, body excerpts and semantic fields remain machine-side;
- selector/operator receive only opaque destination identity plus governed classification/provenance;
- only explicitly authorized metadata-class destinations may project.

### C5.3C — Root transport fitness gate

Status: **CLOSED / HARNESS BASELINE FROZEN**

Merge baseline:
- `edf344b34196258b04041f2fda2caa07d06d1f72`

Closed outcomes:
- root transport fitness separated from insurer/product screening;
- exact allowed sequence frozen: `static_http → playwright_headless → playwright_visible`;
- browser fallback is explicit and ordered;
- no new crawler or transport implementation was added.

### C5.4 — Product #10 three-gate blind cold-start

Status: **GATE A CLOSED / PASS; GATE B AUTHORIZED**

Protocol:
- `docs/architecture/health_post_hc1_neutral_cold_start_protocol_v7_product10.json`

Preregistration merge:
- `8d6f0c763333f75ecd5edab2181db23a41783a99`

Gate A frozen result:
- `docs/architecture/health_product10_gate_a_root_transport_fitness_2026-08-26.json`

Gate A observed results:
- `https://irdai.gov.in/non-life-insurers1` → `DIRECT_HTTP_AVAILABLE` using `static_http` only;
- `https://irdai.gov.in/health-insurers1` → `DIRECT_HTTP_AVAILABLE` using `static_http` only;
- `https://bimabharosa.irdai.gov.in/Home/UnclaimedAmount` → `ALL_ALLOWED_TRANSPORTS_FAILED` after `static_http`, `playwright_headless`, `playwright_visible`;
- Gate A decision: **PASS** because two exact preregistered regulator roots satisfy the frozen minimum pass condition;
- search-engine fallbacks: 0;
- ad-hoc transport attempts: 0;
- Gate B raw operator/selector reads: 0;
- insurer/product screening: not started;
- Product #10 selected: false;
- target-clause reads: 0.

Execution lineage is frozen to disposable non-merged smoke branch `product10-gate-a-live-smoke`, commit `4267e324791961f0cb3433fe1f04a1b1a5bbe4cb`, workflow run `32938095594`, job `98083250521`. The smoke branch is not merge-authorized.

## Next authorized work

### Product #10 Gate B — Blind metadata-path discovery fitness

Status: **ONLY AUTHORIZED LIVE EXPERIMENT STEP**

Rules:
- use only passing Gate A regulator roots and regulator-derived insurer origins permitted by v7;
- machine-side `CaptureEngine` / preservation / discovery may inspect raw page material;
- selector/operator may consume only `blind_discovery_link_metadata_v1`;
- raw destination URL/path, anchor text, page title, body text, screenshot and semantic evidence must not cross the blindness boundary;
- only C5.3B-authorized metadata page types may project;
- unknown/disallowed destinations fail closed;
- record Gate B outcome before Gate C begins;
- no insurer/product eligibility screening during Gate B.

### Product #10 Gate C — Neutral insurer/product selection

Status: **BLOCKED UNTIL GATE B PASS + RECORDED OUTCOME**

No candidate insurer or product screening is authorized until Gate B passes and its outcome is frozen under v7.

Motor gate remains **CLOSED**.

## Known defects / risks currently tracked

1. Live regulator/insurer endpoints can change behavior; historical transport observations remain experiment-specific.
2. Root transport capability can differ by mechanism and time; direct HTTP and browser outcomes must remain explicitly governed.
3. Discovery classification is regression-covered for the C5.3 boundary cases, but new ambiguous live patterns must fail closed.
4. Legacy certifiers emit `EvidencePackage.version_status="CURRENT_APPLICABLE"`; this remains non-authoritative metadata pending a versioned evidence-contract migration.
5. Generic copay shadow migration is non-authoritative; authority switch is not authorized.
6. Governed LLM answer pipeline exists as a limited pilot; broader concept coverage is not yet proven.
7. Product #7, Product #8 and Product #9 are immutable unscored experiment closures and must not be repaired retroactively.
8. Product #8 contamination events lack exact-product exposure lineage sufficient to make them automatically eligible for Product #10; v7 remains conservative.

## Explicitly not authorized now

- Product #10 Gate C or insurer/product screening before Gate B passes and is frozen
- search-engine candidate screening or fallback during the locked v7 run
- ad-hoc transport outside the frozen Gate A sequence
- exposing raw discovered URLs, anchor text, body text, titles, screenshots or semantic fields to selector/operator during Gate B
- merging the disposable `product10-gate-a-live-smoke` branch
- reopening, retrying, repairing, rescoring or reselecting Product #7, Product #8 or Product #9
- Motor implementation or expansion
- Life implementation or investment-comparison logic
- frontend / consumer app / advisor UI
- recommendation-engine expansion
- claims application
- quote-comparison UX
- database migration for scale
- broad ingestion scale-up
- new agent families
- generic copay shadow authority switch
- architecture redesign without an observed falsification
- vocabulary expansion merely to increase concept count
- broad certification-contract cleanup during Product #10

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
