from __future__ import annotations

import json
import re
import argparse
from pathlib import Path
from config.settings import BASE_DIR


PRODUCT_TERMS = {
    "aditya_birla_health:activ_one": [
        "activ-one",
        "activ one",
        "activone",
        "active-one",
        "active one",
        "activeone",
    ]
}

BLOCKED_TERMS = [
    "activ-one-max",
    "activonemax",
    "activ-one-max-plus",
    "activonemaxplus",
    "activ-one-vytl",
    "activonevytl",
    "vytl",
    "maxplus",
]


def flatten(obj):
    parts = []

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                parts.append(str(k))
                walk(v)
        elif isinstance(x, list):
            for i in x:
                walk(i)
        else:
            parts.append(str(x))

    walk(obj)
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entity-id", required=True)
    args = parser.parse_args()

    terms = PRODUCT_TERMS[args.entity_id]

    roots = [
        BASE_DIR / "discovery" / "pdf_queue",
        BASE_DIR / "discovery" / "url_queue",
        BASE_DIR / "archive" / "metadata",
        BASE_DIR / "archive" / "raw_html",
    ]

    results = []

    for root in roots:
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if not path.is_file():
                continue

            if path.suffix.lower() not in [".json", ".html", ".txt"]:
                continue

            try:
                raw = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            text = raw.lower()

            if path.suffix.lower() == ".json":
                try:
                    text = flatten(json.loads(raw)).lower()
                except Exception:
                    pass

            if not any(t in text for t in terms):
                continue

            if any(b in text for b in BLOCKED_TERMS):
                continue

            urls = re.findall(r"https?://[^\s\"'<>]+", text)

            pdf_urls = [
                u.rstrip(").,;]")
                for u in urls
                if ".pdf" in u.lower()
            ]

            doc_urls = [
                u.rstrip(").,;]")
                for u in urls
                if any(x in u.lower() for x in [
                    "policy", "wording", "brochure", "prospectus", "cis", "customer-information"
                ])
            ]

            for u in sorted(set(pdf_urls + doc_urls)):
                results.append({
                    "source_file": str(path.relative_to(BASE_DIR)).replace("\\", "/"),
                    "url": u,
                })

    print("=" * 70)
    print("PRODUCT DOCUMENT URL FILTER")
    print("=" * 70)
    print(f"Entity : {args.entity_id}")
    print(f"Found  : {len(results)}")
    print("-" * 70)

    for item in results:
        print(item["url"])
        print(f"  source: {item['source_file']}")

    out = BASE_DIR / "knowledge" / "health" / "document_acquisition"
    out.mkdir(parents=True, exist_ok=True)

    out_path = out / f"{args.entity_id.replace(':', '_')}_filtered_document_urls.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print("-" * 70)
    print(f"Output : {out_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()