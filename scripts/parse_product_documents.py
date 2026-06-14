from __future__ import annotations

import argparse
import json
from pathlib import Path

import fitz  # PyMuPDF

from config.settings import BASE_DIR


DOCUMENTS = {
    "policy_wording.pdf": "policy_wording",
    "customer_information_sheet.pdf": "customer_information_sheet",
    "prospectus.pdf": "prospectus",
    "brochure.pdf": "brochure",
}


def parse_pdf(pdf_path: Path, source_type: str) -> dict:
    doc = fitz.open(pdf_path)

    pages = []

    for idx, page in enumerate(doc, start=1):
        text = page.get_text("text") or ""

        pages.append(
            {
                "page_number": idx,
                "text": text.strip(),
                "char_count": len(text),
            }
        )

    return {
        "source_type": source_type,
        "source_file": str(pdf_path.relative_to(BASE_DIR)).replace("\\", "/"),
        "page_count": len(pages),
        "pages": pages,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entity-id", required=True)
    args = parser.parse_args()

    insurer_slug, product_slug = args.entity_id.split(":")

    documents_dir = (
        BASE_DIR
        / "knowledge"
        / "health"
        / insurer_slug
        / product_slug
        / "documents"
    )

    parsed_dir = (
        BASE_DIR
        / "knowledge"
        / "health"
        / insurer_slug
        / product_slug
        / "parsed"
    )

    parsed_dir.mkdir(parents=True, exist_ok=True)

    if not documents_dir.exists():
        raise FileNotFoundError(f"Documents folder not found: {documents_dir}")

    results = []

    for filename, source_type in DOCUMENTS.items():
        pdf_path = documents_dir / filename

        if not pdf_path.exists():
            results.append(
                {
                    "source_type": source_type,
                    "file": filename,
                    "status": "missing",
                }
            )
            continue

        parsed = parse_pdf(pdf_path, source_type)

        output_path = parsed_dir / f"{source_type}.json"
        output_path.write_text(
            json.dumps(parsed, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        results.append(
            {
                "source_type": source_type,
                "file": filename,
                "status": "parsed",
                "pages": parsed["page_count"],
                "output": str(output_path.relative_to(BASE_DIR)).replace("\\", "/"),
            }
        )

    report = {
        "entity_id": args.entity_id,
        "documents_dir": str(documents_dir.relative_to(BASE_DIR)).replace("\\", "/"),
        "parsed_dir": str(parsed_dir.relative_to(BASE_DIR)).replace("\\", "/"),
        "results": results,
    }

    report_path = parsed_dir / "parse_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("=" * 70)
    print("PRODUCT DOCUMENT PARSER")
    print("=" * 70)
    print(f"Entity : {args.entity_id}")
    print(f"Input  : {documents_dir}")
    print(f"Output : {parsed_dir}")
    print("-" * 70)

    for item in results:
        symbol = "✓" if item["status"] == "parsed" else "✗"
        print(f"{symbol} {item['source_type']} - {item['status']}")
        if item["status"] == "parsed":
            print(f"  Pages : {item['pages']}")
            print(f"  File  : {item['output']}")

    print("-" * 70)
    print(f"Report : {report_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()