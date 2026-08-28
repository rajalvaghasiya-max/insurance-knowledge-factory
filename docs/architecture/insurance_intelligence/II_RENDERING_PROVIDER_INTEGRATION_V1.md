# Insurance Intelligence — Rendering Provider Integration v1

## Purpose

Wire the existing MO-022 controlled LLM renderer into the newer Rendering Exit Safety v1 boundary without creating a second provider stack and without authorizing free-form LLM output.

The provider runtime is a candidate producer only.  Rendering Exit Safety remains the final release authority.

## Why this slice exists

MO-022 already provides useful infrastructure:

- provider-neutral `LLMRendererProvider`
- exact-once invocation
- provider identity matching
- timeout/error normalization
- structured output parsing
- deterministic legacy fidelity checks
- deterministic fallback to the pre-LLM explanation

Rendering Exit Safety v1, added later, establishes a stronger exit invariant over `ResponseAssemblerOutput`:

- canonical render units
- bidirectional commission/omission checks
- deterministic conformance
- `PRESERVE_EXACT` for every v1 unit
- original `ResponseAssemblerOutput` as the safe fallback

The two layers use different source representations.  This slice bridges them rather than duplicating either one.

## Governed flow

```text
validated ResponseAssemblerOutput
        |
        +--> Canonical Render Envelope -------------------------+
        |                                                       |
        |                                                       v
existing verified ExplanationGeneratorOutput --> MO-022 controlled renderer
                                                        |
                                                        v
                                              legacy candidate sections
                                                        |
                                                        v
                                      explicit source-section mapping
                                                        |
                                                        v
                                              RenderCandidate
                                                        |
                                                        v
                                      Rendering Exit Safety v1
                                           /              \
                                        PASS              FAIL
                                         |                 |
                                         v                 v
                                rendered text eligible   assembler fallback
```

## Non-negotiable invariants

1. The existing `LLMRendererProvider` is reused.  No parallel provider protocol is introduced.
2. The existing MO-022 renderer may reject a candidate early.  If it does, the assembler response is selected immediately.
3. A legacy renderer success is not sufficient for release.
4. Every successful legacy candidate is converted into a `RenderCandidate` and re-evaluated by Rendering Exit Safety.
5. Conversion may not normalize away unsafe provider output.
   - unknown legacy sections remain visible as unauthorized render units;
   - omissions remain omissions;
   - rewrites remain rewrites;
   - ordering remains checkable.
6. `PRESERVE_EXACT` remains authoritative in v1.  A paraphrase that passes the older MO-022 fidelity checks can still be rejected by the new exit gate.
7. Provider timeout, provider failure, malformed output, legacy fidelity failure, bridge mapping failure, or exit-conformance failure may never remove the validated assembler fallback.
8. The production model remains outside the truth boundary.

## Deliberate non-goals

This slice does not:

- add a vendor-specific production adapter;
- change `LLMRendererProvider`;
- authorize semantic paraphrasing;
- add an LLM judge;
- weaken `PRESERVE_EXACT`;
- change ResponseAssembler;
- authorize recommendations or advisory execution.

## Why a real provider is still deferred

With Rendering Exit Safety v1, every render unit currently uses `PRESERVE_EXACT`.  A real model therefore cannot yet improve wording without being rejected.  Connecting a paid/remote production provider before a governed transformation policy exists would add latency, cost, and operational risk without adding product value.

The correct next gate after this integration is to decide whether any narrowly defined transformation policy can be made structurally verifiable.  Until then, the deterministic assembler response is the production-safe floor.

## Acceptance evidence

The v1 tests prove at minimum:

- exact-preserve provider output can pass both layers;
- a paraphrase accepted by the older renderer is still rejected by the new exit gate;
- timeout/error/invalid provider response selects the assembler fallback;
- request identity mismatch fails before provider invocation;
- a failed exit gate never releases legacy rendered text;
- integration result identity is deterministic.
