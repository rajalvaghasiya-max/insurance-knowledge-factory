import hashlib
import json
import mimetypes
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

from config.settings import BASE_DIR
from storage.registry_store import load_json, save_json


class PDFDownloadAgent:
    """
    PDF Download Agent v0.2

    Reads:
        discovery/pdf_queue/*_pdf_urls.json

    Writes:
        archive/raw_pdf/<insurer_id>/<document_type>/<safe_filename>.pdf
        registry/pdf_registry.json
        logs/pdf_download_runs/<timestamp>.json

    Responsibilities:
        - verify PDF/document URL during actual download
        - download file safely
        - compute SHA256 hash
        - avoid duplicate downloads
        - maintain PDF registry
    """

    VERSION = "0.2"

    MAX_WORKERS = 3
    TIMEOUT_SECONDS = 60
    MIN_PDF_SIZE_BYTES = 10 * 1024
    MAX_FILE_SIZE_BYTES = 80 * 1024 * 1024

    PDF_QUEUE_DIR = BASE_DIR / "discovery" / "pdf_queue"
    RAW_PDF_DIR = BASE_DIR / "archive" / "raw_pdf"
    REGISTRY_DIR = BASE_DIR / "registry"
    LOG_DIR = BASE_DIR / "logs" / "pdf_download_runs"

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    )

    def __init__(self):
        self.RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)
        self.REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.REGISTRY_DIR / "pdf_registry.json"

    def utc_now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def run(self, limit_per_insurer: int | None = None) -> dict:
        queue_items = self.load_queue_items(limit_per_insurer=limit_per_insurer)
        registry = self.load_registry()

        run = {
            "generated_at": self.utc_now_iso(),
            "agent": "pdf_download_agent",
            "agent_version": self.VERSION,
            "max_workers": self.MAX_WORKERS,
            "total_queued": len(queue_items),
            "downloaded": 0,
            "new_version_downloaded": 0,
            "unchanged": 0,
            "failed": 0,
            "items": [],
        }

        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            futures = {
                executor.submit(
                    self.process_item,
                    item,
                    registry,
                ): item
                for item in queue_items
            }

            for future in as_completed(futures):
                result = future.result()
                run["items"].append(result)

                if result["status"] == "downloaded":
                    run["downloaded"] += 1
                    self.update_registry(registry, result)

                elif result["status"] == "new_version_downloaded":
                    run["new_version_downloaded"] += 1
                    self.update_registry(registry, result)

                elif result["status"] == "unchanged":
                    run["unchanged"] += 1
                    self.update_registry(registry, result)

                else:
                    run["failed"] += 1

                print(
                    f"{result['status'].upper():18} "
                    f"{result.get('insurer_id')} "
                    f"{result.get('document_type')} "
                    f"{result.get('url')}"
                )

        registry["updated_at"] = self.utc_now_iso()
        save_json(self.registry_path, registry)

        log_path = self.LOG_DIR / f"pdf_download_run_{self.timestamp_for_filename()}.json"
        save_json(log_path, run)

        run["registry_path"] = str(self.registry_path)
        run["log_path"] = str(log_path)

        return run

    def load_queue_items(self, limit_per_insurer: int | None = None) -> list[dict]:
        items = []

        if not self.PDF_QUEUE_DIR.exists():
            return items

        for queue_file in sorted(self.PDF_QUEUE_DIR.glob("*_pdf_urls.json")):
            if queue_file.name.startswith("_"):
                continue

            queue = load_json(queue_file, default={})
            insurer_items = queue.get("items", [])

            if limit_per_insurer is not None:
                insurer_items = insurer_items[:limit_per_insurer]

            for item in insurer_items:
                item = dict(item)
                item["queue_file"] = str(queue_file)
                items.append(item)

        return items

    def load_registry(self) -> dict:
        registry = load_json(self.registry_path, default={})

        if not registry:
            registry = {
                "created_at": self.utc_now_iso(),
                "updated_at": self.utc_now_iso(),
                "agent": "pdf_download_agent",
                "agent_version": self.VERSION,
                "by_url": {},
                "by_hash": {},
            }

        registry.setdefault("by_url", {})
        registry.setdefault("by_hash", {})

        # v0.2 migration:
        # Older registry records had a flat sha256. New records are version-aware.
        for url_key, record in list(registry.get("by_url", {}).items()):
            if "versions" not in record:
                old_sha = record.get("sha256")
                if old_sha:
                    version_record = dict(record)
                    version_record.setdefault("version_status", "migrated_existing")
                    record["current_sha256"] = old_sha
                    record["versions"] = [version_record]

        return registry

    def process_item(
        self,
        item: dict,
        registry: dict,
    ) -> dict:
        url = item.get("url", "")
        insurer_id = item.get("insurer_id", "unknown")
        document_type = item.get("document_type", "other_pdf")
        url_key = self.normalize_url_key(url)

        base_result = {
            "processed_at": self.utc_now_iso(),
            "insurer_id": insurer_id,
            "document_type": document_type,
            "url": url,
            "url_key": url_key,
            "source_page_url": item.get("source_page_url"),
            "source_html_file": item.get("source_html_file"),
            "confidence_score": item.get("confidence_score"),
            "status": None,
            "error": None,
        }

        if not url:
            return {**base_result, "status": "failed", "error": "missing_url"}

        previous_url_record = registry.get("by_url", {}).get(url_key)
        previous_sha256 = None

        if previous_url_record:
            previous_sha256 = previous_url_record.get("current_sha256") or previous_url_record.get("sha256")

        try:
            response = self.fetch_url(url)
            validation = self.validate_response(response, url)

            # Retry once with Referer. Useful for HDFC-like protected DAM URLs.
            if (
                not validation["valid"]
                and response.status_code in {403, 401}
                and item.get("source_page_url")
            ):
                response = self.fetch_url_with_referer(
                    url=url,
                    referer=item.get("source_page_url"),
                )
                validation = self.validate_response(response, url)

            if not validation["valid"]:
                return {
                    **base_result,
                    "status": "failed",
                    "error": validation["reason"],
                    "http_status": response.status_code,
                    "content_type": response.headers.get("Content-Type"),
                    "content_length": response.headers.get("Content-Length"),
                }

            content = response.content
            sha256 = hashlib.sha256(content).hexdigest()

            if previous_sha256 and sha256 == previous_sha256:
                return {
                    **base_result,
                    "status": "unchanged",
                    "sha256": sha256,
                    "previous_sha256": previous_sha256,
                    "file_size_bytes": len(content),
                    "http_status": response.status_code,
                    "content_type": response.headers.get("Content-Type"),
                    "local_path": previous_url_record.get("local_path") if previous_url_record else None,
                    "original_filename": self.extract_filename_from_url(url),
                }

            output_path = self.output_path_for_item(item, sha256)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(content)

            status = "new_version_downloaded" if previous_sha256 else "downloaded"

            return {
                **base_result,
                "status": status,
                "sha256": sha256,
                "previous_sha256": previous_sha256,
                "file_size_bytes": len(content),
                "http_status": response.status_code,
                "content_type": response.headers.get("Content-Type"),
                "local_path": str(output_path),
                "original_filename": self.extract_filename_from_url(url),
            }

        except Exception as exc:
            return {
                **base_result,
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
            }

    def fetch_url(self, url: str) -> requests.Response:
        """
        v0.1.1:
        Use browser-like headers and retry once with source-page Referer.
        This improves success rate for insurers that block simple bot requests.
        """

        headers = self.default_headers()

        response = requests.get(
            url,
            headers=headers,
            timeout=self.TIMEOUT_SECONDS,
            allow_redirects=True,
        )

        return response

    def fetch_url_with_referer(self, url: str, referer: str | None) -> requests.Response:
        headers = self.default_headers()

        if referer:
            headers["Referer"] = referer

        response = requests.get(
            url,
            headers=headers,
            timeout=self.TIMEOUT_SECONDS,
            allow_redirects=True,
        )

        return response

    def default_headers(self) -> dict:
        return {
            "User-Agent": self.USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "application/pdf,image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def validate_response(self, response: requests.Response, url: str) -> dict:
        if response.status_code != 200:
            return {"valid": False, "reason": f"http_status_{response.status_code}"}

        content = response.content or b""
        content_type = (response.headers.get("Content-Type") or "").lower()

        if len(content) < self.MIN_PDF_SIZE_BYTES:
            return {"valid": False, "reason": "file_too_small"}

        if len(content) > self.MAX_FILE_SIZE_BYTES:
            return {"valid": False, "reason": "file_too_large"}

        if content.startswith(b"%PDF"):
            return {"valid": True, "reason": "pdf_signature"}

        if "application/pdf" in content_type:
            return {"valid": True, "reason": "content_type_pdf"}

        if ".pdf" in url.lower() and "application/octet-stream" in content_type:
            return {"valid": True, "reason": "octet_stream_pdf_url"}

        return {
            "valid": False,
            "reason": f"not_pdf_like_content_type:{content_type}",
        }

    def update_registry(self, registry: dict, result: dict) -> None:
        url_key = result["url_key"]
        sha256 = result["sha256"]

        version_record = {
            "insurer_id": result["insurer_id"],
            "document_type": result["document_type"],
            "url": result["url"],
            "url_key": url_key,
            "sha256": sha256,
            "previous_sha256": result.get("previous_sha256"),
            "file_size_bytes": result["file_size_bytes"],
            "content_type": result.get("content_type"),
            "http_status": result.get("http_status"),
            "local_path": result.get("local_path"),
            "source_page_url": result.get("source_page_url"),
            "source_html_file": result.get("source_html_file"),
            "confidence_score": result.get("confidence_score"),
            "checked_at": result["processed_at"],
            "downloaded_at": result["processed_at"] if result["status"] in {"downloaded", "new_version_downloaded"} else None,
            "version_status": result["status"],
        }

        url_record = registry["by_url"].get(url_key)

        if not url_record:
            url_record = {
                "insurer_id": result["insurer_id"],
                "document_type": result["document_type"],
                "url": result["url"],
                "url_key": url_key,
                "first_seen_at": result["processed_at"],
                "current_sha256": sha256,
                "current_local_path": result.get("local_path"),
                "last_checked_at": result["processed_at"],
                "last_changed_at": result["processed_at"],
                "versions": [],
            }

        url_record["last_checked_at"] = result["processed_at"]

        if result["status"] in {"downloaded", "new_version_downloaded"}:
            url_record["current_sha256"] = sha256
            url_record["current_local_path"] = result.get("local_path")
            url_record["last_changed_at"] = result["processed_at"]
            url_record["versions"].append(version_record)

        elif result["status"] == "unchanged":
            url_record["current_sha256"] = sha256
            if result.get("local_path"):
                url_record["current_local_path"] = result.get("local_path")
            # Keep history compact: do not append unchanged checks as full versions.
            url_record["last_unchanged_check"] = version_record

        registry["by_url"][url_key] = url_record

        # by_hash points to the latest known version metadata.
        registry["by_hash"][sha256] = version_record

    def output_path_for_item(self, item: dict, sha256: str) -> Path:
        insurer_id = self.safe_path_part(item.get("insurer_id", "unknown"))
        document_type = self.safe_path_part(item.get("document_type", "other_pdf"))

        original_name = self.extract_filename_from_url(item.get("url", ""))
        safe_name = self.safe_filename(original_name)

        if not safe_name.lower().endswith(".pdf"):
            safe_name += ".pdf"

        stem = safe_name[:-4]
        final_name = f"{stem}__{sha256[:12]}.pdf"

        return self.RAW_PDF_DIR / insurer_id / document_type / final_name

    def extract_filename_from_url(self, url: str) -> str:
        parsed = urlparse(url)
        filename = Path(parsed.path).name

        if not filename:
            filename = "document.pdf"

        if ".pdf" in filename.lower():
            filename = filename[: filename.lower().rfind(".pdf") + 4]

        return filename

    def normalize_url_key(self, url: str) -> str:
        return url.strip().lower()

    def safe_path_part(self, value: str) -> str:
        value = str(value or "unknown").strip().lower()
        value = re.sub(r"[^a-z0-9_\-]+", "_", value)
        value = re.sub(r"_+", "_", value)
        return value.strip("_") or "unknown"

    def safe_filename(self, value: str) -> str:
        value = str(value or "document.pdf").strip()
        value = value.replace("%20", "_").replace(" ", "_")
        value = re.sub(r"[^A-Za-z0-9._\-]+", "_", value)
        value = re.sub(r"_+", "_", value)
        return value.strip("._") or "document.pdf"

    def timestamp_for_filename(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def main():
    agent = PDFDownloadAgent()
    result = agent.run()

    print()
    print("=" * 70)
    print("PDF DOWNLOAD SUMMARY")
    print("=" * 70)
    print(f"Total queued        : {result['total_queued']}")
    print(f"Downloaded          : {result['downloaded']}")
    print(f"New versions        : {result['new_version_downloaded']}")
    print(f"Unchanged           : {result['unchanged']}")
    print(f"Failed              : {result['failed']}")
    print(f"Registry            : {result['registry_path']}")
    print(f"Run log             : {result['log_path']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
