from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qsl, urlencode, urlunparse
from bs4 import BeautifulSoup

from config.settings import BASE_DIR
from storage.registry_store import save_json


TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
    "_ga",
    "_gl",
    "source",
    "agentcode",
    "language",
    "campaign",
    "ref",
}


IGNORE_KEYWORDS = [
    "login",
    "sign in",
    "signin",
    "portal",
    "employee",
    "crm",
    "vendor",
    "mail",
    "webmail",
    "career",
    "jobs",
    "recruitment",
    "branch locator",
    "contact us",
    "become an advisor",
    "become an agent",
    "payment",
    "pay premium",
    "renew",
    "buy online",
    "apply now",
    "callback",
    "whatsapp",
    "app download",
    "playstore",
    "appstore",
]


class DiscoveryAgent:
    """
    Discovery Agent v0.2

    Discovers useful insurance URLs from captured HTML.

    Adds:
    - URL normalization
    - Tracking parameter removal
    - Semantic classification
    - Knowledge value
    - Crawl decision
    """

    def discover_from_html_file(
        self,
        insurer_id: str,
        source_url: str,
        html_path: str,
    ) -> list[dict]:

        html_file = Path(html_path)

        if not html_file.exists():
            raise FileNotFoundError(f"HTML file not found: {html_path}")

        html = html_file.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(html, "lxml")

        discovered = []

        for link in soup.find_all("a"):
            href = link.get("href")

            if not href:
                continue

            anchor_text = link.get_text(" ", strip=True)

            absolute_url = urljoin(source_url, href)
            normalized_url = self.normalize_url(absolute_url)

            if not self.is_valid_url(normalized_url):
                continue

            page_type = self.classify_url(
                url=normalized_url,
                anchor_text=anchor_text,
            )

            knowledge_value = self.assign_knowledge_value(page_type)

            crawl = knowledge_value in ["high", "medium"]

            priority = self.assign_priority(
                page_type=page_type,
                knowledge_value=knowledge_value,
            )

            discovered.append({
                "insurer_id": insurer_id,
                "source_url": source_url,
                "discovered_url": normalized_url,
                "anchor_text": anchor_text,
                "page_type": page_type,
                "knowledge_value": knowledge_value,
                "crawl": crawl,
                "priority": priority,
                "status": "new",
            })

        discovered = self.dedupe(discovered)

        # Save only useful URLs for now.
        useful = [
            item for item in discovered
            if item["crawl"] is True
        ]

        return useful

    def normalize_url(self, url: str) -> str:
        parsed = urlparse(url)

        query_pairs = parse_qsl(parsed.query, keep_blank_values=True)

        clean_query_pairs = [
            (key, value)
            for key, value in query_pairs
            if key.lower() not in TRACKING_PARAMS
        ]

        clean_query = urlencode(clean_query_pairs)

        cleaned = urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),
            parsed.path.rstrip("/") if parsed.path != "/" else parsed.path,
            "",
            clean_query,
            "",
        ))

        return cleaned.strip()

    def is_valid_url(self, url: str) -> bool:
        parsed = urlparse(url)

        if parsed.scheme not in ["http", "https"]:
            return False

        if not parsed.netloc:
            return False

        lower_url = url.lower()

        ignored_extensions = [
            ".jpg", ".jpeg", ".png", ".gif", ".svg",
            ".webp", ".css", ".js", ".ico", ".woff",
            ".woff2", ".ttf", ".mp4", ".mp3", ".zip"
        ]

        for ext in ignored_extensions:
            if lower_url.endswith(ext):
                return False

        return True

    def classify_url(self, url: str, anchor_text: str) -> str:
        text = f"{url} {anchor_text}".lower()

        if self.is_ignore_url(text):
            return "ignore"

        if ".pdf" in text:
            if "policy wording" in text or "wording" in text:
                return "policy_wording_pdf"

            if "brochure" in text:
                return "brochure_pdf"

            if "claim" in text:
                return "claim_form_pdf"

            if "proposal" in text:
                return "proposal_form_pdf"

            if "prospectus" in text:
                return "prospectus_pdf"

            if "customer information sheet" in text or "cis" in text:
                return "customer_information_sheet_pdf"

            return "pdf_document"

        if "withdrawn" in text:
            return "withdrawn_products"

        if "policy wording" in text or "wording" in text:
            return "policy_wording_page"

        if "brochure" in text:
            return "brochure_page"

        if "claim" in text:
            return "claim_process"

        if "download" in text:
            return "download_page"

        if "public disclosure" in text or "disclosure" in text:
            return "public_disclosure"

        if "irdai" in text or "regulatory" in text:
            return "regulatory"

        if "faq" in text or "faqs" in text:
            return "faq"

        if "calculator" in text:
            return "calculator"

        if "glossary" in text:
            return "glossary"

        if "uin" in text:
            return "uin_related"

        product_keywords = [
            "insurance",
            "plan",
            "policy",
            "term",
            "ulip",
            "endowment",
            "pension",
            "annuity",
            "health",
            "motor",
            "travel",
            "critical illness",
            "personal accident",
            "rider",
            "savings",
            "retirement",
            "child",
            "cancer",
            "cardiac",
            "diabetes",
        ]

        for keyword in product_keywords:
            if keyword in text:
                return "product_or_plan_page"

        education_keywords = [
            "what is",
            "benefits",
            "features",
            "tax",
            "guide",
            "knowledge",
            "article",
        ]

        for keyword in education_keywords:
            if keyword in text:
                return "knowledge_article"

        return "low_value_page"

    def is_ignore_url(self, text: str) -> bool:
        for keyword in IGNORE_KEYWORDS:
            if keyword in text:
                return True

        return False

    def assign_knowledge_value(self, page_type: str) -> str:
        high_value = {
            "policy_wording_pdf",
            "brochure_pdf",
            "customer_information_sheet_pdf",
            "proposal_form_pdf",
            "prospectus_pdf",
            "product_or_plan_page",
            "withdrawn_products",
            "uin_related",
            "policy_wording_page",
            "brochure_page",
        }

        medium_value = {
            "claim_process",
            "claim_form_pdf",
            "download_page",
            "public_disclosure",
            "regulatory",
            "faq",
            "calculator",
            "glossary",
            "knowledge_article",
            "pdf_document",
        }

        if page_type in high_value:
            return "high"

        if page_type in medium_value:
            return "medium"

        if page_type == "ignore":
            return "ignore"

        return "low"

    def assign_priority(
        self,
        page_type: str,
        knowledge_value: str,
    ) -> int:

        if knowledge_value == "high":
            return 1

        if knowledge_value == "medium":
            return 2

        if knowledge_value == "low":
            return 3

        return 99

    def dedupe(self, items: list[dict]) -> list[dict]:
        seen = set()
        unique = []

        for item in items:
            key = item["discovered_url"]

            if key not in seen:
                seen.add(key)
                unique.append(item)

        return unique

    def save_discovered_urls(
        self,
        insurer_id: str,
        discovered_urls: list[dict],
    ) -> Path:

        output_dir = BASE_DIR / "discovery" / "url_queue"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"{insurer_id}_discovered_urls.json"

        save_json(output_path, discovered_urls)

        return output_path