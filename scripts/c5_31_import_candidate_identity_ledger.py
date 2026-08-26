from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "evidence/c5_30_registry_enumeration_v2.txt"
LEDGER = ROOT / "docs/architecture/health_c5_31_candidate_identity_ledger.json"
MANIFEST = ROOT / "docs/architecture/health_c5_31_candidate_identity_ledger_manifest.json"
EXPECTED_COUNTS = {
    "cholamandalam": 77,
    "magma": 16,
    "navi": 35,
    "shriram": 22,
}
SOURCE_BLOB_SHA1 = "3c75e3e7197176094ab57e01b90ddb5c3684b741"
SOURCE_COMMIT_SHA = "57ea79f6de127e88d1bab384bdb35e7b7bf780c6"


def load_payload() -> dict:
    text = SOURCE.read_text(encoding="utf-8")
    begin = "C5_30_ENUMERATION_BEGIN\n"
    end = "\nC5_30_ENUMERATION_END"
    if begin not in text or end not in text:
        raise SystemExit("C5.31 source markers missing")
    body = text.split(begin, 1)[1].split(end, 1)[0]
    return json.loads(body)


def project_candidate(row: dict) -> dict:
    # Candidate identity ledger deliberately excludes raw URLs and target-semantic fields.
    allowed = {
        "approval_date",
        "financial_year",
        "insurer",
        "insurer_key",
        "product_name",
        "status",
        "type_of_product",
        "uin",
    }
    projected = {k: row.get(k, "") for k in sorted(allowed)}
    if any("url" in k.lower() for k in projected):
        raise SystemExit("C5.31 raw URL leaked into projected ledger")
    return projected


def canonical_bytes(doc: dict) -> bytes:
    return (json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def build() -> tuple[dict, dict]:
    payload = load_payload()
    if payload.get("candidate_count") != 150:
        raise SystemExit(f"C5.31 expected 150 source candidates, got {payload.get('candidate_count')}")
    candidates = [project_candidate(row) for row in payload["candidates"]]
    if len(candidates) != 150:
        raise SystemExit(f"C5.31 projected candidate count mismatch: {len(candidates)}")

    identity_keys = [
        (row["insurer_key"], row["uin"], row["product_name"])
        for row in candidates
    ]
    if len(set(identity_keys)) != 150:
        raise SystemExit("C5.31 duplicate governed candidate identity")

    counts = dict(sorted(Counter(row["insurer_key"] for row in candidates).items()))
    if counts != EXPECTED_COUNTS:
        raise SystemExit(f"C5.31 insurer distribution mismatch: {counts}")

    candidates.sort(key=lambda row: (row["insurer_key"], row["uin"], row["product_name"]))
    ledger = {
        "schema_version": "1.0",
        "record_type": "health_c5_31_candidate_identity_ledger",
        "record_status": "FROZEN_CANDIDATE_IDENTITY_LEDGER_PENDING_GREEN_MERGE",
        "source_evidence_commit_sha": SOURCE_COMMIT_SHA,
        "source_evidence_blob_sha1": SOURCE_BLOB_SHA1,
        "source_record_type": payload.get("record_type"),
        "candidate_count": 150,
        "target_counts": EXPECTED_COUNTS,
        "identity_key": ["insurer_key", "uin", "product_name"],
        "candidate_fields": sorted(candidates[0].keys()),
        "target_concepts_present": False,
        "raw_urls_present": False,
        "eligibility_adjudication_started": False,
        "selection_started": False,
        "semantic_review_started": False,
        "target_clause_reads": 0,
        "candidates": candidates,
    }
    ledger_bytes = canonical_bytes(ledger)
    ledger_sha256 = hashlib.sha256(ledger_bytes).hexdigest()
    manifest = {
        "schema_version": "1.0",
        "record_type": "health_c5_31_candidate_identity_ledger_manifest",
        "record_status": "FROZEN_LEDGER_HASH_PENDING_GREEN_MERGE",
        "ledger_path": str(LEDGER.relative_to(ROOT)),
        "canonicalization": "json_sort_keys_compact_utf8_single_trailing_newline",
        "ledger_sha256": ledger_sha256,
        "candidate_count": 150,
        "target_counts": EXPECTED_COUNTS,
        "source_evidence_blob_sha1": SOURCE_BLOB_SHA1,
        "eligibility_certification_authorized_after_green_merge": True,
        "product14_selection_authorized": False,
        "target_clause_reads_authorized": False,
    }
    return ledger, manifest


def main() -> int:
    ledger, manifest = build()
    LEDGER.write_bytes(canonical_bytes(ledger))
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"C5_31_LEDGER_PATH={LEDGER.relative_to(ROOT)}")
    print(f"C5_31_LEDGER_SHA256={manifest['ledger_sha256']}")
    print("C5_31_CANDIDATE_COUNT=150")
    print("C5_31_TARGET_COUNTS=cholamandalam:77,magma:16,navi:35,shriram:22")
    print("C5_31_ELIGIBILITY_ADJUDICATION_STARTED=false")
    print("C5_31_PRODUCT14_SELECTION_AUTHORIZED=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
