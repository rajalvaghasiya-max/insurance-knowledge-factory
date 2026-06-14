from datetime import datetime, timezone
from pathlib import Path

from agents.preservation_agent import PreservationAgent
from storage.registry_store import load_json, save_json


class QueueCaptureAgent:
    """
    Reads discovered URL queues and captures URLs marked for crawling.

    Queue item lifecycle:
    new -> capturing -> captured / failed
    """

    def __init__(self):
        self.preservation_agent = PreservationAgent()

    def utc_now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def process_queue_file(
        self,
        queue_file: Path,
        max_urls: int | None = None,
    ) -> dict:

        queue_items = load_json(queue_file, default=[])

        attempted = 0
        captured = 0
        failed = 0
        skipped = 0

        for item in queue_items:
            if max_urls is not None and attempted >= max_urls:
                break

            if item.get("crawl") is not True:
                skipped += 1
                continue

            if item.get("status") != "new":
                skipped += 1
                continue

            attempted += 1

            insurer_id = item.get("insurer_id")
            url = item.get("discovered_url")

            print(f"Capturing queued URL: {insurer_id} - {url}")

            item["status"] = "capturing"
            item["last_attempted_at"] = self.utc_now_iso()
            item["capture_count"] = item.get("capture_count", 0) + 1

            save_json(queue_file, queue_items)

            try:
                result = self.preservation_agent.preserve_page(
                    insurer_id=insurer_id,
                    url=url,
                )

                item["last_capture_hash"] = result.get("content_hash")
                item["last_capture_strategy"] = result.get("capture_strategy")
                item["last_capture_status"] = result.get("status")
                item["last_error"] = result.get("error")

                if result.get("status") in ["captured", "partial_capture"]:
                    item["status"] = "captured"
                    captured += 1
                else:
                    item["status"] = "failed"
                    failed += 1

            except Exception as error:
                item["status"] = "failed"
                item["last_error"] = str(error)
                failed += 1

            save_json(queue_file, queue_items)

        return {
            "queue_file": str(queue_file),
            "attempted": attempted,
            "captured": captured,
            "failed": failed,
            "skipped": skipped,
            "total_items": len(queue_items),
        }