# PolicyScna Execution Ledger

Status: C5.2 Product #9 preregistration
Verified against: `d7dc909696670f77d0db565fc8855820775e53f2`

This ledger defines the current authorized execution path. It exists to prevent scope drift, accidental rebuilding of existing capability, and architecture work that is not justified by observed evidence.

## Current phase

**Health repeatability — Product #9 blind direct-source preregistration.**

Motor, Life and frontend work remain outside the current authorized phase.

## Immediate objective

Freeze Product #9 before screening using the C5.1 blind metadata firewall, exact regulator roots and conservative prior-exposure rules. No Product #9 candidate may be screened until the v6 preregistration is merged and CI is green.

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
- `BlindPreselectionMetadataProjector` now exposes only identity/UIN/source metadata to the selector;
- raw sections, evidence windows, target semantic buckets and semantic-presence counts are structurally absent from selector input;
- regression proves semantic-content changes with unchanged identity metadata do not change the blind projection;
- broad search-result discovery is prohibited for future locked selection runs;
- direct-source method frozen in `docs/architecture/health_neutral_preselection_method_v5_1.json`.

### C5.2 — Product #9 blind direct-source preregistration

Status: **IN PROGRESS — ONLY AUTHORIZED NEXT WORK**

Protocol candidate:
- `docs/architecture/health_post_hc1_neutral_cold_start_protocol_v6_product9.json`

Frozen design:
- HC-1.5 `f05ca07283f53f2882ed5da3ca27875ba7253318` remains the semantic scoring baseline;
- C5.1 merge `d7dc909696670f77d0db565fc8855820775e53f2` is the selection-method baseline;
- exact direct roots are limited to:
  - `https://irdai.gov.in/non-life-insurers1`
  - `https://irdai.gov.in/health-insurers1`
  - `https://bimabharosa.irdai.gov.in/Home/UnclaimedAmount`
- general web search and search-result snippets are forbidden during the locked screening run;
- insurer origins may be obtained only from regulator-linked official websites;
- selector consumes only `blind_preselection_product_metadata_v1`;
- only Product #8 insurers whose immutable status was `EXCLUDED_METADATA_CURRENTNESS_INSUFFICIENT` may be retried;
- Product #8 contamination quarantines remain conservatively ineligible because exact-product exposure lineage was not retained well enough to safely downgrade them;
- selection remains deterministic; semantic fit and manual override are forbidden;
- after selection, exact bytes + reviewed currentness + v4.2 evidence eligibility must pass before any target clause is read;
- no product/version substitution after selection.

**No Product #9 candidate screening is authorized until this preregistration merges with CI green.**

Motor gate remains **CLOSED**.

## Known defects / risks currently tracked

1. Live regulator/insurer endpoints can change behavior or defeat automated retrieval; locked runs must fail closed rather than fall back to broad search.
2. Direct-source metadata roots or insurer-linked paths may change layout; no search-engine fallback is authorized during Product #9.
3. Legacy certifiers emit `EvidencePackage.version_status="CURRENT_APPLICABLE"`; this remains non-authoritative metadata pending a versioned evidence-contract migration.
4. Generic copay shadow migration is non-authoritative; authority switch is not authorized.
5. Governed LLM answer pipeline exists as a limited pilot; broader concept coverage is not yet proven.
6. Product #7 and Product #8 are immutable unscored experiment closures and must not be repaired retroactively.
7. Product #8 contamination events lack exact-product exposure lineage sufficient to make them Product #9-eligible; the v6 protocol therefore excludes those insurers conservatively.

## Explicitly not authorized now

- Product #9 screening before v6 preregistration merge + green CI
- broad search-engine candidate screening or fallback during Product #9
- downgrading/reversing Product #8 contamination quarantines for Product #9
- retroactive Product #7 or Product #8 repair/rescoring/reselection
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
- broad certification-contract cleanup during C5.2

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
