# PolicyScna Execution Ledger

Status: C4 closure candidate
Verified against: `9c495b0acf3cf96d2f383faff1a8b84ec927e0cb`

This ledger defines the current authorized execution path. It exists to prevent scope drift, accidental rebuilding of existing capability, and architecture work that is not justified by observed evidence.

## Current phase

**Health repeatability — preparing the next neutral cold-start experiment.**

Motor, Life and frontend work remain outside the current authorized phase.

## Immediate objective

Freeze the C4 evidence-eligibility correction, then run a fresh Health cold-start experiment under the repaired acquisition/currentness path and the v4.2 current-product scoring gate.

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
- genuine governed `registry/source_asset_classification_rules.json` restored to tracked repository state;
- `SourceAssetClassifier` and `ProductSignalExtractor` clean-checkout execution restored;
- PDF validation / SHA / immutable-storage boundary covered;
- generic browser-assisted protected-PDF transport added behind the same validation boundary;
- document-role classification hardened against the observed GRO-mapping false positive;
- deterministic offline acquisition fitness covers preservation → sections → product signals/UIN → PDF discovery.

Live insurer/browser availability remains an operational smoke concern, not a normal CI dependency.

### C3 — Reconnect acquisition to currentness governance

Status: **CLOSED / REVIEWED / FROZEN**

Closed outcomes:
- acquisition observations bridge into the existing `SourceObservationRecord` contract;
- persisted download runs can be bound by exact `observation_id` to an explicit registered document version;
- exact bytes and retained source-page artifacts are hash-checked before governance handoff;
- byte-identical, changed-bytes and failed observations remain distinct;
- changed bytes cannot become positive `DocumentCurrentnessEvidenceRecord` evidence;
- temporal/currentness authority remains in `DocumentIdentityResolutionOverlay`.

Independent review at merge `90fe884165442a7423c561033a576105e6c1e1a2`: APPROVE FREEZE; no blocker or important finding.

### C4 — Current-product repeatability evidence-eligibility closure

Status: **CLOSED PENDING THIS LEDGER MERGE**

Closed outcomes:
1. Product #7 is immutably recorded as `CURRENTNESS_SELECTION_INVALIDATED / UNSCORED`; the original V01 selection remains historical experiment evidence and V02 substitution is prohibited.
2. `CurrentProductRepeatabilityEvidenceEligibility` now requires exact:
   - target entity;
   - document version id;
   - source SHA-256;
   - document role;
   - resolved document identity;
   - evidence-review eligibility;
   - `current_observed_reviewed` temporal status;
   - current entitlement eligibility.
3. Semantic certification may still PASS for historical/replaced documents. It is not itself proof of current-product evidence eligibility.
4. Legacy `EvidencePackage.version_status="CURRENT_APPLICABLE"` emitted by certification builders is explicitly classified as **non-authoritative for temporal currentness**. Current-product scoring is forbidden from consuming that field as currentness proof.
5. The legacy field rename is deferred to a deliberate versioned evidence-contract migration because broad edits to proven certifiers are metadata cleanup, not a C4 safety prerequisite.
6. v4.2 is locked before the next cold-start experiment.

### C5 — Next neutral Health cold-start experiment

Status: **NEXT AUTHORIZED MILESTONE**

Preconditions now satisfied:
- C2 acquisition fitness green;
- C3 currentness handoff green and frozen;
- C4 current-product evidence-eligibility rules frozen before selection;
- clean checkout / declared dependencies reproduce the canonical suite.

Required sequence:
1. preregister the next neutral Health cold-start protocol before product selection;
2. preserve contamination firewall and immutable selection history;
3. acquire and register exact source bytes through the repaired C2/C3 path;
4. establish governed product/document identity and currentness before any current-product score may count;
5. perform semantic correctness census against the frozen HC-1.5 baseline;
6. score only evidence that passes the v4.2 eligibility gate.

Motor gate remains **CLOSED** unless the repeatability protocol explicitly authorizes crossing it after a successful neutral Health result.

## Known defects / risks currently tracked

1. Live insurer/regulator endpoints can still change behavior or defeat automated retrieval; keep live runs as operational smoke checks.
2. Legacy certification builders emit `EvidencePackage.version_status="CURRENT_APPLICABLE"`; this is non-authoritative metadata and must be migrated only through a versioned evidence-contract change.
3. Generic copay shadow migration is non-authoritative and has zero executable coverage; authority switch is not authorized.
4. Governed LLM answer pipeline exists as a deductible pilot; broader concept coverage is not yet proven.
5. Product #7 remains an immutable unscored experiment closure; it must never be retroactively repaired by substituting another version.

Resolved C1-era defects are removed from this list once their repair is merged and covered by CI.

## Explicitly not authorized now

- Motor implementation or expansion
- Life implementation or investment comparison logic
- Frontend / consumer app / advisor UI
- Recommendation-engine expansion
- Claims application
- Quote-comparison UX
- Database migration for scale
- Broad ingestion scale-up
- New agent families
- Generic copay shadow authority switch
- Architecture redesign without an observed falsification
- Vocabulary expansion merely to increase concept count
- Retroactive Product #7 rescoring or V02 substitution
- Broad certification-contract cleanup before C5

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
