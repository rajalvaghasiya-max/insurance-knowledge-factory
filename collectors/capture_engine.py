import requests
from bs4 import BeautifulSoup
from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

from config.settings import REQUEST_TIMEOUT


REALISTIC_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class CaptureEngine:
    """
    Multi-strategy capture engine.

    Strategy order:
    1. Static HTTP
    2. Playwright headless
    3. Playwright visible browser

    A strategy is accepted only if meaningful text is captured
    and no blocked-page signals are detected.
    """

    def capture(self, url: str) -> dict:
        attempted_strategies = []

        attempted_strategies.append("static_http")
        result = self.capture_with_requests(url)
        result["capture_strategy_attempted"] = attempted_strategies.copy()

        if self.is_valid_capture(result):
            result["screenshot_bytes"] = self.capture_screenshot_only(url)
            return result

        attempted_strategies.append("playwright_headless")
        result = self.capture_with_playwright(url, headless=True)
        result["capture_strategy_attempted"] = attempted_strategies.copy()

        if self.is_valid_capture(result):
            return result

        attempted_strategies.append("playwright_visible")
        result = self.capture_with_playwright(url, headless=False)
        result["capture_strategy_attempted"] = attempted_strategies.copy()

        return result

    def capture_with_requests(self, url: str) -> dict:
        try:
            response = requests.get(
                url,
                headers={"User-Agent": REALISTIC_USER_AGENT},
                timeout=REQUEST_TIMEOUT,
            )

            response.raise_for_status()

            html = response.text
            text = self.extract_text_from_html(html)

            return {
                "status": "captured",
                "url": url,
                "html": html,
                "text": text,
                "page_title": self.extract_title_from_html(html),
                "capture_strategy": "static_http",
                "screenshot_bytes": None,
                "error": None,
            }

        except Exception as error:
            return self.failed_result(
                url=url,
                strategy_name="static_http",
                error=error,
            )

    def capture_with_playwright(self, url: str, headless: bool) -> dict:
        strategy_name = (
            "playwright_headless"
            if headless
            else "playwright_visible"
        )

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=headless
                )

                context = browser.new_context(
                    user_agent=REALISTIC_USER_AGENT,
                    viewport={
                        "width": 1366,
                        "height": 768,
                    },
                    locale="en-IN",
                )

                page = context.new_page()

                try:
                    page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=90000,
                    )

                    page.wait_for_timeout(8000)

                    html = page.content()
                    text = page.locator("body").inner_text()
                    title = page.title()
                    screenshot_bytes = page.screenshot(
                        full_page=True
                    )

                    browser.close()

                    return {
                        "status": "captured",
                        "url": url,
                        "html": html,
                        "text": text,
                        "page_title": title,
                        "capture_strategy": strategy_name,
                        "screenshot_bytes": screenshot_bytes,
                        "error": None,
                    }

                except PlaywrightTimeoutError as error:
                    html = page.content()

                    try:
                        text = page.locator("body").inner_text()
                    except Exception:
                        text = self.extract_text_from_html(html)

                    try:
                        title = page.title()
                    except Exception:
                        title = self.extract_title_from_html(html)

                    try:
                        screenshot_bytes = page.screenshot(
                            full_page=True
                        )
                    except Exception:
                        screenshot_bytes = None

                    browser.close()

                    return {
                        "status": "partial_capture",
                        "url": url,
                        "html": html,
                        "text": text,
                        "page_title": title,
                        "capture_strategy": strategy_name,
                        "screenshot_bytes": screenshot_bytes,
                        "error": str(error),
                    }

        except Exception as error:
            return self.failed_result(
                url=url,
                strategy_name=strategy_name,
                error=error,
            )

    def capture_screenshot_only(self, url: str) -> bytes | None:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True
                )

                context = browser.new_context(
                    user_agent=REALISTIC_USER_AGENT,
                    viewport={
                        "width": 1366,
                        "height": 768,
                    },
                    locale="en-IN",
                )

                page = context.new_page()

                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=90000,
                )

                page.wait_for_timeout(5000)

                screenshot_bytes = page.screenshot(
                    full_page=True
                )

                browser.close()

                return screenshot_bytes

        except Exception as error:
            print(
                f"Screenshot-only capture failed for {url}: {error}"
            )
            return None

    def extract_text_from_html(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")

        for tag in soup([
            "script",
            "style",
            "noscript",
        ]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        lines = [
            line.strip()
            for line in text.splitlines()
        ]
        clean_lines = [
            line
            for line in lines
            if line
        ]

        return "\n".join(clean_lines)

    def extract_title_from_html(self, html: str) -> str | None:
        soup = BeautifulSoup(html, "lxml")

        if soup.title and soup.title.string:
            return soup.title.string.strip()

        return None

    def is_valid_capture(self, result: dict) -> bool:
        if result.get("status") not in [
            "captured",
            "partial_capture",
        ]:
            return False

        text_only = result.get("text", "").strip()

        combined_text = (
            f"{result.get('html', '')}\n{text_only}"
            .lower()
        )

        blocked_signals = [
            "access denied",
            "you don't have permission",
            "errors.edgesuite.net",
            "bot detection",
            "captcha",
            "request blocked",
            "forbidden",
        ]

        for signal in blocked_signals:
            if signal in combined_text:
                return False

        if len(text_only) < 500:
            return False

        return True

    def failed_result(
        self,
        url: str,
        strategy_name: str,
        error: Exception,
    ) -> dict:
        return {
            "status": "failed",
            "url": url,
            "html": "",
            "text": "",
            "page_title": None,
            "capture_strategy": strategy_name,
            "screenshot_bytes": None,
            "error": str(error),
        }