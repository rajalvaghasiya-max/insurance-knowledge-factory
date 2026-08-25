# PolicyScna Capability Registry

Status: C1 v1 — repository memory baseline
Verified against: `593a5d2afb0ee4c9cdc564941ef9ff4e1a6478e7`

This registry is the first place to check before proposing or building a capability. Chat history is not authoritative project memory; tracked code, tests, governed artifacts and this registry are.

## Status vocabulary

- `ACTIVE_AND_PROVEN` — implemented, wired to an authoritative path, and covered by executable tests.
- `ACTIVE_BUT_UNVERIFIED` — implemented and architecturally valid, but coverage or live fitness is incomplete.
- `PARTIALLY_OPERATIONAL` — implemented and usable in part, with a known operational defect.
- `BROKEN` — clean-checkout execution currently fails.
- `DISCONNECTED` — useful implementation exists but is not wired into the relevant authoritative path.
- `LEGACY` / `SUPERSEDED` — historical implementation; do not use for new architecture unless explicitly recovering behavior.

## Action vocabulary

`REUSE`, `WIRE`, `REPAIR`, `EXTEND`, `DO_NOT_TOUCH`, `LEGACY_ONLY`.

## Capability inventory

| Capability | Plane | Primary implementation / runner | Authority / output | Status | Action | Known issue |
|---|---|---|---|---|---|---|
| URL/source discovery | Acquisition | `agents/discovery_agent.py`; `scripts/run_source_discovery` | Candidate URL queue | ACTIVE_BUT_UNVERIFIED | REUSE | Needs explicit CI fitness coverage |
| Web preservation | Acquisition | `agents/preservation_agent.py`, `agents/queue_capture_agent.py`, `collectors/capture_engine.py` | Raw HTML, visible text, screenshot, metadata/hash | PARTIALLY_OPERATIONAL | REPAIR | Visible-browser fallback requires declared X display/Xvfb environment |
| HTML sectioning | Acquisition | `agents/html_section_agent.py`; `scripts/run_html_sectioning` | Parsed HTML sections | ACTIVE_BUT_UNVERIFIED | REUSE | Acquisition-level regression coverage incomplete |
| PDF discovery | Acquisition | `agents/pdf_intelligence/pdf_discovery_agent.py`; `scripts/run_pdf_discovery` | PDF candidate queue + document-type candidates | PARTIALLY_OPERATIONAL | REPAIR | ICICI smoke exposed incorrect policy-wording classification / missed desired document |
| PDF download + binary validation + hash registry | Acquisition | `agents/pdf_intelligence/pdf_download_agent.py`; `scripts/run_pdf_download` | Raw PDF bytes, SHA-256, registry versions | PARTIALLY_OPERATIONAL | REPAIR | Protected insurer/regulator endpoints can return 403/504; browser transport must retain identical validation gate |
| Source asset classification | Acquisition | `agents/source_asset_classifier.py` | Governed source-asset class | BROKEN | REPAIR | `registry/source_asset_classification_rules.json` absent from clean `main`; constructor fails closed |
| Product signal extraction | Acquisition / Product | `agents/product_signal_extractor.py`; `scripts/run_product_signal_extraction` | Candidate product/UIN/topic signals | BROKEN | REPAIR | Transitively fails because SourceAssetClassifier cannot load rules asset |
| UIN candidate extraction | Acquisition / Identity | `agents/uin_candidate_extractor.py` | UIN candidates | ACTIVE_BUT_UNVERIFIED | REUSE | Must remain candidate-only until governed identity resolution |
| Product consolidation | Product | `agents/product_consolidation_agent.py`; `scripts/run_product_consolidation` | Draft/canonical Product Master records | ACTIVE_BUT_UNVERIFIED | REUSE | Depends on healthy product-signal input |
| Product Master index | Product | `knowledge_domains/product/product_master/_product_master_index.json` | Product inventory data asset | ACTIVE | REUSE | Historical generated content may not imply currentness |
| Product quality reporting | Operator | `product_quality_report.py` and product-consolidation reporting surface | Product quality / enrichment recommendation | ACTIVE_BUT_UNVERIFIED | WIRE | Overlapping report implementations require canonical selection before unified status CLI |
| Product identity resolution | Governance | `knowledge_domains/product/identity/product_identity_resolver.py`; `factory_core/governance/product_identity_reference.py` | Governed product identity | ACTIVE | REUSE | Must remain distinct from candidate extraction |
| Source-product linkage | Governance | `knowledge_domains/product/identity/source_product_linkage.py` | Governed document/product linkage | ACTIVE_BUT_UNVERIFIED | REUSE | Important input to change-impact/revalidation |
| Document change impact | Governance / Revalidation | `knowledge_domains/product/identity/document_change_impact.py` | Candidate-only revalidation work | ACTIVE_BUT_UNVERIFIED | WIRE | Writes advisory candidate artifacts; does not gate certification |
| Revalidation work queue | Governance / Revalidation | `knowledge_domains/product/identity/revalidation_work_queue.py`; `scripts/run_revalidation_work_queue.py` | Durable pending/in-progress/resolved/dismissed work | ACTIVE_BUT_UNVERIFIED | WIRE | Depends on acquisition/download events; advisory to certification |
| Document currentness evidence | Governance | `factory_core/governance/document_currentness_evidence.py`; runner | Hash-bound dated official currentness evidence | ACTIVE | REUSE | Evidence-only by design; does not itself decide temporal status |
| Document identity/currentness resolution | Governance | `factory_core/governance/document_identity_resolution.py` | Reviewed temporal/document identity overlay | ACTIVE | REUSE | `current_observed_reviewed` requires structured currentness evidence |
| Canonical fact materialization | Knowledge | `knowledge_domains/health/extraction_primitives/canonical_fact_materialization.py` | Immutable canonical facts | ACTIVE_AND_PROVEN | DO_NOT_TOUCH | Must remain downstream of governed selection/review |
| Fact publication eligibility | Governance / Publication | `knowledge_domains/health/extraction_primitives/fact_publication_eligibility.py` | eligible/blocked/deferred publication-review assessment | ACTIVE_AND_PROVEN | DO_NOT_TOUCH | Correctly blocks non-current temporal states; does not publish itself |
| Currentness publication gate | Governance / Publication | same as above; regression `tests/health/test_bajaj_v2_currentness_publication_gate.py` | Currentness-aware blocking | ACTIVE_AND_PROVEN | DO_NOT_TOUCH | Gates publication review, not semantic certification |
| Waiting-period semantics/binding | Semantic | `factory_core/canonical/waiting_period_binding.py`; `knowledge_domains/health/waiting_period_timeline/` | Typed waiting-period mechanic | ACTIVE_AND_PROVEN | REUSE | Relationship/precedence variants may still expose representation gaps |
| Waiting-period certification | Certification | `insurance_intelligence/rule_certification/waiting_period.py` | Semantic certification result | ACTIVE_AND_PROVEN | REUSE | Certifier currently asserts `version_status="CURRENT_APPLICABLE"`; currentness is not derived here |
| Conditional copayment certification | Certification | `insurance_intelligence/rule_certification/conditional_copayment.py` | Semantic certification result | ACTIVE_AND_PROVEN | REUSE | Conditional path requires genuine trigger semantics |
| Copayment multispan certification | Certification | `insurance_intelligence/rule_certification/copayment_multispan.py` | Certified multispan copay semantics | ACTIVE_AND_PROVEN | REUSE | Keep distinct from policy-wide fixed copay representation gap |
| Copayment nonapplication | Certification | `insurance_intelligence/rule_certification/copayment_nonapplication.py` | Certified no-copay/nonapplication semantics | ACTIVE_AND_PROVEN | REUSE | No change authorized |
| Copay additive/composition semantics | Semantic | `insurance_intelligence/benefits/copayment_composition.py` | Composition semantics | ACTIVE_AND_PROVEN | REUSE | HC-1.2 foundation; do not reopen without falsification |
| Generic copay shadow migration | Migration / Shadow | `CopayFragmentAdapter` → assembler → parity harness → shadow publisher/runners | Non-authoritative parity/migration artifacts | ACTIVE_BUT_UNVERIFIED | WIRE_BEFORE_AUTHORITY_SWITCH | Entire shadow chain has no executable test coverage; do not merge into production path now |
| Rule certification runner/contracts | Certification | `insurance_intelligence/rule_certification/runner.py`; `insurance_intelligence/contracts/rule_certification.py` | PASS/FAIL/BLOCKED semantic certification | ACTIVE_AND_PROVEN | DO_NOT_TOUCH except earned defect | Currentness/revalidation is not an input; semantic certification is document-version-specific, not a currentness gate |
| Constrained LLM verbalization | Answer generation | `knowledge_domains/health/customer_document_intelligence/constrained_llm_verbalizer.py`; `scripts/run_constrained_llm_verbalizer.py` | Non-authoritative verbalized draft | ACTIVE_BUT_UNVERIFIED | REUSE | Pilot is concept-bounded; LLM draft is never source of truth or publishable by itself |
| Governed customer answer pilot | Answer generation | `knowledge_domains/health/customer_document_intelligence/end_to_end_answer_pipeline.py` | Validated delivery artifact | IMPLEMENTED_PILOT | WIRE / EXTEND LATER | Current end-to-end implementation is deductible-specific; broader concept coverage not yet proven |
| Draft validation before delivery | Answer governance | `knowledge_domains/health/customer_document_intelligence/draft_validation.py` | approved/not-deliverable validation | ACTIVE_BUT_UNVERIFIED | REUSE | Required boundary after LLM verbalization |
| Customer-document answer routing/content bundle | Answer reasoning | `answer_route_decision.py`, `approved_content_bundle.py`, `interpretation_packet.py`, understanding matchers | Governed allowed-content packet | ACTIVE_BUT_UNVERIFIED | REUSE | Preserve rule: renderer/verbalizer may reword permitted content, not invent truth |
| PDF benchmark / parse diagnostics | Diagnostics | `knowledge_domains/health/benchmark/`, `knowledge_domains/health/batch/` | Quality/audit reports | ACTIVE_BUT_UNVERIFIED | REUSE | Diagnostic plane, not authority plane |
| Legacy `factory_sdk` / `knowledge_factory` paths | Legacy | `factory_sdk/`, `knowledge_factory/` | Historical capabilities | LEGACY | LEGACY_ONLY | Authoritative core remains quarantined from these surfaces |

## Cross-cutting architectural findings from C0

1. **Lineage integrity, evidence eligibility/currentness, and semantic integrity are different guarantees.** Exact bytes and hashes prove provenance, not that the artifact is the right/current evidence for a present-tense question.
2. **Currentness architecture already exists.** Change detection/revalidation is advisory; document identity/currentness is governed; publication eligibility is currentness-gating.
3. **Semantic certification is intentionally/currently currentness-blind.** Historical documents can be semantically understood. The defect to track is that certifiers hardcode `CURRENT_APPLICABLE` rather than deriving or remaining temporal-neutral.
4. **Product #7 exposed an experiment-scoring/current-evidence eligibility defect, not absence of currentness architecture.** A current-product repeatability result must not count semantic certification of a superseded artifact as current-product proof.
5. **LLM remains part of the answer architecture only.** It verbalizes governed content, then draft validation decides whether anything is deliverable. It is prohibited from becoming insurance truth, entitlement or recommendation authority.
6. **Acquisition is the weakest operational plane.** Core knowledge/certification is substantially better tested than source acquisition and classification.
7. **Do not activate the generic copay shadow migration during the current Health repeatability milestone.** It is a future controlled authority switch and must first gain executable parity coverage.

## Mandatory pre-build check

Before significant new code is proposed, classify the requested capability using this order:

1. Does implementation already exist?
2. Does a contract/registry already exist?
3. Does a historical/disconnected implementation exist?
4. Is the right action `REUSE`, `WIRE`, `REPAIR`, `EXTEND`, `REPLACE`, or genuinely `NEW`?

`NEW` is the last classification, not the default.
