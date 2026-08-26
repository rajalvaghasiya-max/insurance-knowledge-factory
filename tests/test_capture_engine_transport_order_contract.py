from __future__ import annotations

from collectors.capture_engine import CaptureEngine


def _captured(strategy: str) -> dict:
    return {
        "status": "captured",
        "url": "https://example.test/root",
        "html": "<html><body>" + ("x" * 600) + "</body></html>",
        "text": "x" * 600,
        "page_title": "Example",
        "capture_strategy": strategy,
        "screenshot_bytes": None,
        "error": None,
    }


def _failed(strategy: str, error: str = "blocked") -> dict:
    return {
        "status": "failed",
        "url": "https://example.test/root",
        "html": "",
        "text": "",
        "page_title": None,
        "capture_strategy": strategy,
        "screenshot_bytes": None,
        "error": error,
    }


def test_static_http_success_stops_before_browser(monkeypatch) -> None:
    engine = CaptureEngine()
    calls: list[str] = []

    def requests_capture(url: str) -> dict:
        calls.append("static_http")
        return _captured("static_http")

    def playwright_capture(url: str, headless: bool) -> dict:
        calls.append("playwright_headless" if headless else "playwright_visible")
        raise AssertionError("browser transport must not run after accepted static capture")

    monkeypatch.setattr(engine, "capture_with_requests", requests_capture)
    monkeypatch.setattr(engine, "capture_with_playwright", playwright_capture)
    monkeypatch.setattr(engine, "capture_screenshot_only", lambda url: None)

    result = engine.capture("https://example.test/root")

    assert result["capture_strategy"] == "static_http"
    assert result["capture_strategy_attempted"] == ["static_http"]
    assert calls == ["static_http"]


def test_headless_browser_is_second_strategy_after_static_failure(monkeypatch) -> None:
    engine = CaptureEngine()
    calls: list[str] = []

    def requests_capture(url: str) -> dict:
        calls.append("static_http")
        return _failed("static_http", "403 Client Error: Forbidden")

    def playwright_capture(url: str, headless: bool) -> dict:
        strategy = "playwright_headless" if headless else "playwright_visible"
        calls.append(strategy)
        if headless:
            return _captured(strategy)
        raise AssertionError("visible browser must not run after accepted headless capture")

    monkeypatch.setattr(engine, "capture_with_requests", requests_capture)
    monkeypatch.setattr(engine, "capture_with_playwright", playwright_capture)

    result = engine.capture("https://example.test/root")

    assert result["capture_strategy"] == "playwright_headless"
    assert result["capture_strategy_attempted"] == [
        "static_http",
        "playwright_headless",
    ]
    assert calls == ["static_http", "playwright_headless"]


def test_visible_browser_is_third_and_final_strategy(monkeypatch) -> None:
    engine = CaptureEngine()
    calls: list[str] = []

    def requests_capture(url: str) -> dict:
        calls.append("static_http")
        return _failed("static_http")

    def playwright_capture(url: str, headless: bool) -> dict:
        strategy = "playwright_headless" if headless else "playwright_visible"
        calls.append(strategy)
        if headless:
            return _failed(strategy)
        return _captured(strategy)

    monkeypatch.setattr(engine, "capture_with_requests", requests_capture)
    monkeypatch.setattr(engine, "capture_with_playwright", playwright_capture)

    result = engine.capture("https://example.test/root")

    assert result["capture_strategy"] == "playwright_visible"
    assert result["capture_strategy_attempted"] == [
        "static_http",
        "playwright_headless",
        "playwright_visible",
    ]
    assert calls == [
        "static_http",
        "playwright_headless",
        "playwright_visible",
    ]


def test_all_allowed_transport_failures_are_retained_as_failure(monkeypatch) -> None:
    engine = CaptureEngine()

    monkeypatch.setattr(engine, "capture_with_requests", lambda url: _failed("static_http"))
    monkeypatch.setattr(
        engine,
        "capture_with_playwright",
        lambda url, headless: _failed(
            "playwright_headless" if headless else "playwright_visible"
        ),
    )

    result = engine.capture("https://example.test/root")

    assert result["status"] == "failed"
    assert result["capture_strategy"] == "playwright_visible"
    assert result["capture_strategy_attempted"] == [
        "static_http",
        "playwright_headless",
        "playwright_visible",
    ]
