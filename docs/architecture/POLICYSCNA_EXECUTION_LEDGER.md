# PolicyScna Execution Ledger

Status: C5.3 experiment-harness freeze
Verified against: `edf344b34196258b04041f2fda2caa07d06d1f72`

This ledger defines the current authorized execution path. It exists to prevent scope drift, accidental rebuilding of existing capability, and architecture work that is not justified by observed evidence.

## Current phase

**Health repeatability — C5.3 experiment harness frozen; next neutral Health attempt requires fresh preregistration before any screening.**

Motor, Life and frontend work remain outside the current authorized phase.

## Immediate objective

Freeze `edf344b34196258b04041f2fda2caa07d06d1f72` as the experiment-harness baseline. The next authorized work is preregistration only: define a future neutral Health cold-start protocol that separates root transport fitness, blind metadata-path discovery, and insurer/product selection before any candidate screening begins.

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
- existing acquisition / `ProductSignalExtractor` reused;
- existing `UinCandidateExtractor` reused;
- `ProductIdentityResolver` remains a post-selection identity capability because verified identity deliberately requires approved product-document evidence;
- `BlindPreselectionMetadataProjector` exposes only identity/UIN/source metadata to the selector;
- raw sections, evidence windows, target semantic buckets and semantic-presence counts are structurally absent from selector input;
- regression proves semantic-content changes with unchanged identity metadata do not change the blind projection;
- broad search-result discovery is prohibited for future locked selection runs;
- direct-source method frozen in `docs/architecture/health_neutral_preselection_method_v5_1.json`.

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
- semantic anchor text does not promote a product-detail destination into the metadata-class set;
- semantic URL slugs do not promote a product-detail destination into the metadata-class set;
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
- `BROWSER_CAPTURE_AVAILABLE` is recognized as a broader preregistered transport capability than the direct-root observation that closed Product #9;
- no new crawler or transport implementation was added.

**`edf344b34196258b04041f2fda2caa07d06d1f72` is the frozen experiment-harness baseline for the next neutral Health preregistration.**

## Next authorized work

### Future neutral Health cold-start preregistration

Status: **PREREGISTRATION ONLY — PRODUCT SCREENING NOT YET AUTHORIZED**

The next protocol must separate three gates before candidate screening begins:

1. **Gate A — Root transport fitness**
   - use only preregistered roots;
   - use only the frozen C5.3C transport sequence;
   - record transport outcome before insurer/product screening.

2. **Gate B — Blind metadata-path discovery fitness**
   - machine-side capture/discovery may inspect raw page material;
   - selector/operator may consume only the C5.3B blind discovery-link projection;
   - no raw URL path, anchor/body text, title, screenshot or semantic evidence may cross the blindness boundary;
   - failure to derive at least one authorized metadata-class destination must fail closed separately from product eligibility.

3. **Gate C — Neutral insurer/product selection**
   - begins only after Gate A and Gate B pass under the preregistered protocol;
   - selector consumes only governed blind metadata projections;
   - deterministic selection rules, prior-exposure rules and currentness requirements must be frozen before screening;
   - exact bytes + reviewed currentness + v4.2 evidence eligibility must pass before target-clause semantic inspection;
   - no post-selection product/version substitution.

No candidate insurer or product may be screened until this future protocol is merged with CI green.

Motor gate remains **CLOSED**.

## Known defects / risks currently tracked

1. Live regulator/insurer endpoints can change behavior or defeat automated retrieval; future locked runs must fail closed rather than fall back to broad search.
2. Root transport capability can differ by mechanism; direct HTTP failure and browser capture success are distinct governed outcomes and must remain preregistered.
3. Discovery classification is now directly regression-covered for the C5.3 boundary cases, but live site structures may expose new ambiguous patterns; unknown classifications must fail closed.
4. Legacy certifiers emit `EvidencePackage.version_status="CURRENT_APPLICABLE"`; this remains non-authoritative metadata pending a versioned evidence-contract migration.
5. Generic copay shadow migration is non-authoritative; authority switch is not authorized.
6. Governed LLM answer pipeline exists as a limited pilot; broader concept coverage is not yet proven.
7. Product #7, Product #8 and Product #9 are immutable unscored experiment closures and must not be repaired retroactively.
8. Product #8 contamination events lack exact-product exposure lineage sufficient to make them automatically eligible for a future experiment; any future prior-exposure policy must be preregistered conservatively.

## Explicitly not authorized now

- insurer/product screening before the next neutral Health protocol is merged + green CI
- reopening, retrying, repairing, rescoring or reselecting Product #7, Product #8 or Product #9
- broad search-engine candidate screening or fallback in a locked neutral run unless a future protocol explicitly and safely changes that rule before screening
- silent expansion of Gate A transport mechanisms beyond the C5.3C frozen sequence
- exposing raw discovered URLs, anchor text, body text, titles, screenshots or semantic fields to selector/operator during blind path discovery
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
- broad certification-contract cleanup during the next Health repeatability attempt

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
