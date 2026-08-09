# MO-027 — Customer Decision Analysis — Closure

Status: CLOSED for the default governed A→H path

## Scope closed

MO-027 now provides a governed, education-first customer decision-analysis path above MO-026 product understanding. It supports personalization without converting the system into a product-ranking or recommendation engine.

Authoritative default chain:

MO-026 governed product understanding
→ MO-027A intent/personalization context boundary
→ MO-027B customer circumstance facts
→ MO-027C customer priorities and hard constraints
→ MO-027D governed circumstance-to-product applicability/relevance
→ MO-027E material question planning
→ MO-027F per-dimension customer alignment
→ MO-027F2 interaction decision units
→ MO-027G decision sufficiency and set adequacy
→ MO-027H set-relative education-first decision projection
→ USER DECIDES

## Closed capabilities

### MO-027A — Personalization context boundary
- Explicit PRODUCT_ONLY vs personalized context states.
- Customer context is prohibited in product-only turns.
- Personalized context is explicitly bound and cannot silently switch subjects.
- Product-only intent exits personalized context immediately.

### MO-027B/C — Customer context contracts
- Circumstances, priorities, and hard constraints are separate typed concepts.
- Provenance is preserved as DECLARED / INFERRED / CONFIRMED.
- Inferred values cannot silently drive material reasoning.
- Hard constraints remain explicit rules, not preference weights.

### MO-027D — Governed circumstance relevance
- Circumstances affect product applicability only through approved, published, versioned, evidence-backed rules.
- Default path rejects needs-analysis rules.
- Inferred facts require confirmation before deterministic use.

### MO-027E — Material question planner
- No generic missing-field questionnaire.
- Questions require traceable material triggers.
- Inferred facts/priorities are confirmed only when materially relevant.
- Duplicate target questions are suppressed and planning is bounded.

### MO-027F — Per-dimension alignment
- Alignment is local to one governed product dimension and one actionable customer priority.
- No cross-dimension aggregation.
- Protection-floor dimensions remain visible even without a declared priority.
- Unresolved product mechanics remain unresolved.

### MO-027F2 — Interaction decision units
- MATERIAL / CRITICAL MO-026 interactions form connected decision units.
- Coupled mechanics cannot be interpreted as independent benefit cards.
- Missing linked dimensions make interaction analysis explicitly incomplete.
- No claim-admissibility simulator or aggregate product verdict is introduced.

### MO-027G — Decision sufficiency / set adequacy
Possible governed outcomes include:
- DECISION_SUPPORT_READY
- DECISION_SUPPORT_READY_WITH_LIMITATIONS
- MORE_CUSTOMER_CONTEXT_REQUIRED
- BLOCKED_BY_PRODUCT_UNKNOWN
- BOTH_HAVE_MATERIAL_CONCERNS
- NEITHER_MEETS_HARD_CONSTRAINTS
- SET_MAY_BE_INADEQUATE

This gate evaluates whether decision support is safe to present; it does not choose a product.

### MO-027H — Education-first decision projection
- Preserves per-product alignments separately.
- Preserves protection floors, unresolved findings, interaction units, failed hard constraints, limitations, and blockers.
- Makes comparison-set scope explicit.
- Hard-codes the decision boundary: the projection does not choose a product; the user decides.
- No score, rank, winner, net lean, suitability conclusion, or recommendation field exists.

## Architectural laws certified

1. MO-027 may contextualize applicability/relevance of MO-026 facts; it may not modify, suppress, reinterpret, or invent the underlying product fact.
2. Customer preferences may never suppress a protection-floor fact.
3. A circumstance may change product applicability only through a governed circumstance-relevance rule with traceable evidence.
4. The default MO-027 path may never aggregate multiple local alignments into personalized net direction, lean, ranking, or winner.
5. Personal customer context may only participate while explicitly in personalized context and must not silently leak into product-only reasoning.
6. Needs-analysis judgments about what a customer should prioritize are outside the default path.

## Certification evidence

Focused MO-027 A→H adversarial certification: 73 passed.

Full repository regression after MO-027 completion: 2576 passed.

The adversarial suite verifies, among other invariants:
- product-only turns cannot reuse prior personalized health context;
- inferred priorities/facts cannot drive material reasoning before confirmation;
- protection floors survive into final projection;
- unresolved product facts force action-required handling;
- two products failing hard constraints cannot produce a least-bad winner;
- set inadequacy remains explicit;
- verdict/scoring/recommendation fields are absent;
- soft-verdict boundary language such as “leans toward Product B” is rejected.

## Explicitly deferred behind governance/compliance gates

### MO-027N — Needs-Analysis Judgment
Question: what should this customer prioritize given age, health, finances, and other circumstances?

Deferred because this is a normative needs-analysis function. It requires governed circumstance→priority evidence, versioned decision policy, auditability, and compliance review. It must not be approximated by heuristic LLM inference.

### MO-027R — Product Recommendation / Net Direction
Question: which product should this customer buy?

Deferred because it requires explicit user request, legal/compliance sign-off, governed combination/decision policy, retained reasons, auditability, set-scope controls, and no hidden weighting. It is not part of the default MO-027 closure.

## Closure decision

MO-027 is CLOSED for the default governed customer decision-analysis capability. Further work on needs-analysis or recommendation is a separate governed/compliance milestone, not unfinished work within the closed A→H path.
