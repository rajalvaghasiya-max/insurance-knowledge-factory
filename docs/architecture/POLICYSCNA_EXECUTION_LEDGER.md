# PolicyScna Execution Ledger

Status: C1 v1
Verified against: `593a5d2afb0ee4c9cdc564941ef9ff4e1a6478e7`

This ledger defines the current authorized execution path. It exists to prevent scope drift, accidental rebuilding of existing capability, and architecture work that is not justified by observed evidence.

## Current phase

**Health foundation / repeatability and operational fitness.**

Motor, Life and frontend work remain outside the current authorized phase.

## Immediate objective

Restore a reproducible acquisition-to-governance path and make current-product repeatability scoring depend on the right/current evidence identity, without rebuilding capabilities that already exist.

## Authorized work sequence

### C1 — Capability registry / architecture map / execution ledger

Status: IN PROGRESS

Deliverables:
- `docs/architecture/POLICYSCNA_CAPABILITY_REGISTRY.md`
- `docs/architecture/POLICYSCNA_ARCHITECTURE_MAP.md`
- `docs/architecture/POLICYSCNA_EXECUTION_LEDGER.md`

Exit condition: merged, CI green, and used as the pre-build lookup for subsequent work.

### C2 — Restore acquisition foundation

Authorized actions:
1. Recover the genuine governed `source_asset_classification_rules.json` (or prove its tracked successor) rather than synthesizing product-specific logic.
2. Restore `ProductSignalExtractor` clean-checkout execution.
3. Formalize browser/Xvfb runtime requirements for preservation.
4. Add representative acquisition fitness tests so CI covers capture → text → screenshot → PDF discovery/classification → PDF download/hash where feasible.
5. Harden protected-document retrieval generically. Browser-assisted retrieval may be used only if bytes pass the same signature/content validation, immutable raw storage and SHA-256 registration boundary as the existing downloader.
6. Improve document-role classification based on generic evidence, not insurer-specific branches.

Non-goal: no new crawler architecture unless existing mechanisms are proven incapable.

### C3 — Reconnect acquisition to revalidation/currentness

Authorized actions:
1. Wire download/change events into existing `document_change_impact` machinery.
2. Wire candidate changes into the durable revalidation work queue.
3. Preserve the existing separation between advisory change detection, reviewed currentness evidence, document identity resolution and publication eligibility.
4. Add tests proving the connection without making revalidation candidates automatically authoritative.

Non-goal: do not rebuild product identity, currentness evidence, document identity resolution or publication eligibility.

### C4 — Current-product repeatability evidence-eligibility closure

Authorized actions:
1. Record Product #7 as `CURRENTNESS_SELECTION_INVALIDATED`, unscored and immutable.
2. Amend future current-product repeatability scoring so semantic reuse only counts when:
   - product identity is resolved;
   - document identity is resolved;
   - document role is correct;
   - currentness is resolved for the experiment's present-tense scope;
   - exact source/candidate/version/hash lineage is valid;
   - semantic correctness census passes.
3. Track the known certification-contract defect where certifiers assert `CURRENT_APPLICABLE` without deriving it from temporal governance. Decide whether to remove, derive or temporal-neutralize that field only after the evidence-eligibility contract is explicit.

Non-goal: historical semantic certification must remain possible; historical documents are not globally invalid evidence.

### C5 — Next neutral Health cold-start experiment

Preconditions:
- C2 acquisition fitness green;
- C3 revalidation wiring green;
- C4 current-product evidence-eligibility rules frozen before selection;
- clean checkout and declared dependencies reproduce the test baseline.

Then select a fresh neutral Health product/version and repeat the preregistered experiment.

Motor gate remains CLOSED unless the repeatability protocol explicitly authorizes crossing it.

## Known defects / risks currently tracked

1. Missing `registry/source_asset_classification_rules.json` breaks `SourceAssetClassifier` and ProductSignalExtractor on clean `main`.
2. Protected insurer/regulator PDF endpoints can defeat the requests-based downloader.
3. PDF document-role classification produced a false policy-wording candidate during ICICI smoke.
4. Acquisition → document-change → revalidation wiring is incomplete/disconnected.
5. Semantic certifiers hardcode `version_status="CURRENT_APPLICABLE"` without governed currentness derivation.
6. Product #7 currentness selection was invalidated by discovery of newer ICICI Arogya Sanjeevani UIN/version.
7. Generic copay shadow migration is non-authoritative and has zero executable coverage; authority switch is not authorized.
8. Governed LLM answer pipeline exists as a deductible pilot; broader concept coverage is not yet proven.

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

External reviews (including Claude) may challenge this ledger, but changes must be reconciled against tracked code/tests/artifacts before the ledger is updated.
