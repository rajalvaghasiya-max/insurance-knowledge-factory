# PolicyScna Architecture Map

Status: C1 v1
Verified against: `593a5d2afb0ee4c9cdc564941ef9ff4e1a6478e7`

This map describes the authoritative architectural flow and the trust boundary at each stage. It is intentionally implementation-linked: every box should correspond to tracked code, governed artifacts, tests, or an explicitly classified gap.

## End-to-end flow

```text
INSURER / REGULATOR SOURCES
        │
        ▼
SOURCE DISCOVERY
agents/discovery_agent.py
        │
        ▼
SOURCE PRESERVATION
agents/preservation_agent.py
collectors/capture_engine.py
        │
        ├── raw HTML
        ├── visible text
        ├── screenshot
        └── capture metadata / hash
        │
        ▼
HTML SECTIONING
agents/html_section_agent.py
        │
        ├──────────────────────────────┐
        ▼                              ▼
PRODUCT SIGNALS                  PDF DISCOVERY
agents/product_signal_extractor.py   agents/pdf_intelligence/pdf_discovery_agent.py
        │                              │
        ▼                              ▼
PRODUCT CONSOLIDATION            PDF DOWNLOAD
agents/product_consolidation_agent.py agents/pdf_intelligence/pdf_download_agent.py
        │                              │
        ▼                              ├── raw immutable bytes
PRODUCT MASTER                        ├── PDF validation
knowledge_domains/product/...         ├── SHA-256
                                       └── PDF registry/version
                                              │
                                              ▼
                                    SOURCE REGISTRATION / CANDIDATES
                                    factory_core/canonical/*
                                              │
                                              ▼
                                   PRODUCT + DOCUMENT IDENTITY
                                   knowledge_domains/product/identity/*
                                   factory_core/governance/*identity*
                                              │
                                              ▼
                                    CURRENTNESS / REVALIDATION
                                    document_change_impact
                                    revalidation_work_queue
                                    document_currentness_evidence
                                    document_identity_resolution
                                              │
                                              ▼
                                  SEMANTIC EXTRACTION / BINDING
                                  knowledge_domains/health/*
                                  factory_core/canonical/*
                                              │
                                              ▼
                                    SEMANTIC CERTIFICATION
                                    insurance_intelligence/rule_certification/*
                                              │
                                              ▼
                                     CANONICAL FACTS / KNOWLEDGE
                                     health extraction primitives
                                              │
                                              ▼
                                    PUBLICATION ELIGIBILITY
                                    fact_publication_eligibility.py
                                              │
                               currentness/identity may BLOCK here
                                              │
                                              ▼
                                      APPROVED CONTENT / CLAIMS
                                              │
                                              ▼
                                    CONSTRAINED LLM VERBALIZER
                                    customer_document_intelligence/*
                                              │
                                              ▼
                                       DRAFT VALIDATION
                                              │
                                   approved ───┴─── blocked
                                      │
                                      ▼
                                 ANSWER DELIVERY
```

## Trust boundaries

### 1. Acquisition boundary

Captured pages, discovered PDFs, classifier outputs, extracted product names and UIN-like values are **evidence artifacts or candidates**, not insurance truth.

Current health:
- preservation works but deployment requirements need formalization;
- source-asset classifier is broken on clean `main` because its rules asset is missing;
- PDF acquisition needs generic hardening for protected endpoints;
- document classification accuracy needs fitness testing.

### 2. Identity/currentness boundary

Product and document identity are governed separately from extraction. Currentness evidence binds a dated official observation to an immutable registered version. Change-impact and revalidation work are advisory/candidate-only until reviewed governance establishes temporal state.

Important separation:

```text
revalidation queue != currentness decision
currentness evidence != temporal decision
identity overlay = reviewed temporal/document decision
```

### 3. Semantic boundary

Semantic binding/certification answers:

> “Does this governed representation faithfully capture the meaning of this document/version?”

It does **not** inherently answer:

> “Is this document version current for a present-tense product question?”

Historical documents can legitimately be semantically certified. Currentness belongs to evidence eligibility / publication / query-context governance.

Known defect to track: multiple certification builders currently hardcode `version_status="CURRENT_APPLICABLE"` rather than deriving that state from currentness governance or remaining temporal-neutral.

### 4. Publication boundary

`FactPublicationEligibilityContract` consumes identity/currentness state and blocks non-current or unresolved evidence from publication review. This is proven by the Bajaj v2 currentness regression test.

Semantic certification PASS therefore does not imply publication eligibility.

### 5. LLM boundary

The LLM is a **language-generation component only**. It must never become a source of insurance truth, product identity, currentness, entitlement, certification, or recommendation authority.

Current governed pilot flow:

```text
customer fact
  + concept understanding
  + route decision
  + approved content bundle
        ↓
constrained verbalizer request
        ↓
LLM draft
        ↓
draft validation
        ↓
approved for delivery OR not deliverable
```

The existing end-to-end implementation is deductible-specific. The architecture is reusable; broad concept coverage is not yet proven.

## Authority map

| Layer | May assert truth? | May block? | May generate prose? |
|---|---:|---:|---:|
| Discovery / capture | No | No | No |
| Source classifier / signals | No | Candidate filtering only | No |
| Source registration / lineage | Provenance only | Yes on invalid lineage | No |
| Product/document identity | Identity/temporal governance | Yes | No |
| Semantic binding/certification | Meaning of a governed version | Yes on unsupported/incomplete semantics | No |
| Publication eligibility | Eligibility for publication review | Yes | No |
| Approved content / answer claims | Permitted factual content | Yes | Limited structured text |
| LLM verbalizer | No new truth | Draft can be rejected | Yes |
| Draft validation | No new truth | Yes | No |
| Delivery | Only validated approved content | Yes | Presents final text |

## Current architecture gaps / repairs

1. Recover missing `registry/source_asset_classification_rules.json` or its genuine governed successor.
2. Add acquisition-plane clean-checkout fitness coverage.
3. Harden protected PDF retrieval generically while preserving identical byte validation, raw storage and SHA lineage.
4. Improve PDF document-role classification so valid lineage cannot attach to the wrong artifact role.
5. Reconnect acquisition document-change events to the existing revalidation machinery.
6. For current-product repeatability experiments, require resolved evidence identity/currentness before semantic reuse counts toward a current-product score.
7. Remove or derive unjustified `CURRENT_APPLICABLE` assertions in certification at an explicitly authorized milestone.
8. Keep generic copay shadow migration non-authoritative until executable parity coverage exists and a controlled authority switch is separately approved.

## Non-goals in the current phase

This map does not authorize Motor, Life, frontend, recommendation expansion, DB scaling, new agent families, or copay shadow authority migration.
