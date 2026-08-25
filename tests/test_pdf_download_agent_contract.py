from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from agents.pdf_intelligence.pdf_download_agent import PDFDownloadAgent


def _response(*, status=200, content=b"", content_type="application/pdf", url="https://example.test/file.pdf"):
    return SimpleNamespace(
        status_code=status,
        content=content,
        headers={"Content-Type": content_type},
        url=url,
    )


def _agent() -> PDFDownloadAgent:
    # Validation helpers are pure and do not require filesystem initialization.
    return object.__new__(PDFDownloadAgent)


def test_pdf_signature_is_authoritative_transport_validation_signal() -> None:
    content = b"%PDF-1.7\n" + b"x" * PDFDownloadAgent.MIN_PDF_SIZE_BYTES
    result = _agent().validate_response(
        _response(content=content, content_type="text/plain"),
        "https://example.test/download?id=123",
    )

    assert result == {"valid": True, "reason": "pdf_signature"}


def test_application_pdf_is_accepted_even_when_url_has_no_pdf_suffix() -> None:
    content = b"x" * (PDFDownloadAgent.MIN_PDF_SIZE_BYTES + 1)
    result = _agent().validate_response(
        _response(content=content, content_type="application/pdf"),
        "https://example.test/document?id=123",
    )

    assert result == {"valid": True, "reason": "content_type_pdf"}


def test_octet_stream_requires_pdf_url() -> None:
    content = b"x" * (PDFDownloadAgent.MIN_PDF_SIZE_BYTES + 1)

    accepted = _agent().validate_response(
        _response(content=content, content_type="application/octet-stream"),
        "https://example.test/policy-wording.pdf",
    )
    rejected = _agent().validate_response(
        _response(content=content, content_type="application/octet-stream"),
        "https://example.test/download?id=123",
    )

    assert accepted == {"valid": True, "reason": "octet_stream_pdf_url"}
    assert rejected["valid"] is False
    assert rejected["reason"].startswith("not_pdf_like_content_type:")


def test_non_200_and_undersized_payloads_fail_closed() -> None:
    forbidden = _agent().validate_response(
        _response(status=403, content=b"%PDF"),
        "https://example.test/file.pdf",
    )
    too_small = _agent().validate_response(
        _response(status=200, content=b"%PDF"),
        "https://example.test/file.pdf",
    )

    assert forbidden == {"valid": False, "reason": "http_status_403"}
    assert too_small == {"valid": False, "reason": "file_too_small"}


def test_oversized_payload_fails_closed_without_pdf_acceptance() -> None:
    agent = _agent()
    agent.MAX_FILE_SIZE_BYTES = 16
    agent.MIN_PDF_SIZE_BYTES = 4
    response = _response(content=b"%PDF" + b"x" * 20)

    result = agent.validate_response(response, "https://example.test/file.pdf")

    assert result == {"valid": False, "reason": "file_too_large"}


def test_403_retry_with_referer_still_passes_through_identical_validation_gate(tmp_path) -> None:
    valid_content = b"%PDF-1.7\n" + b"x" * PDFDownloadAgent.MIN_PDF_SIZE_BYTES

    class StubAgent(PDFDownloadAgent):
        def __init__(self):
            self.fetch_calls = []

        def fetch_url(self, url):
            self.fetch_calls.append(("plain", url, None))
            return _response(status=403, content=b"blocked", url=url)

        def fetch_url_with_referer(self, url, referer):
            self.fetch_calls.append(("referer", url, referer))
            return _response(status=200, content=valid_content, url=url)

        def source_page_artifact_metadata(self, source_html_file):
            return {
                "source_page_artifact_path": None,
                "source_page_artifact_sha256": None,
            }

        def output_path_for_item(self, item, sha256):
            return tmp_path / f"{sha256}.pdf"

        def repository_relative_path(self, path_value):
            return Path(path_value).name if path_value else None

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
    assert result["http_status"] == 200
    assert result["sha256"]
    assert Path(result["local_path"]).read_bytes() == valid_content
    assert agent.fetch_calls == [
        ("plain", "https://example.test/protected-policy.pdf", None),
        (
            "referer",
            "https://example.test/protected-policy.pdf",
            "https://example.test/product",
        ),
    ]
