from agents.discovery_agent import DiscoveryAgent
from storage.registry_store import load_json
from config.settings import BASE_DIR


def run_discovery():
    agent = DiscoveryAgent()

    metadata_dir = BASE_DIR / "archive" / "metadata"

    total_discovered = 0

    for insurer_folder in metadata_dir.iterdir():
        if not insurer_folder.is_dir():
            continue

        insurer_id = insurer_folder.name
        insurer_results = []

        for metadata_file in insurer_folder.glob("*.json"):
            metadata = load_json(metadata_file, default={})

            if metadata.get("status") not in ["captured", "partial_capture"]:
                continue

            html_path = metadata.get("html_path")
            source_url = metadata.get("url")

            if not html_path or not source_url:
                continue

            discovered = agent.discover_from_html_file(
                insurer_id=insurer_id,
                source_url=source_url,
                html_path=html_path,
            )

            insurer_results.extend(discovered)

        insurer_results = agent.dedupe(insurer_results)

        if insurer_results:
            output_path = agent.save_discovered_urls(
                insurer_id=insurer_id,
                discovered_urls=insurer_results,
            )

            total_discovered += len(insurer_results)

            print(
                f"{insurer_id}: {len(insurer_results)} URLs discovered"
            )
            print(f"Saved: {output_path}")

    print()
    print("=" * 70)
    print("DISCOVERY SUMMARY")
    print("=" * 70)
    print(f"Total discovered URLs: {total_discovered}")
    print("=" * 70)


if __name__ == "__main__":
    run_discovery()