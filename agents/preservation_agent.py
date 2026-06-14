import time
from collectors.capture_engine import CaptureEngine

from config.settings import (
    RAW_HTML_DIR,
    TEXT_DIR,
    METADATA_DIR,
    SCREENSHOT_DIR,
)

from storage.file_store import (
    sha256_text,
    safe_filename,
    utc_now_iso,
    write_text_file,
    write_bytes_file,
)

from storage.registry_store import save_json


class PreservationAgent:
    """
    Preservation agent.

    Saves:
    - Raw HTML
    - Visible text
    - Screenshot, when available
    - Metadata

    Capture strategy is handled by CaptureEngine.
    """

    def __init__(self):
        self.capture_engine = CaptureEngine()

    def clean_text(self, text: str) -> str:
        lines = text.splitlines()
        cleaned_lines = []

        for line in lines:
            line = line.strip()

            if line:
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def preserve_page(self, insurer_id: str, url: str) -> dict:
        print(f"Capturing URL: {url}")

        start_time = time.time()
        captured_at = utc_now_iso()
        filename = safe_filename(url)

        metadata_path = METADATA_DIR / insurer_id / f"{filename}.json"

        capture = self.capture_engine.capture(url)

        if capture["status"] == "failed":
            metadata = {
                "insurer_id": insurer_id,
                "url": url,
                "source_type": "webpage",
                "captured_at": captured_at,
                "capture_strategy": capture.get("capture_strategy"),
                "status": "failed",
                "error": capture.get("error"),
                "capture_duration_seconds": round(time.time() - start_time, 2),
                "capture_strategy_attempted": capture.get("capture_strategy_attempted", []),
            }

            save_json(metadata_path, metadata)
            return metadata

        html = capture.get("html", "")
        text = self.clean_text(capture.get("text", ""))

        content_hash = sha256_text(html)

        html_path = RAW_HTML_DIR / insurer_id / f"{filename}.html"
        text_path = TEXT_DIR / insurer_id / f"{filename}.txt"

        write_text_file(html_path, html)
        write_text_file(text_path, text)

        screenshot_path = None

        if capture.get("screenshot_bytes"):
            screenshot_path = SCREENSHOT_DIR / insurer_id / f"{filename}.png"
            write_bytes_file(screenshot_path, capture["screenshot_bytes"])

        capture_duration_seconds = round(time.time() - start_time, 2)

        metadata = {
            "insurer_id": insurer_id,
            "url": url,
            "source_type": "webpage",
            "page_title": capture.get("page_title"),
            "content_hash": content_hash,
            "captured_at": captured_at,
            "html_path": str(html_path),
            "text_path": str(text_path),
            "screenshot_path": str(screenshot_path) if screenshot_path else None,
            "capture_strategy": capture.get("capture_strategy"),
            "status": capture.get("status"),
            "text_character_count": len(text),
            "html_character_count": len(html),
            "has_screenshot": screenshot_path is not None,
            "error": capture.get("error"),
            "capture_duration_seconds": capture_duration_seconds,
            "capture_strategy_attempted": capture.get("capture_strategy_attempted", []),
        }

        save_json(metadata_path, metadata)

        return metadata