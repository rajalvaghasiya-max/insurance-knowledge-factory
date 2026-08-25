from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from agents.pdf_intelligence.browser_assisted_pdf_download_agent import (
    BrowserAssistedPDFDownloadAgent,
    BrowserTransportResponse,
)
from agents.pdf_intelligence.pdf_download_agent import PDFDownloadAgent


def _response(*, status=200, content=b"", content_type="application/pdf", url="https://example.test/file.pdf"):
    return SimpleNamespace(
        status_code=status,
        content=content,
        headers={"Content-Type": content_type},
        url=url,
    )


def test_browser_transport_runs_only_after_referer_retry_is_still_protected(monkeypatch) -> None:
    agent = object.__new__(BrowserAssistedPDFDownloadAgent)
    calls = []

    monkeypatch.setattr(
        PDFDownloadAgent,
        "fetch_url_with_referer",
        lambda self, url, referer: _response(status=403, content=b"blocked", url=url),
    )

    def browser_fetch(self, *, url, source_page_url):
        calls.append((url, source_page_url))
        return BrowserTransportResponse(
            status_code=200,
            content=b"%PDF-1.7\n" + b"x" * PDFDownloadAgent.MIN_PDF_SIZE_BYTES,
            headers={"Content-Type": "application/pdf"},
            url=url,
        )

    monkeypatch.setattr(
        BrowserAssistedPDFDownloadAgent,
        "fetch_url_with_browser_context",
        browser_fetch,
    )

    response = agent.fetch_url_with_referer(
        "https://example.test/protected.pdf",
        "https://example.test/product",
    )

    assert response.status_code == 200
    assert calls == [
        ("https://example.test/protected.pdf", "https://example.test/product")
    ]


def test_successful_referer_transport_does_not_invoke_browser(monkeypatch) -> None:
    agent = object.__new__(BrowserAssistedPDFDownloadAgent)

    monkeypatch.setattr(
        PDFDownloadAgent,
        "fetch_url_with_referer",
        lambda self, url, referer: _response(
            status=200,
            content=b"%PDF-1.7\n" + b"x" * PDFDownloadAgent.MIN_PDF_SIZE_BYTES,
            url=url,
        ),
    )

    def unexpected_browser_fetch(*args, **kwargs):
        raise AssertionError("browser fallback must not run after successful Referer transport")

    monkeypatch.setattr(
        BrowserAssistedPDFDownloadAgent,
        "fetch_url_with_browser_context",
        unexpected_browser_fetch,
    )

    response = agent.fetch_url_with_referer(
        "https://example.test/policy.pdf",
        "https://example.test/product",
    )

    assert response.status_code == 200


def test_browser_retrieved_bytes_still_use_parent_validation_hash_and_storage(monkeypatch, tmp_path) -> None:
    valid_content = b"%PDF-1.7\n" + b"browser" * PDFDownloadAgent.MIN_PDF_SIZE_BYTES

    class StubAgent(BrowserAssistedPDFDownloadAgent):
        def __init__(self):
            self.transport_calls = []

        def fetch_url(self, url):
            self.transport_calls.append(("plain", url))
            return _response(status=403, content=b"blocked", url=url)

        def fetch_url_with_browser_context(self, *, url, source_page_url):
            self.transport_calls.append(("browser", url, source_page_url))
            return BrowserTransportResponse(
                status_code=200,
                content=valid_content,
                headers={"Content-Type": "application/pdf"},
                url=url,
            )

        def source_page_artifact_metadata(self, source_html_file):
            return {
                "source_page_artifact_path": None,
                "source_page_artifact_sha256": None,
            }

        def output_path_for_item(self, item, sha256):
            return tmp_path / f"{sha256}.pdf"

        def repository_relative_path(self, path_value):
            return Path(path_value).name if path_value else None

    monkeypatch.setattr(
        PDFDownloadAgent,
        "fetch_url_with_referer",
        lambda self, url, referer: _response(status=403, content=b"still blocked", url=url),
    )

    agent = StubAgent()
    result = agent.process_item(
        {
            "url": "https://example.test/protected-policy.pdf",
            "insurer_id": "example_insurer",
            "document_type": "policy_wording",
            "source_page_url": "https://example.test/product",
            "source_html_file": None,
        },
        {"by_url": {}, "by_hash": {}},
    )

    assert result["status"] == "downloaded"
    assert result["sha256"]
    assert Path(result["local_path"]).read_bytes() == valid_content
    assert agent.transport_calls == [
        ("plain", "https://example.test/protected-policy.pdf"),
        (
            "browser",
            "https://example.test/protected-policy.pdf",
            "https://example.test/product",
        ),
    ]


def test_browser_transport_cannot_bypass_parent_pdf_validation(monkeypatch) -> None:
    class StubAgent(BrowserAssistedPDFDownloadAgent):
        def __init__(self):
            pass

        def fetch_url(self, url):
            return _response(status=403, content=b"blocked", url=url)

        def fetch_url_with_browser_context(self, *, url, source_page_url):
            return BrowserTransportResponse(
                status_code=200,
                content=b"<html>not a pdf</html>" * 1000,
                headers={"Content-Type": "text/html"},
                url=url,
            )

        def source_page_artifact_metadata(self, source_html_file):
            return {
                "source_page_artifact_path": None,
                "source_page_artifact_sha256": None,
            }

    monkeypatch.setattr(
        PDFDownloadAgent,
        "fetch_url_with_referer",
        lambda self, url, referer: _response(status=403, content=b"still blocked", url=url),
    )

    result = StubAgent().process_item(
        {
            "url": "https://example.test/protected-policy.pdf",
            "insurer_id": "example_insurer",
            "document_type": "policy_wording",
            "source_page_url": "https://example.test/product",
            "source_html_file": None,
        },
        {"by_url": {}, "by_hash": {}},
    )

    assert result["status"] == "failed"
    assert result["error"].startswith("not_pdf_like_content_type:")
    assert "sha256" not in result
