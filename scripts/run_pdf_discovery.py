from agents.pdf_intelligence.pdf_discovery_agent import PDFDiscoveryAgent


def run_pdf_discovery():
    agent = PDFDiscoveryAgent()
    result = agent.run()

    print()
    print("=" * 70)
    print("PDF DISCOVERY SUMMARY")
    print("=" * 70)
    print(f"Status          : {result.get('status')}")
    print(f"Insurers scanned: {result.get('insurers_scanned')}")
    print(f"Total PDF URLs  : {result.get('total_pdf_urls')}")
    print(f"Output dir      : {result.get('output_dir')}")
    print("-" * 70)

    for item in result.get("insurers", []):
        print(
            f"{item['insurer_id']}: "
            f"html={item['html_files_scanned']} "
            f"pdfs={item['pdf_urls_found']}"
        )

    print("=" * 70)


if __name__ == "__main__":
    run_pdf_discovery()
