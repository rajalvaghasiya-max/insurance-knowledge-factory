from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from requests.structures import CaseInsensitiveDict

from agents.pdf_intelligence.pdf_download_agent import PDFDownloadAgent


@dataclass(frozen=True)
class BrowserTransportResponse:
    """Minimal response adapter consumed by the existing PDF validation boundary."""

    status_code: int
    content: bytes
    headers: Mapping[str, str]
    url: str


class BrowserAssistedPDFDownloadAgent(PDFDownloadAgent):
    """PDF downloader with a browser-context fallback for protected documents.

    Transport authority is intentionally narrow:
    - normal requests transport runs first;
    - the existing Referer retry runs second;
    - browser-context retrieval is attempted only after the Referer response is
      still 401/403 and a source page is available;
    - returned bytes are handed back to ``PDFDownloadAgent.process_item`` and
      therefore pass through the exact same size/type/signature validation,
      raw-byte storage, SHA-256, versioning, and registry logic.

    The browser transport never classifies a document, never infers currentness,
    and never bypasses the parent's validation boundary.
    """

    VERSION = "0.4"
    BROWSER_PAGE_TIMEOUT_MS = 90_000
    BROWSER_SETTLE_MS = 2_000

    def fetch_url_with_referer(self, url: str, referer: str | None):
        response = super().fetch_url_with_referer(url=url, referer=referer)

        if response.status_code not in {401, 403} or not referer:
            return response

        return self.fetch_url_with_browser_context(
            url=url,
            source_page_url=referer,
        )

    def fetch_url_with_browser_context(
        self,
        *,
        url: str,
        source_page_url: str,
    ) -> BrowserTransportResponse:
        """Retrieve a protected document through a source-page browser context.

        ``BrowserContext.request`` shares cookie storage with the browser
        context. Visiting the source page first therefore lets insurer sites
        establish the same session state that a human browser would have before
        the document request is made.
        """
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                context = browser.new_context(
                    user_agent=self.USER_AGENT,
                    viewport={"width": 1366, "height": 768},
                    locale="en-IN",
                )
                page = context.new_page()
                page.goto(
                    source_page_url,
                    wait_until="domcontentloaded",
                    timeout=self.BROWSER_PAGE_TIMEOUT_MS,
                )
                page.wait_for_timeout(self.BROWSER_SETTLE_MS)

                api_response = context.request.get(
                    url,
                    headers={
                        "Referer": source_page_url,
                        "Accept": "application/pdf,application/octet-stream,*/*;q=0.8",
                    },
                    timeout=self.TIMEOUT_SECONDS * 1000,
                    fail_on_status_code=False,
                )

                return BrowserTransportResponse(
                    status_code=api_response.status,
                    content=api_response.body(),
                    headers=CaseInsensitiveDict(api_response.headers),
                    url=api_response.url,
                )
            finally:
                browser.close()
