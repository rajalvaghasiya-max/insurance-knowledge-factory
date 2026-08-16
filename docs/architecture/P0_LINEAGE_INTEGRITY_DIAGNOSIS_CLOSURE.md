# P0 — Lineage Integrity Diagnosis Closure

Status: **CLOSED PENDING MERGE**

## Purpose

P0 investigated whether the known Star Comprehensive copayment lineage
mis-binding was isolated, repeated across production construction sites, caused
by a shared construction contract, or accepted contrary to an existing
governance guard contract.

No factory, helper, validator, refactor, or new runtime architecture was
pre-authorized.

## Question A — Construction integrity

The repository-wide production census covered every explicit construction of
`source_artifact_sha256` and `governed_record_sha256` in the authoritative
`factory_core/` and `insurance_intelligence/` packages.

### Evidence `Lineage` construction sites

| Construction site | Source artifact classification | Governed record classification | Disposition |
|---|---|---|---|
| `insurance_intelligence/evidence/resolver.py` | Current document SHA, loaded from the governed canonical document version | Current binding-manifest file SHA, computed from bytes | Verified; unchanged |
| `insurance_intelligence/rule_certification/star_health.py` | Candidate-text SHA was used instead of the current policy-wording SHA | Candidate-text SHA was used instead of the binding-manifest SHA | Defect confirmed and corrected |
| `insurance_intelligence/rule_certification/star_health_room_rent.py` | Current policy-wording SHA | Candidate-text SHA was used instead of the source-registration SHA | Defect confirmed and corrected |
| `insurance_intelligence/rule_certification/star_health_bariatric_surgery.py` | Current policy-wording SHA | Candidate-text SHA was used instead of the source-registration SHA | Defect confirmed and corrected |
| `insurance_intelligence/rule_certification/aditya_birla_health.py` | Candidate-text SHA was used instead of the approved current policy-wording SHA | Candidate-text SHA was used instead of the governed policy-intelligence record SHA | Defect confirmed and corrected |

`insurance_intelligence/rule_certification/fixtures.py` is a synthetic reusable
test fixture and does not assert production artifact identity.

### Canonical `source_artifact_sha256` construction sites

The separate canonical-model field was also inspected:

- `generic_legal_condition_canonical_projection.py` binds derived assertions
  and publication decisions to the byte-computed binding-manifest SHA.
- `legacy_conditional_rule_adapter.py` binds canonical assertions to the
  byte-verified authoritative-rules artifact and publication decisions to the
  byte-verified publication receipt.

Both match their existing canonical contracts and were unchanged.

## Question B — Protection integrity

The governed Evidence Resolver verifies the binding-manifest SHA against the
canonical projection's recorded binding SHA and fails strict resolution on a
mismatch. That protection is functioning for resolver-produced lineage.

The product certification modules construct `EvidenceResolverOutput` directly
and do not pass through repository-backed evidence resolution. Their shared
`validate_output` contract validates structure, enumerated statuses, references,
and confidence. It does not promise to open artifact paths and prove that each
hash represents the semantic artifact type named by its field.

Therefore:

- the Star defect did not violate the documented resolver guard because the
  affected certification construction bypassed that resolver path;
- acceptance by structural output validation is not classified as a guard
  defect because semantic path-to-byte verification is outside that contract;
- independently resolver-produced records are not downgraded.

## Diagnosis and blast radius

Final classification:

**REPEATED CALL-SITE MISUSE**

Affected production paths: **4 certification construction modules**.

Unaffected production path: the shared registry-backed Evidence Resolver.

No shared runtime architecture defect was proven.

## Bounded repair

The four affected modules now use:

- approved/current document SHA values for `source_artifact_sha256`; and
- actual governed file SHA values for `governed_record_sha256`.

Existing certification assertions that encoded candidate-text hashes as
document or governed-record lineage were corrected. A repository-backed
regression test now recomputes governed-record hashes from the named files and
proves candidate-text hashes cannot occupy those fields in the affected cases.

## Certification

- Focused lineage and rule-certification suite: **44 passed**.
- Full repository regression: **2579 passed**.
- `git diff --check`: clean.

## Closure decision

P0 is closed by the smallest evidence-justified repair.

No lineage factory, new validation framework, broad refactor, or runtime
architecture gate is authorized by this diagnosis.

The next separate product milestone is HARM-1A: pressure the existing governed
pipeline to distinguish temporary waiting-period restriction, permanent
exclusion, conditional coverage, schedule dependency, and unresolved outcomes.
