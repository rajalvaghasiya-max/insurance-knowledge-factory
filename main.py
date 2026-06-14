import json
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

from agents.preservation_agent import PreservationAgent
from storage.registry_store import load_json
from config.settings import BASE_DIR


MAX_WORKERS = 3
from config.version import APP_NAME, APP_VERSION


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def capture_insurer(insurer: dict) -> dict:
    agent = PreservationAgent()

    insurer_id = insurer["insurer_id"]
    website = insurer["website"]

    print(f"Capturing: {insurer['name']}")

    result = agent.preserve_page(
        insurer_id=insurer_id,
        url=website,
    )

    return result


def save_run_log(summary: dict, run_id: str) -> None:
    log_dir = BASE_DIR / "logs" / "capture_runs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_path = log_dir / f"capture_{run_id}.json"

    with open(log_path, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2, ensure_ascii=False)

    print(f"Run log saved        : {log_path}")


def print_summary(results, run_metadata):
    print()
    print("=" * 70)
    print("CAPTURE SUMMARY")
    print("=" * 70)

    total = len(results)

    successful = sum(
        1 for r in results
        if r["status"] in ["captured", "partial_capture"]
    )

    failed = total - successful

    strategy_counter = Counter(
        r.get("capture_strategy", "unknown")
        for r in results
    )

    screenshot_count = sum(
        1 for r in results
        if r.get("has_screenshot")
    )

    print(f"Run ID               : {run_metadata['run_id']}")
    print(f"Started At           : {run_metadata['started_at']}")
    print(f"Completed At         : {run_metadata['completed_at']}")
    print(f"Duration Seconds     : {run_metadata['duration_seconds']}")
    print(f"Max Workers          : {run_metadata['max_workers']}")
    print(f"Version              : {run_metadata['version']}")
    print()
    print(f"Total URLs           : {total}")
    print(f"Successful           : {successful}")
    print(f"Failed               : {failed}")
    print()

    print("Capture Strategies")
    print("------------------------------")

    for strategy, count in strategy_counter.items():
        print(f"{strategy:<25} {count}")

    print()

    print(f"Screenshots Saved    : {screenshot_count}")

    summary = {
        **run_metadata,
        "total_urls": total,
        "successful": successful,
        "failed": failed,
        "capture_strategies": dict(strategy_counter),
        "screenshots_saved": screenshot_count,
        "results": results,
    }

    save_run_log(summary, run_metadata["run_id"])

    print("=" * 70)


def run_first_capture():
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    started_at = utc_now_iso()
    run_start_time = time.time()

    insurers_path = (
        BASE_DIR
        / "registries"
        / "insurers"
        / "insurers.json"
    )

    insurers = load_json(insurers_path)

    print()
    print("=" * 70)
    print(APP_NAME.upper())
    print("=" * 70)
    print(f"Run ID               : {run_id}")
    print(f"Total insurers/pages : {len(insurers)}")
    print(f"Parallel workers     : {MAX_WORKERS}")
    print(f"Version              : {APP_VERSION}")
    print("=" * 70)
    print()

    results = []

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        future_to_insurer = {
            executor.submit(
                capture_insurer,
                insurer
            ): insurer

            for insurer in insurers
        }

        for future in as_completed(
            future_to_insurer
        ):
            insurer = future_to_insurer[future]

            try:
                result = future.result()
                results.append(result)

                print(
                    f"✓ {insurer['insurer_id']} "
                    f"({result.get('capture_strategy')}) "
                    f"{result.get('capture_duration_seconds')}s"
                )

            except Exception as error:
                print(
                    f"✗ {insurer['insurer_id']} "
                    f"{error}"
                )

                results.append({
                    "insurer_id": insurer.get("insurer_id"),
                    "url": insurer.get("website"),
                    "status": "failed",
                    "capture_strategy": "error",
                    "capture_strategy_attempted": [],
                    "has_screenshot": False,
                    "capture_duration_seconds": None,
                    "error": str(error),
                })

    completed_at = utc_now_iso()
    duration_seconds = round(time.time() - run_start_time, 2)

    run_metadata = {
        "run_id": run_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_seconds": duration_seconds,
        "max_workers": MAX_WORKERS,
        "version": APP_VERSION,
    }

    print_summary(results, run_metadata)


if __name__ == "__main__":
    run_first_capture()