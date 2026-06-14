from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

from config.settings import BASE_DIR


PRODUCT_PAGES = {
    "star_health:star_comprehensive": [
        "https://www.starhealth.in/health-insurance/comprehensive-health-insurance"
    ],
    "aditya_birla_health:activ_one": [
        "https://www.adityabirlacapital.com/healthinsurance/activ-one"
    ],
}


DOCUMENT_TYPE_KEYWORDS = {
    "policy_wording": [
        "policy wording",
        "policy wordings",
        "policy document",
        "policy-document",
        "policy_document",
        "wording",
        "policy clause",
    ],
    "customer_information_sheet": [
        "customer information sheet",
        "customer-information-sheet",
        "customer_information_sheet",
        "cis",
    ],
    "prospectus": [
        "prospectus",
    ],
    "brochure": [
        "brochure",
    ],
    "claim_form": [
        "claim form",
        "claim-form",
        "claim_form",
    ],
}


def classify_document(title: str, url: str) -> str:
    text = f"{title} {url}".lower()

    for document_type, keywords in DOCUMENT_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text:
                return document_type

    return "other"


def discover_from_page(page_url: str, headless: bool = True) -> list[dict]:
    print(f"Opening product page in browser: {page_url}")

    results = []
    seen_urls = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)

        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )

        try:

            pdf_requests = []

            def capture_response(response):
                url = response.url
                content_type = response.headers.get("content-type", "")
                if ".pdf" in url.lower() or "pdf" in content_type.lower():
                    pdf_requests.append({
                        "label": "Network PDF",
                        "url": url,
                        "document_type": classify_document("Network PDF", url),
                    })

            page.on("response", capture_response)

            page.goto(
                page_url,
                wait_until="domcontentloaded",
                timeout=90000,
            )

            print("Page opened successfully.")

            # Let JS-rendered download links load.
            page.wait_for_timeout(10000)

            # Scroll to bottom to trigger lazy-loaded sections.
            for _ in range(5):
                page.mouse.wheel(0, 2500)
                page.wait_for_timeout(1500)

                elements = page.locator("a, button, div, span").evaluate_all(
                    """
                    elements => elements.map(el => ({
                        tag: el.tagName || "",
                        text: el.innerText || el.textContent || "",
                        href: el.href || "",
                        onclick: el.getAttribute("onclick") || "",
                        datahref: el.getAttribute("data-href") || "",
                        datalink: el.getAttribute("data-link") || "",
                        title: el.getAttribute("title") || "",
                        aria: el.getAttribute("aria-label") || ""
                    }))
                    """
                )

                print(f"Total elements scanned: {len(elements)}")

                for el in elements:
                    title = (
                        el.get("text")
                        or el.get("title")
                        or el.get("aria")
                        or "Document"
                    ).strip()

                    values = [
                        el.get("href", ""),
                        el.get("onclick", ""),
                        el.get("datahref", ""),
                        el.get("datalink", ""),
                    ]

                    for value in values:
                        if not value:
                            continue

                        if ".pdf" not in value.lower():
                            continue

                        full_url = urljoin(page_url, value)

                        if full_url in seen_urls:
                            continue

                        seen_urls.add(full_url)

                        results.append(
                            {
                                "page_url": page_url,
                                "label": title,
                                "url": full_url,
                                "document_type": classify_document(title, full_url),
                            }
                        )

            for item in pdf_requests:
                if item["url"] not in seen_urls:
                    seen_urls.add(item["url"])
                    item["page_url"] = page_url
                    results.append(item)

        except Exception as exc:
            print(f"Error while opening page in browser: {exc}")

        finally:
            browser.close()

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entity-id", required=True)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    entity_id = args.entity_id

    urls = PRODUCT_PAGES.get(entity_id)
    if not urls:
        raise ValueError(f"No product page configured for entity_id: {entity_id}")

    all_results = []

    for page_url in urls:
        all_results.extend(
            discover_from_page(
                page_url=page_url,
                headless=not args.headed,
            )
        )

    out_dir = BASE_DIR / "knowledge" / "health" / "document_acquisition"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{entity_id.replace(':', '_')}_live_document_links.json"
    out_path.write_text(
        json.dumps(all_results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("=" * 70)
    print("BROWSER PRODUCT DOCUMENT DISCOVERY")
    print("=" * 70)
    print(f"Entity : {entity_id}")
    print(f"Found  : {len(all_results)}")
    print(f"Output : {out_path}")
    print("-" * 70)

    for item in all_results:
        print(f"[{item['document_type']}] {item['label']}")
        print(item["url"])

    print("=" * 70)


if __name__ == "__main__":
    main()