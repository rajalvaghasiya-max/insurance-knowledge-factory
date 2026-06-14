from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config.settings import BASE_DIR

PRODUCT_PAGES = {
    "aditya_birla_health:activ_one": [
        "https://www.adityabirlacapital.com/healthinsurance/activ-one"
    ],
    "star_health:star_comprehensive": [
        "https://www.starhealth.in/health-insurance/comprehensive-health-insurance"
    ],
}

KEYWORDS = [
    "policy",
    "wording",
    "brochure",
    "prospectus",
    "cis",
    "customer information",
    "customer-information",
    "product",
    "download",
    "pdf",
]


def classify(url: str, text: str) -> str:
    combined = f"{url} {text}".lower()

    if "policy" in combined and "wording" in combined:
        return "policy_wording"

    if "customer" in combined and "information" in combined:
        return "customer_information_sheet"

    if "cis" in combined:
        return "customer_information_sheet"

    if "brochure" in combined:
        return "brochure"

    if "prospectus" in combined:
        return "prospectus"

    return "unknown"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entity-id", required=True)
    args = parser.parse_args()

    urls = PRODUCT_PAGES.get(args.entity_id, [])
    results = []

    for page_url in urls:
        try:
            response = requests.get(
                page_url,
                timeout=90,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            response.raise_for_status()
        except Exception as exc:
            print(f"Failed to fetch: {page_url}")
            print(f"Error: {exc}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        for a in soup.find_all("a"):
            href = a.get("href")
            label = a.get_text(" ", strip=True)

            if not href:
                continue

            abs_url = urljoin(page_url, href)
            combined = f"{abs_url} {label}".lower()

            if ".pdf" in combined or any(k in combined for k in KEYWORDS):
                results.append({
                    "page_url": page_url,
                    "label": label,
                    "url": abs_url,
                    "document_type": classify(abs_url, label),
                })

    out_dir = BASE_DIR / "knowledge" / "health" / "document_acquisition"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{args.entity_id.replace(':', '_')}_live_document_links.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print("=" * 70)
    print("LIVE PRODUCT DOCUMENT DISCOVERY")
    print("=" * 70)
    print(f"Entity : {args.entity_id}")
    print(f"Found  : {len(results)}")
    print(f"Output : {out_path}")
    print("-" * 70)

    for item in results:
        print(f"[{item['document_type']}] {item['label']}")
        print(item["url"])

    print("=" * 70)


if __name__ == "__main__":
    main()