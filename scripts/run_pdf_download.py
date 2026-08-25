from agents.pdf_intelligence.browser_assisted_pdf_download_agent import (
    BrowserAssistedPDFDownloadAgent,
)


def run_pdf_download():
    agent = BrowserAssistedPDFDownloadAgent()
    result = agent.run()

    print()
    print("=" * 70)
    print("PDF DOWNLOAD SUMMARY")
    print("=" * 70)
    print(f"Total queued        : {result.get('total_queued', 0)}")
    print(f"Downloaded          : {result.get('downloaded', 0)}")
    print(f"New versions        : {result.get('new_version_downloaded', 0)}")
    print(f"Unchanged           : {result.get('unchanged', 0)}")
    print(f"Failed              : {result.get('failed', 0)}")
    print(f"Registry            : {result.get('registry_path')}")
    print(f"Run log             : {result.get('log_path')}")
    print("=" * 70)


if __name__ == "__main__":
    run_pdf_download()
