import json
import time
from datetime import datetime, timezone

from agents.queue_capture_agent import QueueCaptureAgent
from config.settings import BASE_DIR
from config.version import APP_NAME, APP_VERSION


MAX_URLS_PER_QUEUE = 5


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_queue_capture_log(summary: dict, run_id: str) -> None:
    log_dir = BASE_DIR / "logs" / "queue_capture_runs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_path = log_dir / f"queue_capture_{run_id}.json"

    with open(log_path, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2, ensure_ascii=False)

    print(f"Run log saved   : {log_path}")


def run_queue_capture():
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    started_at = utc_now_iso()
    start_time = time.time()

    queue_dir = BASE_DIR / "discovery" / "url_queue"

    if not queue_dir.exists():
        print(f"Queue directory not found: {queue_dir}")
        return

    print()
    print("=" * 70)
    print(f"{APP_NAME.upper()} - QUEUE CAPTURE RUN")
    print("=" * 70)
    print(f"Run ID          : {run_id}")
    print(f"Version         : {APP_VERSION}")
    print(f"Max URLs/Queue  : {MAX_URLS_PER_QUEUE}")
    print("=" * 70)

    agent = QueueCaptureAgent()
    queue_summaries = []

    for queue_file in queue_dir.glob("*_discovered_urls.json"):
        print()
        print("=" * 70)
        print(f"Processing queue: {queue_file.name}")
        print("=" * 70)

        summary = agent.process_queue_file(
            queue_file=queue_file,
            max_urls=MAX_URLS_PER_QUEUE,
        )

        queue_summaries.append(summary)
        print(summary)

    completed_at = utc_now_iso()
    duration_seconds = round(time.time() - start_time, 2)

    total_attempted = sum(s["attempted"] for s in queue_summaries)
    total_captured = sum(s["captured"] for s in queue_summaries)
    total_failed = sum(s["failed"] for s in queue_summaries)
    total_skipped = sum(s["skipped"] for s in queue_summaries)

    final_summary = {
        "run_id": run_id,
        "app_name": APP_NAME,
        "version": APP_VERSION,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_seconds": duration_seconds,
        "max_urls_per_queue": MAX_URLS_PER_QUEUE,
        "total_attempted": total_attempted,
        "total_captured": total_captured,
        "total_failed": total_failed,
        "total_skipped": total_skipped,
        "queue_summaries": queue_summaries,
    }

    print()
    print("=" * 70)
    print("QUEUE CAPTURE SUMMARY")
    print("=" * 70)
    print(f"Run ID          : {run_id}")
    print(f"Duration        : {duration_seconds}s")
    print(f"Total attempted : {total_attempted}")
    print(f"Total captured  : {total_captured}")
    print(f"Total failed    : {total_failed}")
    print(f"Total skipped   : {total_skipped}")
    save_queue_capture_log(final_summary, run_id)
    print("=" * 70)


if __name__ == "__main__":
    run_queue_capture()