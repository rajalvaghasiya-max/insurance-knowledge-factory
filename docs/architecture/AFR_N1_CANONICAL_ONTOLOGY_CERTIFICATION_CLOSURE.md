# AFR-N1 — Canonical Ontology Certification Closure

**Status:** CERTIFIED WITH EXPLICIT HISTORICAL PROVENANCE DEBT  
**Date:** 2026-08-15

## Scope

AFR-N1 was the remaining Architecture Fitness Review foundation gate after AR-2.5 repository cleanup and AR-3.0 hostile commercial-product pressure testing.

Its purpose was to prove that the canonical terminology / standard-definition layer can serve as a governed semantic backbone without becoming a glossary-shaped authority hazard.

## Certified gates

### AFR-N1.A — Governed standard-definition contract + PED valid time

Certified behaviors:

- immutable definition versions;
- source authority and evidence class;
- explicit effective ranges;
- category-scoped canonical identities;
- as-of-date resolution;
- stale 48-month PED meaning does not overwrite current 36-month meaning;
- overlapping or missing applicable definitions fail closed;
- product/customer/comparison fields remain outside the standard-definition contract.

### AFR-N1.B — Room Rent semantic preservation

Certified behaviors:

- historical IRDAI Room Rent definition preserves Room and Boarding expenses;
- associated medical expenses are preserved rather than amputated;
- unresolved current primary-source authority fails closed rather than silently carrying historical text forward.

### AFR-N1.C — Health Cumulative Bonus vs Motor NCB category collision

Certified behaviors:

- Health Cumulative Bonus and Motor No Claim Bonus retain separate category identities;
- exact alias resolution requires explicit category and as-of date;
- Health NCB is not silently collapsed into Cumulative Bonus;
- cross-category shortcuts fail closed.

### AFR-N1.D — Co-payment definition vs product conditionality

Certified behaviors:

- the generic co-payment definition explains the cost-sharing concept;
- product value, trigger, exception and scope remain product-governed facts;
- Star Comprehensive's 10%, entry-age trigger, renewal exception and section scope do not leak into the ontology definition.

### AFR-N1.E — Restoration vs recharge / trigger semantics

Certified behaviors:

- restoration and recharge are protected by an explicit false-synonym boundary at the canonical terminology layer;
- a product-governed feature may still map to the restoration benefit concept where evidence establishes that mapping;
- Star Comprehensive and Activ One NXT preserve different trigger, timing, frequency and same-hospitalization mechanics under the shared product-neutral restoration concept;
- shared concept identity does not imply identical customer entitlement or claim behavior.

## Final validation evidence

Latest final repair validation supplied locally:

```text
AFR-N1.E focused                         6 passed
HG-3 restoration semantic regression     6 passed
AFR-N1.A through E combined             30 passed
insurance_intelligence                2898 passed
regressions                               0
```

Previously certified focused gates:

```text
AFR-N1.A   9 passed
AFR-N1.B   3 passed
AFR-N1.C   6 passed
AFR-N1.D   6 passed
AFR-N1.E   6 passed
```

## Historical eleven-term traceability

The retained Canonical Insurance Ontology artifact states that eleven lay/marketing definitions originally motivated the work. The complete source list is not retained in the project material available at closure.

Six distinct identities are recoverable with provenance:

1. Pre-existing Disease
2. Room Rent
3. No Claim Bonus
4. Cumulative Bonus
5. Co-payment
6. Automatic Restoration

Five historical identities remain unknown.

The project performed recovery across repository history, retained ontology/roadmap material, attached project blueprint/review material, conversation exports and earlier concept-layer roadmap material. The complete eleven-definition source was not recovered.

The exact-eleven-identity historical criterion is therefore superseded as an executable closure blocker by `AFR_N1_TRACEABILITY_SUPERSESSION_DECISION.md`.

### Permanent non-claim

**AFR-N1 certification does not claim that the five unknown historical definitions were identified or tested.**

They remain explicit provenance debt in:

`docs/architecture/AFR_N1_ELEVEN_TERM_REGRESSION_SET_TRACEABILITY.json`

If the original source is later recovered, the manifest must be amended and any genuinely missing semantic coverage must be certified.

## Architecture verdict

AFR-N1 proves that the current architecture can support:

- source-governed standard definitions;
- valid-time versioning;
- immutable reference-never-mutate semantics;
- category isolation;
- exact alias resolution with fail-closed behavior;
- explicit false-synonym guards;
- separation of ontology meaning from product facts and applicability;
- mechanic-rich product implementations under shared product-neutral concepts.

No ontology rewrite, knowledge graph, vector-store redesign, database migration or product-specific reasoning branch is justified by AFR-N1 evidence.

## Fitness Review conclusion

The Architecture Fitness Review now has no remaining technical foundation blocker.

Combined evidence:

```text
AR-2.5  repository cleanup / succession          CERTIFIED
AR-3.0  hostile commercial Health pressure       CERTIFIED
AFR-N1  canonical ontology foundation            CERTIFIED
```

The historical five-identity provenance debt is retained but does not represent a runtime architecture defect.

The next milestone should return to the existing roadmap and expand Health as governed data using the architecture now proven under cleanup, hostile-product pressure and canonical-ontology certification. New architecture should be introduced only when new product pressure demonstrates a concrete representation or governance gap.
