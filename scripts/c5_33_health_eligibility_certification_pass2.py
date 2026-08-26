from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASS1_PATH = ROOT / "docs/architecture/health_c5_32_registry_decidable_eligibility_pass1.json"
OUT_PATH = ROOT / "docs/architecture/health_c5_33_registry_domain_eligibility_pass2.json"

EXPECTED_PASS1_GIT_BLOB_SHA1 = "44c3614993da168e4808b2f603527f55c0b3d43e"
EXPECTED_LEDGER_SHA256 = "cec7620abde012982844beb212892db13cdf509177fc4d5fae9145d752f8a0a2"
EXPECTED_COUNTS = {"cholamandalam": 77, "magma": 16, "navi": 35, "shriram": 22}
EXPECTED_PASS1_STATUS_COUNTS = {"INELIGIBLE_FAIL_CLOSED": 19, "PENDING_EVIDENCE": 131}


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def domain_attestation() -> dict:
    return {
        "predicate_id": "domain",
        "normalized_value": "HEALTH",
        "authority_scope": "IRDAI_STRUCTURED_HEALTH_PRODUCT_REGISTER",
        "source_ref": "docs/architecture/health_c5_31_candidate_identity_ledger.json",
        "source_content_hash": EXPECTED_LEDGER_SHA256,
        "certification_decision": "PASS",
        "ambiguity_conflict_status": "NONE",
    }


def main() -> int:
    if git_blob_sha1(PASS1_PATH) != EXPECTED_PASS1_GIT_BLOB_SHA1:
        raise SystemExit("C5_33_ABORT_PASS1_BLOB_HASH_MISMATCH")

    pass1 = json.loads(PASS1_PATH.read_text(encoding="utf-8"))
    if pass1.get("source_ledger_sha256") != EXPECTED_LEDGER_SHA256:
        raise SystemExit("C5_33_ABORT_LEDGER_HASH_MISMATCH")
    if pass1.get("candidate_count") != 150 or pass1.get("all_150_processed") is not True:
        raise SystemExit("C5_33_ABORT_CANDIDATE_SET_MISMATCH")
    if pass1.get("insurer_counts") != EXPECTED_COUNTS:
        raise SystemExit("C5_33_ABORT_INSURER_COUNT_MISMATCH")
    if pass1.get("status_counts") != EXPECTED_PASS1_STATUS_COUNTS:
        raise SystemExit("C5_33_ABORT_PASS1_STATUS_MISMATCH")
    if pass1.get("target_clause_reads") != 0 or pass1.get("selection_started") is not False:
        raise SystemExit("C5_33_ABORT_PRESELECTION_INTEGRITY_MISMATCH")

    adjudications = []
    for row in pass1["adjudications"]:
        copied = json.loads(json.dumps(row))
        attestations = copied["predicate_attestations"]
        domain_positions = [i for i, att in enumerate(attestations) if att["predicate_id"] == "domain"]
        if len(domain_positions) != 1:
            raise SystemExit("C5_33_ABORT_DOMAIN_ATTESTATION_CARDINALITY")

        prior_domain = attestations[domain_positions[0]]
        if (
            prior_domain.get("normalized_value") != "UNKNOWN"
            or prior_domain.get("certification_decision") != "PENDING_EVIDENCE"
        ):
            raise SystemExit("C5_33_ABORT_UNEXPECTED_PRIOR_DOMAIN_STATE")

        attestations[domain_positions[0]] = domain_attestation()

        # Pass 2 resolves exactly one frozen predicate. It deliberately does not
        # reinterpret Non-Archived as CURRENTLY_OFFERED, infer indemnity/main-product
        # status from names or UINs, or touch target semantics.
        copied["status"] = row["status"]
        copied["decisive_predicate"] = row.get("decisive_predicate")
        adjudications.append(copied)

    status_counts = Counter(row["status"] for row in adjudications)
    if dict(status_counts) != EXPECTED_PASS1_STATUS_COUNTS:
        raise SystemExit("C5_33_ABORT_STATUS_DRIFT")

    pending_rows = [row for row in adjudications if row["status"] == "PENDING_EVIDENCE"]
    for row in pending_rows:
        by_id = {att["predicate_id"]: att for att in row["predicate_attestations"]}
        if by_id["domain"]["certification_decision"] != "PASS":
            raise SystemExit("C5_33_ABORT_DOMAIN_NOT_ESTABLISHED")
        if by_id["current_offering"]["certification_decision"] != "PENDING_EVIDENCE":
            raise SystemExit("C5_33_ABORT_CURRENT_OFFERING_OVERREACH")
        if by_id["benefit_basis"]["certification_decision"] != "PENDING_EVIDENCE":
            raise SystemExit("C5_33_ABORT_BENEFIT_BASIS_OVERREACH")
        if by_id["insurance_object_type"]["certification_decision"] != "PENDING_EVIDENCE":
            raise SystemExit("C5_33_ABORT_OBJECT_TYPE_OVERREACH")

    payload = {
        "schema_version": "1.0",
        "record_type": "health_c5_33_registry_domain_eligibility_pass2",
        "record_status": "GENERATED_PENDING_GREEN_FREEZE",
        "source_pass1_path": str(PASS1_PATH.relative_to(ROOT)),
        "source_pass1_git_blob_sha1": EXPECTED_PASS1_GIT_BLOB_SHA1,
        "source_ledger_sha256": EXPECTED_LEDGER_SHA256,
        "candidate_count": 150,
        "insurer_counts": EXPECTED_COUNTS,
        "pass_scope": "IRDAI_HEALTH_REGISTER_DOMAIN_PREDICATE_ONLY",
        "decision_policy": {
            "domain_rule": "C5.31 candidates were exhaustively enumerated from the official IRDAI Health Products register under the frozen C5.29 Health candidate-pool derivation rule; that bounded regulator provenance establishes domain=HEALTH for every ledger candidate.",
            "current_offering_rule": "Do not equate registry Non-Archived status with the stricter frozen predicate CURRENTLY_OFFERED without separate governed evidence of current offering.",
            "preserved_from_pass1": "Explicit Group rows remain INELIGIBLE_FAIL_CLOSED; all other rows remain PENDING_EVIDENCE until every frozen required predicate is positively established.",
            "forbidden_inferences": [
                "infer benefit basis from product name, UIN, or domain",
                "infer main-product status from absence of Add On text",
                "infer currently offered solely from Non-Archived registry status",
                "infer family-floater eligibility from product name or marketing language",
                "read copayment or waiting-period terms",
                "use semantic complexity or expected repeatability outcome",
            ],
        },
        "resolved_in_this_pass": ["domain"],
        "explicitly_not_resolved_in_this_pass": [
            "benefit_basis",
            "insurance_object_type",
            "current_offering",
        ],
        "status_counts": dict(sorted(status_counts.items())),
        "adjudications": adjudications,
        "all_150_processed": len(adjudications) == 150,
        "pending_candidate_count": len(pending_rows),
        "final_universe_frozen": False,
        "eligible_candidate_count": None,
        "product14_selection_authorized": False,
        "selection_started": False,
        "semantic_review_started": False,
        "target_clause_reads": 0,
        "next_step": "RESOLVE_REMAINING_PENDING_NON_TARGET_PREDICATES_WITH_GOVERNED_EVIDENCE_ONLY",
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("C5_33_DOMAIN_PASS=150")
    print(f"C5_33_INELIGIBLE_FAIL_CLOSED={status_counts.get('INELIGIBLE_FAIL_CLOSED', 0)}")
    print(f"C5_33_PENDING_EVIDENCE={status_counts.get('PENDING_EVIDENCE', 0)}")
    print("C5_33_CURRENT_OFFERING_FROM_NON_ARCHIVED=false")
    print("C5_33_PRODUCT14_SELECTION_AUTHORIZED=false")
    print("C5_33_TARGET_CLAUSE_READS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
