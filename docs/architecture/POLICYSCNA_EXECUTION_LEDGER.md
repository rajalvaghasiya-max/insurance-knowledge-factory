# PolicyScna Execution Ledger

Status: C5.4 Product #10 three-gate cold start — Gate A authorized
Verified against: `8d6f0c763333f75ecd5edab2181db23a41783a99`

This ledger defines the current authorized execution path. It exists to prevent scope drift, accidental rebuilding of existing capability, and architecture work that is not justified by observed evidence.

## Current phase

**Health repeatability — Product #10 v7 preregistration is frozen; Gate A root transport fitness is the only authorized live experiment step.**

Motor, Life and frontend work remain outside the current authorized phase.

## Immediate objective

Execute Product #10 **Gate A only** against the exact preregistered roots using the frozen C5.3C transport sequence. Record each root outcome before any Gate B blind metadata-path discovery or Gate C insurer/product screening begins.

Authoritative Product #10 protocol:
- `docs/architecture/health_post_hc1_neutral_cold_start_protocol_v7_product10.json`

Frozen baselines:
- semantic scoring baseline: `f05ca07283f53f2882ed5da3ca27875ba7253318`
- experiment-harness baseline: `edf344b34196258b04041f2fda2caa07d06d1f72`
- Product #10 preregistration merge: `8d6f0c763333f75ecd5edab2181db23a41783a99`

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
- full current insurer universe reconciled: 27 General + 6 standalone Health insurers;
- no Product #8 selected;
- no selected-product acquisition, target semantic review or scoring began;
- Product #8 closed `SELECTION_UNIVERSE_EXHAUSTED_NO_ELIGIBLE_UNCONTAMINATED_CURRENTNESS_CORROBORATED_PRODUCT / UNSCORED`;
- Product #8 does not prove or falsify semantic repeatability and does not authorize Motor.

Methodology finding:

**`SEARCH_ENGINE_DISCOVERY_IS_TOO_CONTAMINATION_PRONE_FOR_V5_PRESELECTION`.** Broad/exact-UIN search queries frequently exposed prohibited product-document links or target-mechanic snippets. This finding cannot repair Product #8 retroactively.

### C5.1 — Blind direct-source preselection method

Status: **CLOSED**

Merge baseline:
- `d7dc909696670f77d0db565fc8855820775e53f2`

Closed outcomes:
- work classified `WIRE + small EXTEND`, not a new agent family;
- existing acquisition / `ProductSignalExtractor` and `UinCandidateExtractor` reused;
- `BlindPreselectionMetadataProjector` exposes only identity/UIN/source metadata to the selector;
- raw sections, evidence windows, target semantic buckets and semantic-presence counts are structurally absent from selector input;
- regression proves semantic-content changes with unchanged identity metadata do not change the blind projection;
- broad search-result discovery is prohibited for locked selection runs unless a future preregistration safely changes that rule before execution.

### C5.2 — Product #9 blind direct-source cold-start

Status: **CLOSED / UNSCORED BEFORE SELECTION**

Protocol:
- `docs/architecture/health_post_hc1_neutral_cold_start_protocol_v6_product9.json`

Closure:
- `docs/architecture/health_product9_preselection_abort_2026-08-26.json`

Observed result:
- Product #9 remained unselected and unscored;
- IRDAI non-life and Health preregistered roots returned 403 and did not trigger search fallback;
- Bima Bharosa was the reachable preregistered fallback root;
- regulator directory entries for the four preregistered retry insurers exposed only bare/ambiguous insurer origins;
- the then-active pre-render operator guardrail refused to render those origins because they could not be classified as metadata before body rendering;
- zero insurer origins rendered, zero product documents opened, zero target-clause reads occurred, zero search fallbacks occurred, zero selection overrides/substitutions occurred;
- Product #9 closed `EXPERIMENT_UNSCORED / PRE_RENDER_METADATA_PATH_UNAVAILABLE_FOR_ALL_PREREGISTERED_RETRY_INSURERS`;
- Product #9 does not prove or falsify semantic repeatability and does not authorize Motor.

**No Product #9 candidate screening is authorized now or in any future run. Product #9 is an immutable closed experiment.**

Methodology finding:

The C5.2A operator guardrail was stricter than the actual blindness requirement. The true requirement is that semantic body content must not reach the selector/operator before selection; machine-only capture may occur if only a governed sanitized projection crosses the boundary. This finding cannot reopen or repair Product #9 retroactively.

### C5.3A — Discovery classifier blindness-boundary proof

Status: **CLOSED**

Merge baseline:
- `2d3dd02ab92abcc8f3df9e3111cf90730874ffc1`

Closed outcomes:
- existing `DiscoveryAgent` reused unchanged;
- direct contract coverage proves positive metadata/index classifications and negative product-detail classifications;
- semantic anchor text and semantic URL slugs do not promote product-detail destinations into the metadata-class set;
- policy-wording destinations remain outside the metadata-class set;
- no runtime classifier repair was required.

### C5.3B — Blind discovery-link projection

Status: **CLOSED**

Merge baseline:
- `addca46a88c104394a37bc6513c22e2556e3acf4`

Closed outcomes:
- existing machine-side discovery records remain internal;
- raw discovered URL/path, anchor text, titles, body excerpts and semantic fields do not cross to selector/operator;
- selector-facing discovery output uses opaque SHA-256 destination identity plus derived classification/provenance;
- adversarial regression proves semantic-bearing URL slugs cannot leak through the projection;
- only explicitly authorized metadata-class destinations may project;
- product-detail and policy-wording destinations fail closed.

### C5.3C — Root transport fitness gate

Status: **CLOSED / HARNESS BASELINE FROZEN**

Merge baseline:
- `edf344b34196258b04041f2fda2caa07d06d1f72`

Closed outcomes:
- root transport fitness is separated from insurer/product screening;
- allowed transport sequence is explicitly frozen to the existing `CaptureEngine` order:
  1. `static_http`
  2. `playwright_headless`
  3. `playwright_visible`
- accepted static capture stops before browser fallback;
- browser fallback after static HTTP failure/403 is explicit and ordered;
- all allowed transport failures remain a failure;
- `BROWSER_CAPTURE_AVAILABLE` is a broader preregistered transport capability than the direct-root observation that closed Product #9;
- no new crawler or transport implementation was added.

### C5.4 — Product #10 three-gate blind cold-start preregistration

Status: **PREREGISTRATION CLOSED / GATE A AUTHORIZED**

Protocol:
- `docs/architecture/health_post_hc1_neutral_cold_start_protocol_v7_product10.json`

Merge baseline:
- `8d6f0c763333f75ecd5edab2181db23a41783a99`

Frozen design:
- exact roots remain:
  - `https://irdai.gov.in/non-life-insurers1`
  - `https://irdai.gov.in/health-insurers1`
  - `https://bimabharosa.irdai.gov.in/Home/UnclaimedAmount`
- Gate A uses only the frozen `static_http → playwright_headless → playwright_visible` sequence;
- Gate B allows machine-only raw capture/discovery but selector/operator may consume only `blind_discovery_link_metadata_v1`;
- raw destination URL/path, anchor text, titles, body text, screenshots and semantic evidence may not cross the Gate B blindness boundary;
- Gate C begins only after Gate A and Gate B pass and consumes only governed blind projections;
- candidate insurer pool remains the four Product #9 retry-pool insurers derived from Product #8 `EXCLUDED_METADATA_CURRENTNESS_INSUFFICIENT` status;
- Product #8 contamination quarantines remain closed;
- Product #9 is not reopened or retried;
- exact-product prior-exposure audit is required after selection and before semantic review;
- exact bytes/SHA, reviewed currentness and v4.2 evidence eligibility remain mandatory before target-clause reads;
- no product/version substitution is authorized after selection.

## Next authorized work

### Product #10 Gate A — Root transport fitness

Status: **ONLY AUTHORIZED LIVE EXPERIMENT STEP**

Rules:
- run only against the three exact v7 preregistered roots;
- use only `collectors.capture_engine.CaptureEngine` with the frozen sequence;
- record one governed outcome per root: `DIRECT_HTTP_AVAILABLE`, `BROWSER_CAPTURE_AVAILABLE`, or `ALL_ALLOWED_TRANSPORTS_FAILED`;
- browser success after static HTTP failure is allowed because it was preregistered before Product #10 execution;
- no search-engine fallback and no ad-hoc transport are authorized;
- do not begin Gate B until Gate A has a passing root and its outcome record is frozen;
- do not begin Gate C or any insurer/product screening during Gate A.

### Product #10 Gate B — Blind metadata-path discovery fitness

Status: **BLOCKED UNTIL GATE A PASS + RECORDED OUTCOME**

Machine-only raw capture/discovery is permitted only after Gate A passes. Selector/operator exposure remains limited to `blind_discovery_link_metadata_v1`.

### Product #10 Gate C — Neutral insurer/product selection

Status: **BLOCKED UNTIL GATE A AND GATE B PASS**

No candidate insurer or product screening is authorized before both upstream gates pass under the locked v7 protocol.

Motor gate remains **CLOSED**.

## Known defects / risks currently tracked

1. Live regulator/insurer endpoints can change behavior or defeat automated retrieval; locked runs must fail closed rather than fall back to broad search.
2. Root transport capability can differ by mechanism; direct HTTP failure and browser capture success are distinct governed outcomes.
3. Discovery classification is regression-covered for the C5.3 boundary cases, but live site structures may expose new ambiguous patterns; unknown classifications must fail closed.
4. Legacy certifiers emit `EvidencePackage.version_status="CURRENT_APPLICABLE"`; this remains non-authoritative metadata pending a versioned evidence-contract migration.
5. Generic copay shadow migration is non-authoritative; authority switch is not authorized.
6. Governed LLM answer pipeline exists as a limited pilot; broader concept coverage is not yet proven.
7. Product #7, Product #8 and Product #9 are immutable unscored experiment closures and must not be repaired retroactively.
8. Product #8 contamination events lack exact-product exposure lineage sufficient to make them automatically eligible for Product #10; v7 therefore remains conservative.

## Explicitly not authorized now

- Product #10 Gate B before a passing Gate A outcome is recorded
- Product #10 Gate C or insurer/product screening before Gate A and Gate B pass
- search-engine candidate screening or fallback during the locked v7 run
- ad-hoc transport outside the frozen Gate A sequence
- exposing raw discovered URLs, anchor text, body text, titles, screenshots or semantic fields to selector/operator during Gate B
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
