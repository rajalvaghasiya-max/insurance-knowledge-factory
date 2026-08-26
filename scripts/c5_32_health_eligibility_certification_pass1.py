from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "docs/architecture/health_c5_31_candidate_identity_ledger.json"
OUT_PATH = ROOT / "docs/architecture/health_c5_32_registry_decidable_eligibility_pass1.json"

EXPECTED_LEDGER_SHA256 = "cec7620abde012982844beb212892db13cdf509177fc4d5fae9145d752f8a0a2"
EXPECTED_COUNTS = {"cholamandalam": 77, "magma": 16, "navi": 35, "shriram": 22}


def canonical_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def attest(predicate_id: str, normalized_value: str, decision: str, ambiguity: str) -> dict:
    return {
        "predicate_id": predicate_id,
        "normalized_value": normalized_value,
        "authority_scope": "IRDAI_STRUCTURED_HEALTH_PRODUCT_REGISTER",
        "source_ref": "docs/architecture/health_c5_31_candidate_identity_ledger.json",
        "source_content_hash": EXPECTED_LEDGER_SHA256,
        "certification_decision": decision,
        "ambiguity_conflict_status": ambiguity,
    }


def main() -> int:
    if canonical_sha256(LEDGER_PATH) != EXPECTED_LEDGER_SHA256:
        raise SystemExit("C5_32_ABORT_LEDGER_HASH_MISMATCH")

    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    candidates = ledger["candidates"]
    if len(candidates) != 150:
        raise SystemExit("C5_32_ABORT_CANDIDATE_COUNT_MISMATCH")

    counts = Counter(row["insurer_key"] for row in candidates)
    if dict(counts) != EXPECTED_COUNTS:
        raise SystemExit("C5_32_ABORT_INSURER_COUNT_MISMATCH")

    adjudications = []
    for row in candidates:
        atts = [
            attest(
                "exact_identity",
                "EXACT_PRODUCT_NAME_AND_UIN_OR_EQUIVALENT_REGULATOR_IDENTITY_RESOLVED",
                "PASS",
                "NONE",
            ),
            attest(
                "issuer_authority",
                "AUTHORIZED_GENERAL_OR_HEALTH_INSURER",
                "PASS",
                "NONE",
            ),
        ]

        # C5.32 Pass 1 is deliberately conservative. The only final rejection made from
        # the frozen registry row alone is an explicit structured Group classification,
        # which contradicts the stipulated INDIVIDUAL/FAMILY_FLOATER/BOTH population.
        if row.get("type_of_product", "").strip().casefold() == "group":
            atts.append(attest("coverage_arrangement", "GROUP", "FAIL", "NONE"))
            status = "INELIGIBLE_FAIL_CLOSED"
            decisive_predicate = "coverage_arrangement"
        else:
            structured_type = row.get("type_of_product", "").strip()
            if structured_type.casefold() == "individual":
                atts.append(attest("coverage_arrangement", "INDIVIDUAL", "PASS", "NONE"))
            else:
                atts.append(attest("coverage_arrangement", "UNKNOWN", "PENDING_EVIDENCE", "UNRESOLVED"))
            status = "PENDING_EVIDENCE"
            decisive_predicate = None

        for pid in ("domain", "benefit_basis", "insurance_object_type", "current_offering"):
            atts.append(attest(pid, "UNKNOWN", "PENDING_EVIDENCE", "UNRESOLVED"))

        adjudications.append(
            {
                "identity": {
                    "insurer_key": row["insurer_key"],
                    "uin": row["uin"],
                    "product_name": row["product_name"],
                },
                "registry_type_of_product": row.get("type_of_product", ""),
                "status": status,
                "decisive_predicate": decisive_predicate,
                "predicate_attestations": atts,
            }
        )

    status_counts = Counter(row["status"] for row in adjudications)
    payload = {
        "schema_version": "1.0",
        "record_type": "health_c5_32_registry_decidable_eligibility_pass1",
        "record_status": "GENERATED_PENDING_GREEN_FREEZE",
        "source_ledger_path": str(LEDGER_PATH.relative_to(ROOT)),
        "source_ledger_sha256": EXPECTED_LEDGER_SHA256,
        "candidate_count": 150,
        "insurer_counts": EXPECTED_COUNTS,
        "pass_scope": "REGISTRY_DECIDABLE_NON_TARGET_PREDICATES_ONLY",
        "decision_policy": {
            "final_rejection_rule": "Only an explicit structured IRDAI Type Of Product value of Group is sufficient in pass 1 to fail coverage_arrangement against the frozen INDIVIDUAL/FAMILY_FLOATER/BOTH experiment population.",
            "individual_rule": "An explicit structured Individual value may pass coverage_arrangement only; it does not establish domain, benefit_basis, insurance_object_type, or current_offering.",
            "forbidden_inferences": [
                "infer regulatory benefit basis from product name",
                "infer domain from marketing words or UIN pattern",
                "infer main-product status from absence of Add On text",
                "infer current offering solely from historical approval date",
                "infer family-floater eligibility from marketing language unless a separately governed source establishes it",
                "read copayment or waiting-period terms",
            ],
        },
        "status_counts": dict(sorted(status_counts.items())),
        "adjudications": adjudications,
        "all_150_processed": len(adjudications) == 150,
        "final_universe_frozen": False,
        "eligible_candidate_count": None,
        "product14_selection_authorized": False,
        "selection_started": False,
        "semantic_review_started": False,
        "target_clause_reads": 0,
        "next_step": "RESOLVE_PENDING_NON_TARGET_PREDICATES_WITH_GOVERNED_EVIDENCE_ONLY",
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"C5_32_CANDIDATE_COUNT={len(adjudications)}")
    print(f"C5_32_INELIGIBLE_FAIL_CLOSED={status_counts.get('INELIGIBLE_FAIL_CLOSED', 0)}")
    print(f"C5_32_PENDING_EVIDENCE={status_counts.get('PENDING_EVIDENCE', 0)}")
    print("C5_32_PRODUCT14_SELECTION_AUTHORIZED=false")
    print("C5_32_TARGET_CLAUSE_READS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
