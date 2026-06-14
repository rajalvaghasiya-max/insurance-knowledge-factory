from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

import requests

from config.settings import BASE_DIR


DOCUMENT_TYPE_TO_FILENAME = {
    "policy_wording": "policy_wording.pdf",
    "customer_information_sheet": "customer_information_sheet.pdf",
    "prospectus": "prospectus.pdf",
    "brochure": "brochure.pdf",
}


def safe_download(url: str, output_path: Path) -> dict:
    try:
        response = requests.get(
            url,
            timeout=60,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        response.raise_for_status()

        content_type = response.headers.get("content-type", "").lower()

        if "pdf" not in content_type and not url.lower().endswith(".pdf"):
            return {
                "success": False,
                "error": f"not_pdf_content_type: {content_type}",
            }

        if len(response.content) < 1000:
            return {
                "success": False,
                "error": "file_too_small",
            }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)

        return {
            "success": True,
            "error": None,
            "bytes": len(response.content),
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entity-id", required=True)
    args = parser.parse_args()

    entity_id = args.entity_id
    entity_slug = entity_id.replace(":", "_")

    input_path = (
        BASE_DIR
        / "knowledge"
        / "health"
        / "document_acquisition"
        / f"{entity_slug}_live_document_links.json"
    )

    if not input_path.exists():
        raise FileNotFoundError(f"Missing input file: {input_path}")

    links = json.loads(input_path.read_text(encoding="utf-8"))

    insurer_slug, product_slug = entity_id.split(":")

    output_dir = (
        BASE_DIR
        / "knowledge"
        / "health"
        / insurer_slug
        / product_slug
        / "documents"
    )

    downloaded = []

    seen_doc_types = set()

    for item in links:
        doc_type = item.get("document_type")
        url = item.get("url")

        if doc_type not in DOCUMENT_TYPE_TO_FILENAME:
            continue

        if doc_type in seen_doc_types:
            continue

        if not url or not url.lower().endswith(".pdf"):
            continue

        filename = DOCUMENT_TYPE_TO_FILENAME[doc_type]
        output_path = output_dir / filename

        result = safe_download(url, output_path)

        downloaded.append(
            {
                "document_type": doc_type,
                "label": item.get("label"),
                "url": url,
                "output_path": str(output_path.relative_to(BASE_DIR)).replace("\\", "/"),
                **result,
            }
        )

        if result["success"]:
            seen_doc_types.add(doc_type)

    report = {
        "entity_id": entity_id,
        "input_file": str(input_path.relative_to(BASE_DIR)).replace("\\", "/"),
        "output_dir": str(output_dir.relative_to(BASE_DIR)).replace("\\", "/"),
        "downloaded": downloaded,
    }

    report_path = (
        BASE_DIR
        / "knowledge"
        / "health"
        / "document_acquisition"
        / f"{entity_slug}_download_report.json"
    )

    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("=" * 70)
    print("PRODUCT DOCUMENT DOWNLOADER")
    print("=" * 70)
    print(f"Entity : {entity_id}")
    print(f"Input  : {input_path}")
    print(f"Output : {output_dir}")
    print("-" * 70)

    for item in downloaded:
        symbol = "✓" if item["success"] else "✗"
        print(f"{symbol} {item['document_type']}")
        print(f"  URL  : {item['url']}")
        print(f"  File : {item['output_path']}")
        if item["error"]:
            print(f"  Error: {item['error']}")

    print("-" * 70)
    print(f"Report : {report_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()