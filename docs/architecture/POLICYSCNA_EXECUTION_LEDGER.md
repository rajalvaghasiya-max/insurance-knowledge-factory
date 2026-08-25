# PolicyScna Execution Ledger

Status: C5.1 selection-method hardening
Verified against: `20d2d678bc029f2394344e7638e0721dbab5d676`

This ledger defines the current authorized execution path. It exists to prevent scope drift, accidental rebuilding of existing capability, and architecture work that is not justified by observed evidence.

## Current phase

**Health repeatability — selection-method hardening after Product #8 preselection abort.**

Motor, Life and frontend work remain outside the current authorized phase.

## Immediate objective

Replace contamination-prone search-result screening with a frozen direct-source, blind metadata-selection boundary before any Product #9 screening. Preserve Product #7 and Product #8 as immutable unscored experiment history.

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
- governed source-asset classification restored to tracked repository state;
- `ProductSignalExtractor` clean-checkout execution restored;
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
- the full current insurer universe was reconciled: 27 General + 6 standalone Health insurers;
- no Product #8 was selected;
- no selected-product acquisition, target semantic review or scoring began;
- every insurer was prior-excluded, non-qualifying, currentness-insufficient, or quarantined by the locked v5 preselection firewall;
- Product #8 closed `SELECTION_UNIVERSE_EXHAUSTED_NO_ELIGIBLE_UNCONTAMINATED_CURRENTNESS_CORROBORATED_PRODUCT / UNSCORED`;
- Product #8 does not prove or falsify semantic repeatability and does not authorize Motor.

Methodology finding:

**`SEARCH_ENGINE_DISCOVERY_IS_TOO_CONTAMINATION_PRONE_FOR_V5_PRESELECTION`.** Broad and exact-UIN search queries frequently exposed prohibited product-document links or target-mechanic snippets even when the intended query was metadata-only. This finding may shape a future protocol but cannot repair Product #8 retroactively.

### C5.1 — Blind direct-source preselection method

Status: **IN PROGRESS — ONLY AUTHORIZED NEXT WORK**

Work classification: **WIRE + small EXTEND**.

Repository census result:
- existing acquisition / `ProductSignalExtractor`: REUSE;
- existing `UinCandidateExtractor`: REUSE;
- existing `ProductIdentityResolver`: REUSE after selection only because verified identity deliberately requires approved product-document evidence;
- safe identity-only preselection projection: absent before C5.1;
- new crawler or agent family: not authorized.

Authorized deliverables:
1. `BlindPreselectionMetadataProjector` as an information firewall over existing product-signal output;
2. selector receives only identity/UIN/source metadata, never raw sections, evidence windows, semantic buckets, or semantic-presence counts;
3. direct regulator/insurer metadata roots replace broad search-result discovery after a future experiment lock;
4. semantic content detected internally by existing machine extraction cannot influence selection because it is structurally absent from the selector contract;
5. raw acquisition/full extraction remains separately retained for audit;
6. exact blind projection used for selection must be hash-lockable and auditable.

Frozen method artifact:
- `docs/architecture/health_neutral_preselection_method_v5_1.json`

### C5.2 — Product #9 preregistration

Status: **NOT YET AUTHORIZED UNTIL C5.1 MERGES GREEN**

Before any Product #9 screening, a new preregistration must:
- name the exact allow-listed direct-source roots used for the run;
- define deterministic cross-category insurer ordering;
- attest that selection consumes only `blind_preselection_product_metadata_v1` projections;
- preserve prior experiment exclusions/history without retroactively changing Product #8;
- retain HC-1.5 `f05ca07` as the semantic scoring baseline unless a separately approved architecture decision changes the experiment design;
- retain v4.2 present-tense evidence eligibility before semantic scoring.

**No Product #9 candidate screening is authorized before that preregistration merges.**

Motor gate remains **CLOSED**.

## Known defects / risks currently tracked

1. Live insurer/regulator endpoints can change behavior or defeat automated retrieval; live runs remain operational smoke checks.
2. Direct-source metadata roots may themselves change layout or link structure; the future selection protocol must fail closed rather than fall back to broad search.
3. Legacy certifiers emit `EvidencePackage.version_status="CURRENT_APPLICABLE"`; this remains non-authoritative metadata pending a versioned evidence-contract migration.
4. Generic copay shadow migration is non-authoritative; authority switch is not authorized.
5. Governed LLM answer pipeline exists as a limited pilot; broader concept coverage is not yet proven.
6. Product #7 and Product #8 are immutable unscored experiment closures and must not be repaired retroactively.

## Explicitly not authorized now

- Product #9 screening before C5.1 and a new preregistration are merged
- broad search-engine candidate screening in the next neutral experiment
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
- broad certification-contract cleanup during C5.1

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
