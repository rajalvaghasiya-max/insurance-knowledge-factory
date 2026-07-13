"""Governed classification of captured source assets for safe routing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from config.settings import BASE_DIR


class SourceAssetClassifier:
    """Classifies a source asset before product identity or consolidation routing.

    The registry is the governed extension point. New insurer/product patterns are
    registered there; this classifier deliberately contains no product-specific
    URL rules.
    """

    RULES_PATH = BASE_DIR / "registry" / "source_asset_classification_rules.json"

    def __init__(self, rules_path: Path | None = None) -> None:
        self.rules_path = rules_path or self.RULES_PATH
        self.rules = self._load_rules(self.rules_path)

    @staticmethod
    def _load_rules(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(
                f"Source asset classification rules not found: {path}"
            )

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid source asset classification rules JSON: {path}"
            ) from exc

        required_keys = {
            "home_paths",
            "generic_product_slugs",
            "product_listing_slugs",
            "category_url_keywords",
            "individual_product_slug_keywords",
            "page_intent_scope_map",
        }
        missing = sorted(required_keys - payload.keys())
        if missing:
            raise ValueError(
                "Source asset classification rules missing required keys: "
                + ", ".join(missing)
            )

        return payload

    def classify(self, url: str, page_title: str = "") -> dict[str, str]:
        page_intent, intent_reason = self._detect_page_intent(url, page_title)
        asset_scope, scope_reason = self._derive_asset_scope(url, page_intent)

        return {
            "page_intent": page_intent,
            "asset_scope": asset_scope,
            "classification_reason": f"{intent_reason}; {scope_reason}",
            "classification_rules_version": str(
                self.rules.get("schema_version", "unknown")
            ),
        }

    def _detect_page_intent(self, url: str, page_title: str) -> tuple[str, str]:
        parsed = urlparse(url)
        path = parsed.path.lower().rstrip("/")
        slug = path.split("/")[-1]
        text = f"{url} {page_title}".lower()

        if path in self._set("home_paths") or slug in {"home", "homepage"}:
            return "homepage", "matched home path"
        if self._contains_any(text, ["customer-service", "customer service", "support", "contact-us"]):
            return "customer_service", "matched customer-service marker"
        if self._contains_any(text, ["calculator", "calculators"]):
            return "calculator", "matched calculator marker"
        if slug in {"faq", "faqs"} or "/faq" in path or "/faqs" in path:
            return "faq", "matched FAQ marker"
        if self._contains_any(text, ["investor", "financial-information", "annual-report", "public-disclosure"]):
            return "institution", "matched institutional marker"
        if self._contains_any(text, ["download", "brochure", "policy-wording", "policy wording", "proposal-form"]):
            return "document_listing", "matched document-listing marker"
        if slug in self._set("product_listing_slugs"):
            return "product_listing", "matched product-listing slug"
        if self._contains_any(text, self._list("category_url_keywords")):
            return "product_listing", "matched category URL marker"
        if slug and slug not in self._set("generic_product_slugs") and self._contains_any(
            f"{slug} {url}".lower(),
            self._list("individual_product_slug_keywords"),
        ):
            return "individual_product", "matched approved individual-product URL marker"
        if "claim" in text:
            return "claim", "matched claim marker"
        if "glossary" in text:
            return "glossary", "matched glossary marker"
        if self._contains_any(text, ["what-is", "guide", "benefits", "types-of", "tax"]):
            return "article", "matched article marker"
        if self._contains_any(text, ["insurance", "plan", "policy"]):
            return "article_or_product_related", "matched insurance-related marker"
        return "article_or_other", "no stronger classification signal"

    def _derive_asset_scope(self, url: str, page_intent: str) -> tuple[str, str]:
        text = url.lower()
        if self._contains_any(text, self._list("category_url_keywords")):
            return "category", "category override from URL marker"

        scope = self.rules["page_intent_scope_map"].get(page_intent, "unknown")
        return scope, f"mapped from page intent '{page_intent}'"

    def _list(self, key: str) -> list[str]:
        values = self.rules.get(key, [])
        if not isinstance(values, list):
            raise ValueError(f"Classification rules '{key}' must be a list")
        return [str(value).lower() for value in values]

    def _set(self, key: str) -> set[str]:
        return set(self._list(key))

    @staticmethod
    def _contains_any(text: str, markers: list[str]) -> bool:
        return any(marker and marker in text for marker in markers)
