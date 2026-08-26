from __future__ import annotations

import hashlib
import json
import re
import sys
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://irdai.gov.in/health-insurance-products"
DELTA = 60
TARGETS = {
    "cholamandalam": ["cholamandalam ms general insurance"],
    "magma": ["magma hdi general insurance", "magma general insurance"],
    "navi": ["navi general insurance"],
    "shriram": ["shriram general insurance"],
}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def target_key(insurer: str) -> str | None:
    n = norm(insurer)
    for key, aliases in TARGETS.items():
        if any(alias in n for alias in aliases):
            return key
    return None


def fetch_page(cur: int, delta: int = DELTA) -> tuple[list[dict], str]:
    params = {
        "p_p_id": "com_irdai_document_media_IRDAIDocumentMediaPortlet",
        "p_p_lifecycle": "0",
        "p_p_state": "normal",
        "p_p_mode": "view",
        "_com_irdai_document_media_IRDAIDocumentMediaPortlet_cur": str(cur),
        "_com_irdai_document_media_IRDAIDocumentMediaPortlet_delta": str(delta),
        "_com_irdai_document_media_IRDAIDocumentMediaPortlet_resetCur": "false",
    }
    r = requests.get(BASE, params=params, timeout=30, headers={"User-Agent": "PolicyScna-C5.30/1.1"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    rows = []
    for tr in soup.find_all("tr"):
        cells = [" ".join(td.stripped_strings) for td in tr.find_all(["td", "th"])]
        if len(cells) < 8:
            continue
        joined = " | ".join(cells)
        if "Name of the Insurer" in joined or "Financial Year" in joined:
            continue
        status_idx = next((i for i, c in enumerate(cells) if c in {"Non-Archived", "Archived"}), None)
        if status_idx is None or len(cells) <= status_idx + 6:
            continue
        status = cells[status_idx]
        fy = cells[status_idx + 1]
        insurer = cells[status_idx + 2]
        uin = cells[status_idx + 3].strip()
        product = cells[status_idx + 4].strip()
        approval = cells[status_idx + 5].strip()
        type_of_product = cells[-1].strip() if len(cells) > status_idx + 7 else ""
        doc_href = None
        for a in tr.find_all("a", href=True):
            href = a["href"]
            if ".pdf" in href.lower() or "download" in norm(a.get_text(" ", strip=True)):
                doc_href = urljoin(BASE, href)
                break
        rows.append({
            "status": status,
            "financial_year": fy,
            "insurer": insurer,
            "uin": uin,
            "product_name": product,
            "approval_date": approval,
            "type_of_product": type_of_product,
            "document_url": doc_href,
        })
    return rows, r.url


def main() -> int:
    all_rows: list[dict] = []
    page_fingerprints: set[str] = set()
    page_audit: list[dict] = []
    terminal_reason: str | None = None

    for cur in range(1, 101):
        rows, url = fetch_page(cur)
        fp = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()

        if fp in page_fingerprints:
            page_audit.append({
                "cur": cur,
                "row_count": len(rows),
                "sha256": fp,
                "terminal": False,
                "pagination_anomaly": "REPEATED_PAGE_FINGERPRINT",
            })
            print("C5_30_ENUMERATION_PAGINATION_ANOMALY_REPEATED_PAGE", file=sys.stderr)
            return 3

        page_fingerprints.add(fp)
        is_terminal = len(rows) < DELTA
        page_audit.append({
            "cur": cur,
            "row_count": len(rows),
            "sha256": fp,
            "terminal": is_terminal,
        })
        all_rows.extend(rows)

        if is_terminal:
            terminal_reason = "ROW_COUNT_BELOW_REQUESTED_DELTA"
            break
    else:
        print("C5_30_ENUMERATION_INCOMPLETE_NO_TERMINAL_PAGE", file=sys.stderr)
        return 4

    if terminal_reason is None:
        print("C5_30_ENUMERATION_INCOMPLETE_NO_TERMINAL_REASON", file=sys.stderr)
        return 5

    seen: set[tuple[str, str, str]] = set()
    selected: list[dict] = []
    for row in all_rows:
        key = target_key(row["insurer"])
        if not key:
            continue
        identity = (key, row["uin"], row["product_name"])
        if identity in seen:
            continue
        seen.add(identity)
        out = dict(row)
        out["insurer_key"] = key
        selected.append(out)

    selected.sort(key=lambda r: (r["insurer_key"], r["uin"], r["product_name"]))
    counts = {k: 0 for k in TARGETS}
    for row in selected:
        counts[row["insurer_key"]] += 1

    payload = {
        "record_type": "c5_30_disposable_irdai_health_registry_enumeration",
        "source": BASE,
        "requested_page_delta": DELTA,
        "pages_scanned": len(page_audit),
        "terminal_reason": terminal_reason,
        "terminal_page": page_audit[-1]["cur"],
        "terminal_page_row_count": page_audit[-1]["row_count"],
        "page_audit": page_audit,
        "target_counts": counts,
        "candidate_count": len(selected),
        "candidates": selected,
        "selection_started": False,
        "eligibility_adjudication_started": False,
        "semantic_review_started": False,
        "target_clause_reads": 0,
    }
    print("C5_30_ENUMERATION_BEGIN")
    print(json.dumps(payload, indent=2, sort_keys=True))
    print("C5_30_ENUMERATION_END")

    if any(v == 0 for v in counts.values()):
        print("C5_30_ENUMERATION_INCOMPLETE_ZERO_TARGET_INSURER", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
