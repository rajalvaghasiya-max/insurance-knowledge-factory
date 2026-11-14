# Health Customer v0 — Qualifying Dev36 Blind Score Record

Status: **QUALIFYING DEV36 SCORE ACCEPTED; HOLDOUT STILL REQUIRED**

This record consolidates the repository-supported evidence for the blind dev36 repair verdict used by Issue #435. It does not authorize any further answer-path tuning before the independent holdout is authored, frozen, run once, and scored.

## Bound artifacts

- Baseline pre-repair live artifact SHA-256: `19a5c760764cfd3b0f0975e0136da51585a9f4682b527816e62945df2f36d5aa`
- Final post-repair live artifact SHA-256: `ab55537ec3f223dab193f6acdbe7367a502dfd88ac111cbc957ab63b15f621a3`
- Blind A/B scorer packet SHA-256: `82db72878c999ec684a95889c73999197a7edcb020e62962f3cbf26a4c846a40`
- Blind-packet randomization seed: `4352026`
- Case count: 36

The repository also retains the earlier first arithmetic-change run binding:

- First arithmetic-change run SHA-256: `68372c0960dcb99ea6d11f8c672d88e86d4e1e809008bd760a41d5b7f50e67fc`
- Bound record: `benchmarks/health_customer_v0/evidence/dev36_after_components_arithmetic_run_2026-10-22.json`

## Qualifying scorer

- Scorer model: **Gemini 1.5 Pro**
- Independence status: **QUALIFYING**
- Project-owner declaration accepted for this run: scoring occurred in a fresh session with no exposure to implementation history, previous scores/diagnoses, or the A/B reveal mapping.
- Reveal mapping was applied only after scoring.

The exact external scorer prompt and the scored packet bytes are not currently archived in this repository. They must not be reconstructed or inferred. If the original external artifacts are available, they should be added verbatim in a follow-up evidence-only commit.

## Qualifying before/after results

| Metric | Before | After |
| --- | ---: | ---: |
| Safety PASS | 36/36 | 36/36 |
| Correctness = 2 | 3/36 | 31/36 |
| Usefulness = 2 | 3/36 | 31/36 |
| Clarity = 2 | 4/36 | 31/36 |
| Unnecessary deferral | 29/36 | 1/36 |

Repair verdicts:

- #432 concept-component/content repair: **19/25 materially improved** against preregistered threshold **>=18** — **PASS**.
- #433 arithmetic repair final dev result: **4/4 materially improved**.

## Corrected #433 arithmetic history

The final 4/4 result must not be described as a first-attempt preregistered pass.

1. The first arithmetic-change dev36 run was bound at SHA-256 `68372c0960dcb99ea6d11f8c672d88e86d4e1e809008bd760a41d5b7f50e67fc`.
2. Provisional scoring of that run found only **2/4** arithmetic material improvements and therefore **FAIL_PREREGISTERED_THRESHOLD**.
3. The failing dev arithmetic cases were inspected.
4. Generic arithmetic-context repairs were then made (#438, #439, #440).
5. A later final post-repair run, SHA-256 `ab55537ec3f223dab193f6acdbe7367a502dfd88ac111cbc957ab63b15f621a3`, produced the blind packet used for the qualifying score and yielded **4/4** arithmetic material improvements.

Therefore the accurate interpretation is: **initial arithmetic repair failed 2/4; generic follow-up repairs on inspected dev failures produced 4/4 on the final dev run.** The independent holdout is the generalization gate.

## Reference-criteria limitation

The historical `BLIND_SCORING_PROTOCOL.md` supplied the blind packet and scoring rubric to the scorer. Repository evidence does not establish that the scorer also received the 36 preregistered per-case reference criteria.

Accordingly:

- the qualifying score remains the accepted dev-repair evidence recorded on Issue #435;
- the holdout protocol must be stricter;
- the independent holdout scorer must receive the frozen scoring rubric **and the holdout's own preregistered reference criteria** so Correctness can be adjudicated directly against `must_include`, `must_not_imply`, legitimate dependency, acceptable clarification, and unnecessary-deferral criteria.

## Freeze implication

No runtime, prompt, model-routing, education-content, arithmetic, reasoning, relevance, or release-safety change is authorized before the independent holdout is frozen and run.
