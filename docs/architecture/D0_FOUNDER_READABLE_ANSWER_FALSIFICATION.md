# D0 Founder-Readable Governed Answer Slice — Falsification Protocol

Status: PREREGISTERED BEFORE RENDERER WORK

## Purpose

D0 tests whether already-proven governed intelligence composes into a human-usable answer. It is not a frontend milestone and must not add insurer-specific answer prose.

## Cases

The experiment must use one generic projection path for all three cases:

1. factual answer — Star Comprehensive PED waiting period;
2. resolved conditional answer — waiting-period applicability with sufficient approved case context;
3. fail-closed answer — exact-boundary or materially incomplete context.

## Machine gates

A D0 projection passes only if all of the following are true:

- ONE generic projector renders all three cases; no case/product-specific renderer or prose branch is permitted;
- the human view is a separate object from provenance/developer detail;
- the human view contains the answer or explicit uncertainty, plain-language meaning, and honest unknowns/limitations;
- a fail-closed human view contains a concrete resolution next step describing what fact/document/person would resolve the uncertainty;
- provenance remains separately inspectable and preserves evidence/source/finding references and machine trace lineage;
- no product/insurer identifier is used to choose wording or layout;
- the projector cannot manufacture new insurance facts, recommendations, claim approval, or payment conclusions.

## Outsider comprehension gate

The founder/developer is not the readability judge. At least one outsider who has not participated in PolicyScna architecture work must read ONLY the human view, without the provenance panel or architecture explanation.

Before the outsider sees the output, score these questions independently for each case:

1. Can the reader state the answer or uncertainty correctly? YES/NO
2. Can the reader state what the answer means for the customer? YES/NO
3. Can the reader state what PolicyScna still does not know or cannot conclude? YES/NO
4. For the fail-closed case only: can the reader state the next action that could resolve the uncertainty? YES/NO

Pass threshold:

- Cases 1 and 2: 3/3 YES.
- Case 3: 4/4 YES.
- Any materially incorrect interpretation is an automatic fail regardless of score.

The outsider's responses must be captured verbatim before scoring. The projector must not be edited after seeing the outsider responses and then re-scored as the same experiment; a changed projector requires a new run.

## Negative controls

- Removing a limitation from the machine response must remove or change the corresponding human-view uncertainty; otherwise the projector is not causally controlled by governed output.
- Changing the approved direct answer or explanation text must change the human view; otherwise the projector is masking machine output with canned insurance prose.
- The same projector must render an unrehearsed fourth ResponseAssemblerOutput fixture without a new template branch.

## Raw baseline

Frozen PR #279 ran before this implementation. Hosted result: `1 failed, 3509 passed`. The only failure was the absence of a separate generic human-answer projection boundary. No production runtime changes were present in that PR.

## Implementation boundary

The repair lives under the existing `II.RESPONSE.ASSEMBLY` ownership path at `insurance_intelligence/response/human_answer.py`. This is a separate projection object over the canonical `ResponseAssemblerOutput`; the assembler contract itself remains unchanged.

## Stop rule

Machine gates may be automated. Human readability cannot be self-certified by the developer or founder. D0 remains incomplete until the preregistered outsider comprehension gate has been run on the actual three human views.
