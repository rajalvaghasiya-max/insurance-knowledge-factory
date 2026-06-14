from agents.html_section_agent import HtmlSectionAgent
from config.settings import BASE_DIR


MAX_FILES = 20


def run_html_sectioning():
    agent = HtmlSectionAgent()

    metadata_dir = BASE_DIR / "archive" / "metadata"

    if not metadata_dir.exists():
        print(f"Metadata directory not found: {metadata_dir}")
        return

    parsed = 0
    skipped = 0

    for insurer_folder in metadata_dir.iterdir():
        if not insurer_folder.is_dir():
            continue

        for metadata_file in insurer_folder.glob("*.json"):
            if parsed >= MAX_FILES:
                break

            result = agent.parse_metadata_file(metadata_file)

            if result["status"] == "parsed":
                parsed += 1
                print(
                    f"✓ Parsed {result['insurer_id']} "
                    f"sections={result['section_count']} "
                    f"chunks={result['chunk_count']}"
                )
            else:
                skipped += 1

        if parsed >= MAX_FILES:
            break

    print()
    print("=" * 70)
    print("HTML SECTIONING SUMMARY")
    print("=" * 70)
    print(f"Parsed  : {parsed}")
    print(f"Skipped : {skipped}")
    print("=" * 70)


if __name__ == "__main__":
    run_html_sectioning()