from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
PASS2_PATH = ROOT / "docs/architecture/health_c5_33_registry_domain_eligibility_pass2.json"
BASE = "https://irdai.gov.in/non-life-insurance-products"
DELTA = 60
EXPECTED_PASS2_GIT_BLOB_SHA1 = "8e5616f6e5ec53d0a0ee0757040e16dfee369ca3"


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def parse_rows(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict] = []
    for tr in soup.find_all("tr"):
        cells = [norm(" ".join(td.stripped_strings)) for td in tr.find_all(["td", "th"])]
        if not cells or any("Name of the Insurer" in c for c in cells):
            continue
        status_idx = next((i for i, c in enumerate(cells) if c in {"Non-Archived", "Archived"}), None)
        if status_idx is None:
            continue
        # Non-Life register columns after status are: S.no, Financial Year, Insurer,
        # Product Name, Type Of Product, UIN, Date of Approval, Documents.
        tail = cells[status_idx:]
        if len(tail) < 8:
            continue
        rows.append({
            "archive_status": tail[0],
            "serial_no": tail[1],
            "financial_year": tail[2],
            "insurer": tail[3],
            "product_name": tail[4],
            "type_of_product": tail[5],
            "uin": tail[6],
            "approval_date": tail[7],
        })
    return rows


def fetch_page(cur: int) -> tuple[list[dict], str]:
    params = {
        "p_p_id": "com_irdai_document_media_IRDAIDocumentMediaPortlet",
        "p_p_lifecycle": "0",
        "p_p_state": "normal",
        "p_p_mode": "view",
        "_com_irdai_document_media_IRDAIDocumentMediaPortlet_cur": str(cur),
        "_com_irdai_document_media_IRDAIDocumentMediaPortlet_delta": str(DELTA),
        "_com_irdai_document_media_IRDAIDocumentMediaPortlet_resetCur": "false",
    }
    r = requests.get(BASE, params=params, timeout=30, headers={"User-Agent": "PolicyScna-C5.35/1.0"})
    r.raise_for_status()
    return parse_rows(r.text), r.url


def main() -> int:
    if git_blob_sha1(PASS2_PATH) != EXPECTED_PASS2_GIT_BLOB_SHA1:
        raise SystemExit("C5_35_ABORT_PASS2_BLOB_HASH_MISMATCH")

    pass2 = json.loads(PASS2_PATH.read_text(encoding="utf-8"))
    pending = [r for r in pass2["adjudications"] if r["status"] == "PENDING_EVIDENCE"]
    if len(pending) != 131:
        raise SystemExit(f"C5_35_ABORT_PENDING_COUNT_{len(pending)}")

    pending_by_uin: dict[str, list[dict]] = defaultdict(list)
    for row in pending:
        uin = norm(row["identity"]["uin"])
        if not uin:
            raise SystemExit("C5_35_ABORT_EMPTY_PENDING_UIN")
        pending_by_uin[uin].append(row)

    page_fingerprints: set[str] = set()
    page_audit: list[dict] = []
    matches: dict[str, list[dict]] = defaultdict(list)
    terminal_reason = None

    for cur in range(1, 201):
        rows, url = fetch_page(cur)
        fp = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if fp in page_fingerprints:
            print("C5_35_ABORT_REPEATED_PAGE_FINGERPRINT", file=sys.stderr)
            return 3
        page_fingerprints.add(fp)
        terminal = len(rows) < DELTA
        page_audit.append({"cur": cur, "row_count": len(rows), "sha256": fp, "terminal": terminal})

        for row in rows:
            if row["uin"] in pending_by_uin:
                matches[row["uin"]].append(row)

        if terminal:
            terminal_reason = "ROW_COUNT_BELOW_REQUESTED_DELTA"
            break
    else:
        print("C5_35_ABORT_NO_TERMINAL_PAGE", file=sys.stderr)
        return 4

    capture = []
    for source_row in pending:
        identity = source_row["identity"]
        uin = norm(identity["uin"])
        exact = matches.get(uin, [])
        if not exact:
            query_status = "NO_MATCH"
            ambiguity = "UNRESOLVED"
            matched_uin = None
            structured_type = None
        elif len(exact) == 1:
            query_status = "EXACT_MATCH"
            ambiguity = "NONE"
            matched_uin = exact[0]["uin"]
            structured_type = exact[0]["type_of_product"]
        else:
            query_status = "MULTIPLE_EXACT_MATCHES"
            ambiguity = "CONFLICT"
            matched_uin = uin
            structured_type = sorted({r["type_of_product"] for r in exact})

        evidence_projection = {
            "uin": uin,
            "match_count": len(exact),
            "matches": [
                {
                    "uin": r["uin"],
                    "type_of_product": r["type_of_product"],
                    "archive_status": r["archive_status"],
                    "serial_no": r["serial_no"],
                }
                for r in exact
            ],
        }
        snapshot_hash = hashlib.sha256(
            json.dumps(evidence_projection, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        identity_ref = hashlib.sha256(
            f"{identity['insurer_key']}|{uin}|{identity['product_name']}".encode()
        ).hexdigest()
        capture.append({
            "candidate_identity_ref": f"candidate_sha256:{identity_ref}",
            "uin": uin,
            "query_status": query_status,
            "match_count": len(exact),
            "matched_uin": matched_uin,
            "structured_type_of_product": structured_type,
            "authority_scope": "IRDAI_NON_LIFE_INSURANCE_PRODUCTS_STRUCTURED_REGISTER",
            "source_ref": BASE,
            "source_content_hash_or_snapshot_hash": snapshot_hash,
            "ambiguity_conflict_status": ambiguity,
        })

    capture.sort(key=lambda r: r["candidate_identity_ref"])
    status_counts = defaultdict(int)
    type_counts = defaultdict(int)
    for row in capture:
        status_counts[row["query_status"]] += 1
        if row["query_status"] == "EXACT_MATCH":
            type_counts[norm(str(row["structured_type_of_product"])) or "<blank>"] += 1

    payload = {
        "schema_version": "1.0",
        "record_type": "health_c5_35_disposable_object_type_evidence_capture",
        "source": BASE,
        "source_predecessor_git_blob_sha1": EXPECTED_PASS2_GIT_BLOB_SHA1,
        "candidate_count": 131,
        "requested_page_delta": DELTA,
        "pages_scanned": len(page_audit),
        "terminal_reason": terminal_reason,
        "terminal_page": page_audit[-1]["cur"],
        "terminal_page_row_count": page_audit[-1]["row_count"],
        "page_audit": page_audit,
        "query_status_counts": dict(sorted(status_counts.items())),
        "exact_match_type_counts": dict(sorted(type_counts.items())),
        "capture_records": capture,
        "all_131_processed": len(capture) == 131,
        "adjudication_started": False,
        "candidate_status_changes": 0,
        "product14_selection_authorized": False,
        "selection_started": False,
        "semantic_review_started": False,
        "target_clause_reads": 0,
    }
    print("C5_35_OBJECT_TYPE_CAPTURE_BEGIN")
    print(json.dumps(payload, indent=2, sort_keys=True))
    print("C5_35_OBJECT_TYPE_CAPTURE_END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
