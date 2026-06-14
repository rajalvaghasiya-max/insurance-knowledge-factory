from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlunparse

from agents.discovery_agent import DiscoveryAgent
from config.settings import BASE_DIR
from storage.registry_store import load_json, save_json

try:
    from config.settings import SOURCE_REGISTRY_PATH
except Exception:
    SOURCE_REGISTRY_PATH = BASE_DIR / "registry" / "source_registry.json"


class SourceDiscoveryRunner:
    """
    Source Discovery Runner v0.7

    Purpose:
        Create discovered URL queues for non-insurer sources:
        - IRDAI
        - Bima Bharosa
        - Life Insurance Council
        - General Insurance Council

    Reads:
        registry/source_registry.json

    Writes:
        discovery/url_queue/<source_id>_discovered_urls.json

    Notes:
        Existing QueueCaptureAgent expects fields named:
        - insurer_id
        - discovered_url
        - crawl
        - status

        For compatibility, we set insurer_id = source_id.
        Additional source_* fields are also added for future separation.
    """

    VERSION = "0.7"

    def __init__(self):
        self.discovery_agent = DiscoveryAgent()
        self.queue_dir = BASE_DIR / "discovery" / "url_queue"
        self.metadata_dir = BASE_DIR / "archive" / "metadata"

        # v0.2 safety limits.
        # Regulatory / council sites can expose hundreds of navigation links.
        # We keep a curated queue for first production crawl.
        self.default_max_urls_per_source = 100
        self.max_urls_by_source = {
            "irdai": 100,
            "life_insurance_council": 75,
            "bima_bharosa": 25,
            "general_insurance_council": 50,
        }

        # v0.3 strict source boundary rules.
        # These prevent council pages from expanding into insurer/news websites.
        self.strict_allowed_domains_by_source = {
            "irdai": [
                "irdai.gov.in",
                "www.irdai.gov.in",
            ],
            "bima_bharosa": [
                "bimabharosa.irdai.gov.in",
                "irdai.gov.in",
                "www.irdai.gov.in",
            ],
            "life_insurance_council": [
                "lifeinscouncil.org",
                "www.lifeinscouncil.org",
                "sabsepehlelifeinsurance.com",
                "www.sabsepehlelifeinsurance.com",
            ],
            "general_insurance_council": [
                "gicouncil.in",
                "www.gicouncil.in",
                "idv.gicouncil.in",
            ],
        }

    def utc_now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def run(self) -> dict:
        self.queue_dir.mkdir(parents=True, exist_ok=True)

        sources = self.load_sources()

        summary = {
            "agent": "source_discovery_runner",
            "agent_version": self.VERSION,
            "generated_at": self.utc_now_iso(),
            "source_registry_path": str(SOURCE_REGISTRY_PATH),
            "sources_processed": 0,
            "total_queue_items": 0,
            "source_summaries": [],
        }

        print()
        print("=" * 70)
        print("SOURCE DISCOVERY RUN")
        print("=" * 70)
        print(f"Registry : {SOURCE_REGISTRY_PATH}")
        print(f"Sources  : {len(sources)}")
        print("=" * 70)

        for source in sources:
            if source.get("status", "active") != "active":
                continue

            if source.get("crawl_enabled", True) is False:
                continue

            source_summary = self.process_source(source)
            summary["sources_processed"] += 1
            summary["total_queue_items"] += source_summary["queue_items"]
            summary["source_summaries"].append(source_summary)

            print(
                f"{source_summary['source_id']}: "
                f"seed={source_summary['seed_items']} "
                f"discovered={source_summary['discovered_items']} "
                f"queue={source_summary['queue_items']} "
                f"limit={source_summary['max_urls_per_source']} "
                f"saved={source_summary['output_file']}"
            )

        print()
        print("=" * 70)
        print("SOURCE DISCOVERY SUMMARY")
        print("=" * 70)
        print(f"Sources processed : {summary['sources_processed']}")
        print(f"Total queue items : {summary['total_queue_items']}")
        print("=" * 70)

        return summary

    def load_sources(self) -> list[dict]:
        registry = load_json(SOURCE_REGISTRY_PATH, default=[])

        # Current project format:
        # [
        #   {"source_id": "...", ...}
        # ]
        if isinstance(registry, list):
            return registry

        # Future grouped format:
        # {
        #   "source_groups": {
        #      "regulators": {"sources": [...]}
        #   }
        # }
        if isinstance(registry, dict):
            if "sources" in registry and isinstance(registry["sources"], list):
                return registry["sources"]

            source_groups = registry.get("source_groups", {})
            if isinstance(source_groups, dict):
                sources = []

                for group_name, group_data in source_groups.items():
                    group_sources = group_data.get("sources", [])

                    for source in group_sources:
                        item = dict(source)
                        item.setdefault("source_group", group_name)
                        sources.append(item)

                return sources

        raise ValueError(
            f"Unsupported source_registry.json structure: {SOURCE_REGISTRY_PATH}"
        )

    def process_source(self, source: dict) -> dict:
        source_id = source["source_id"]
        source_type = source.get("source_type", "unknown")
        storage_layer = source.get("storage_layer", "market_intelligence")
        crawl_frequency = source.get("crawl_frequency", "monthly")
        allowed_domains = self.get_effective_allowed_domains(source)

        seed_items = self.create_seed_queue_items(
            source=source,
            allowed_domains=allowed_domains,
        )

        discovered_items = self.discover_from_existing_captures(
            source=source,
            allowed_domains=allowed_domains,
        )

        all_items = seed_items + discovered_items
        all_items = self.dedupe_merge_with_existing(
            source_id=source_id,
            new_items=all_items,
        )

        all_items = self.filter_and_limit_source_queue(
            source=source,
            items=all_items,
        )

        output_file = self.queue_dir / f"{source_id}_discovered_urls.json"
        save_json(output_file, all_items)

        return {
            "source_id": source_id,
            "source_type": source_type,
            "storage_layer": storage_layer,
            "crawl_frequency": crawl_frequency,
            "seed_items": len(seed_items),
            "discovered_items": len(discovered_items),
            "queue_items": len(all_items),
            "max_urls_per_source": int(
                source.get(
                    "max_urls_per_source",
                    self.max_urls_by_source.get(
                        source_id,
                        self.default_max_urls_per_source,
                    ),
                )
            ),
            "output_file": str(output_file),
        }

    def repair_malformed_external_url(self, url: str) -> str:
        """
        v0.7:
        Repair common malformed external links produced when HTML has href like:
        - policyholder.gov.in
        - www.example.org
        - //example.org/path

        This prevents bad URLs like:
        https://www.gicouncil.in/policyholder.gov.in
        """

        if not url:
            return url

        raw = url.strip()

        if raw.startswith("//"):
            return "https:" + raw

        if raw.startswith(("http://", "https://")):
            parsed = urlparse(raw)
            path = parsed.path or ""

            # Pattern:
            # https://www.gicouncil.in/policyholder.gov.in
            # should become:
            # https://policyholder.gov.in
            path_part = path.strip("/")

            if (
                parsed.netloc.endswith("gicouncil.in")
                and "." in path_part
                and "/" not in path_part
                and not path_part.lower().endswith((".pdf", ".aspx", ".html"))
            ):
                return f"https://{path_part}"

            return raw

        if (
            "." in raw
            and not raw.startswith(("/", "#"))
            and not raw.lower().startswith(("mailto:", "tel:", "javascript:"))
        ):
            return "https://" + raw

        return raw

    def is_low_value_event_or_news_url(
        self,
        url: str,
        anchor_text: str,
    ) -> bool:
        """
        v0.7:
        Avoid letting source crawls become news/event crawls.
        We keep regulatory/council knowledge pages, not every press item.
        """

        text = f"{url} {anchor_text}".lower()
        anchor = (anchor_text or "").strip().lower()

        low_value_anchors = {
            "read more",
            "read more...",
            "learn more",
            "view details",
            "click here",
        }

        if anchor in low_value_anchors:
            if "/news-media/" in text or "/events/" in text or "/media_center/" in text:
                return True

        low_value_paths = [
            "/news-media/events/",
            "/media_center/latestnews",
            "/media_center/pressrelease",
            "/photo-gallery",
            "/video-gallery",
        ]

        return any(fragment in text for fragment in low_value_paths)

    def get_effective_allowed_domains(self, source: dict) -> list[str]:
        """
        v0.3:
        Prefer strict source boundary domains.
        This prevents council crawls from becoming insurer/news crawls.
        """

        source_id = source["source_id"]

        strict_domains = self.strict_allowed_domains_by_source.get(source_id)

        if strict_domains:
            return strict_domains

        return source.get("allowed_domains", [])

    def create_seed_queue_items(
        self,
        source: dict,
        allowed_domains: list[str],
    ) -> list[dict]:
        source_id = source["source_id"]
        source_type = source.get("source_type", "unknown")
        storage_layer = source.get("storage_layer", "market_intelligence")
        crawl_frequency = source.get("crawl_frequency", "monthly")

        items = []

        for seed_url in source.get("seed_urls", []):
            seed_url = self.repair_malformed_external_url(seed_url)
            normalized_url = self.discovery_agent.normalize_url(seed_url)

            if not self.discovery_agent.is_valid_url(normalized_url):
                continue

            if not self.is_allowed_domain(normalized_url, allowed_domains):
                continue

            page_type = self.classify_source_url(normalized_url, "", source_type)
            knowledge_value = self.assign_source_knowledge_value(page_type)

            items.append(
                {
                    # Compatibility with QueueCaptureAgent
                    "insurer_id": source_id,
                    "source_url": source.get("website", seed_url),
                    "discovered_url": normalized_url,
                    "anchor_text": source.get("name", source_id),
                    "page_type": page_type,
                    "knowledge_value": knowledge_value,
                    "crawl": True,
                    "priority": source.get("crawl_priority", source.get("priority", 2)),
                    "status": "new",

                    # Source metadata
                    "source_id": source_id,
                    "source_name": source.get("name", source.get("display_name", source_id)),
                    "source_type": source_type,
                    "storage_layer": storage_layer,
                    "crawl_frequency": crawl_frequency,
                    "discovery_origin": "seed_url",
                    "created_at": self.utc_now_iso(),
                }
            )

        return items

    def discover_from_existing_captures(
        self,
        source: dict,
        allowed_domains: list[str],
    ) -> list[dict]:
        source_id = source["source_id"]
        source_type = source.get("source_type", "unknown")
        storage_layer = source.get("storage_layer", "market_intelligence")
        crawl_frequency = source.get("crawl_frequency", "monthly")

        source_metadata_dir = self.metadata_dir / source_id

        if not source_metadata_dir.exists():
            return []

        discovered_all = []

        for metadata_file in sorted(source_metadata_dir.glob("*.json")):
            metadata = load_json(metadata_file, default={})

            if metadata.get("status") not in ["captured", "partial_capture"]:
                continue

            html_path = metadata.get("html_path")
            source_url = metadata.get("url")

            if not html_path or not source_url:
                continue

            try:
                discovered = self.discovery_agent.discover_from_html_file(
                    insurer_id=source_id,
                    source_url=source_url,
                    html_path=html_path,
                )
            except Exception as exc:
                print(f"Discovery failed for {metadata_file}: {exc}")
                continue

            for item in discovered:
                url = item.get("discovered_url", "")
                repaired_url = self.repair_malformed_external_url(url)

                if repaired_url != url:
                    item["original_discovered_url"] = url
                    item["discovered_url"] = repaired_url
                    url = repaired_url

                if not self.is_allowed_domain(url, allowed_domains):
                    continue

                item["source_id"] = source_id
                item["source_name"] = source.get("name", source.get("display_name", source_id))
                item["source_type"] = source_type
                item["storage_layer"] = storage_layer
                item["crawl_frequency"] = crawl_frequency
                item["discovery_origin"] = "captured_html"
                item["created_at"] = item.get("created_at", self.utc_now_iso())

                # Reclassify for regulatory / industry pages where useful.
                item["page_type"] = self.classify_source_url(
                    url,
                    item.get("anchor_text", ""),
                    source_type,
                )
                item["knowledge_value"] = self.assign_source_knowledge_value(
                    item["page_type"]
                )
                item["crawl"] = item["knowledge_value"] in ["high", "medium"]
                item["priority"] = self.assign_source_priority(
                    item["page_type"],
                    item["knowledge_value"],
                    source.get("crawl_priority", source.get("priority", 2)),
                )

                discovered_all.append(item)

        return discovered_all

    def source_noise_skip_reason(
        self,
        url: str,
        anchor_text: str,
    ) -> str | None:
        """
        v0.5:
        Remove structural/navigation URLs that do not carry standalone knowledge.

        Main target:
        - IRDAI Liferay pagination/sort URLs
        - numeric pagination anchors
        - sortable table header anchors
        """

        url = self.repair_malformed_external_url(url)
        parsed = urlparse(url)
        query_text = parsed.query.lower()
        anchor = (anchor_text or "").strip().lower()

        pagination_or_sort_params = [
            "_com_irdai_document_media_irdaidocumentmediaportlet_cur",
            "_com_irdai_document_media_irdaidocumentmediaportlet_delta",
            "_com_irdai_document_media_irdaidocumentmediaportlet_orderbycol",
            "_com_irdai_document_media_irdaidocumentmediaportlet_orderbytype",
            "_com_irdai_document_media_irdaidocumentmediaportlet_resetcur",
            "p_p_id=com_irdai_document_media_irdaidocumentmediaportlet",
        ]

        if any(param in query_text for param in pagination_or_sort_params):
            return "irdai_pagination_or_sort_url"

        # Fallback using parsed query keys.
        query = parse_qs(parsed.query)
        noisy_query_keys = {
            "_com_irdai_document_media_IRDAIDocumentMediaPortlet_cur",
            "_com_irdai_document_media_IRDAIDocumentMediaPortlet_delta",
            "_com_irdai_document_media_IRDAIDocumentMediaPortlet_orderByCol",
            "_com_irdai_document_media_IRDAIDocumentMediaPortlet_orderByType",
            "_com_irdai_document_media_IRDAIDocumentMediaPortlet_resetCur",
        }

        if any(key in query for key in noisy_query_keys):
            return "irdai_pagination_or_sort_query_key"

        bad_anchor_texts = {
            "sub title",
            "short description",
            "documents",
            "last updated",
            "last",
            "last →",
            "next",
            "next →",
            "previous",
            "previous →",
            "first",
            "first →",
            "view all",
            "skip to content",
            "skip main content",
            "skip-main-content",
        }

        if anchor in bad_anchor_texts:
            return "table_or_navigation_anchor"

        if anchor.isdigit():
            return "numeric_pagination_anchor"

        # Common pagination strings like "1 2 3" are not useful anchors.
        compact_anchor = anchor.replace(" ", "")
        if compact_anchor.isdigit() and len(compact_anchor) <= 4:
            return "numeric_pagination_anchor"

        return None

    def is_allowed_for_bima_bharosa(
        self,
        url: str,
        anchor_text: str,
    ) -> bool:
        """
        v0.4:
        Bima Bharosa may link to IRDAI pages.
        We only keep IRDAI links that are grievance / complaint / policyholder related.
        We do not let Bima Bharosa become a full IRDAI regulatory crawl.
        """

        parsed = urlparse(url)
        host = parsed.netloc.lower()
        text = f"{url} {anchor_text}".lower()

        if host in {"bimabharosa.irdai.gov.in"}:
            return True

        if host in {"irdai.gov.in", "www.irdai.gov.in"}:
            grievance_keywords = [
                "grievance",
                "complaint",
                "complaints",
                "policyholder",
                "policy-holder",
                "policyholders",
                "consumer",
                "gro",
                "gros",
                "redressal",
                "ombudsman",
                "bima-bharosa",
                "bimabharosa",
                "about-consumer-affairs",
                "list-of-gros",
            ]

            return any(keyword in text for keyword in grievance_keywords)

        return False

    def filter_and_limit_source_queue(
        self,
        source: dict,
        items: list[dict],
    ) -> list[dict]:
        """
        v0.2:
        Remove low-value/noisy URLs and cap per source.
        Always keep seed URLs.
        """

        source_id = source["source_id"]
        max_urls = int(
            source.get(
                "max_urls_per_source",
                self.max_urls_by_source.get(
                    source_id,
                    self.default_max_urls_per_source,
                ),
            )
        )

        filtered = []

        for item in items:
            url = item.get("discovered_url", "")
            repaired_url = self.repair_malformed_external_url(url)

            if repaired_url != url:
                item["original_discovered_url"] = url
                item["discovered_url"] = repaired_url
                url = repaired_url

            anchor_text = item.get("anchor_text", "")
            origin = item.get("discovery_origin", "")

            if origin == "seed_url":
                item["queue_reason"] = "seed_url"
                filtered.append(item)
                continue

            noise_reason = self.source_noise_skip_reason(url, anchor_text)

            if noise_reason:
                item["crawl"] = False
                item["status"] = "skipped"
                item["skip_reason"] = noise_reason
                continue

            if self.is_low_value_event_or_news_url(url, anchor_text):
                item["crawl"] = False
                item["status"] = "skipped"
                item["skip_reason"] = "low_value_news_or_event_url"
                continue

            if source_id == "bima_bharosa":
                if not self.is_allowed_for_bima_bharosa(url, anchor_text):
                    item["crawl"] = False
                    item["status"] = "skipped"
                    item["skip_reason"] = "bima_bharosa_non_grievance_irdai_link"
                    continue

            if not self.is_allowed_domain(
                url,
                self.get_effective_allowed_domains(source),
            ):
                item["crawl"] = False
                item["status"] = "skipped"
                item["skip_reason"] = "outside_source_boundary"
                continue

            skip_reason = self.source_skip_reason(url, anchor_text)

            if skip_reason:
                item["crawl"] = False
                item["status"] = "skipped"
                item["skip_reason"] = skip_reason
                continue

            knowledge_value = item.get("knowledge_value", "low")

            if knowledge_value not in {"high", "medium"}:
                item["crawl"] = False
                item["status"] = "skipped"
                item["skip_reason"] = "low_knowledge_value"
                continue

            item["queue_reason"] = f"{knowledge_value}_value_source_url"
            filtered.append(item)

        filtered = sorted(
            filtered,
            key=lambda x: (
                0 if x.get("discovery_origin") == "seed_url" else 1,
                x.get("priority", 99),
                self.source_url_score(x),
                x.get("discovered_url", ""),
            ),
        )

        seeds = [item for item in filtered if item.get("discovery_origin") == "seed_url"]
        non_seeds = [item for item in filtered if item.get("discovery_origin") != "seed_url"]

        remaining_slots = max(0, max_urls - len(seeds))
        return seeds + non_seeds[:remaining_slots]

    def source_skip_reason(self, url: str, anchor_text: str) -> str | None:
        text = f"{url} {anchor_text}".lower()

        noisy_fragments = [
            "facebook.com",
            "twitter.com",
            "x.com/",
            "linkedin.com",
            "youtube.com",
            "instagram.com",
            "mailto:",
            "tel:",
            "javascript:",
            "#",
            "/contact",
            "contact-us",
            "privacy",
            "terms",
            "disclaimer",
            "sitemap",
            "site-map",
            "login",
            "signin",
            "sign-in",
            "register",
            "career",
            "jobs",
            "tender",
            "procurement",
            "gallery",
            "photo",
            "video",
            "feedback",
            "faq",
            "faqs",
            "search",
            "font-size",
            "screen-reader",
            "skip-main-content",
            "archive/old",
            "nri-",
            "/ae/",
            "/au/",
            "/ca/",
            "/uk/",
            "premium-calculator",
            "premium-calculators",
            "tools-and-calculators",
            "human-life-value-calculator",
            "retirement-calculator",
            "/news-media/events/",
            "/media_center/latestnews",
            "/photo-gallery",
            "/video-gallery",
        ]

        for fragment in noisy_fragments:
            if fragment in text:
                return f"noise_fragment:{fragment}"

        static_extensions = [
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".svg",
            ".webp",
            ".ico",
            ".css",
            ".js",
            ".woff",
            ".ttf",
        ]

        if any(ext in text for ext in static_extensions):
            return "static_asset"

        return None

    def source_url_score(self, item: dict) -> int:
        """
        Lower score is better for sorting.
        """

        page_type = item.get("page_type", "")
        knowledge_value = item.get("knowledge_value", "")
        url = item.get("discovered_url", "").lower()
        anchor = item.get("anchor_text", "").lower()
        text = f"{url} {anchor}"

        score = 100

        if knowledge_value == "high":
            score -= 40
        elif knowledge_value == "medium":
            score -= 20

        priority_types = {
            "regulatory_circular_pdf": 50,
            "regulatory_circular_page": 48,
            "regulation_pdf": 45,
            "regulation_or_guideline_page": 42,
            "insurer_directory": 40,
            "fund_nav": 35,
            "industry_report_pdf": 30,
            "public_disclosure": 25,
            "consumer_grievance": 20,
        }

        score -= priority_types.get(page_type, 0)

        important_keywords = [
            "circular",
            "regulation",
            "guideline",
            "master-circular",
            "insurers",
            "listofcompanies",
            "list-of-companies",
            "nav",
            "public disclosure",
            "annual report",
            "handbook",
            "claim",
            "complaint",
            "complaints",
            "grievance",
            "redressal",
            "policyholder",
            "consumer",
            "gro",
            "ombudsman",
        ]

        for keyword in important_keywords:
            if keyword in text:
                score -= 5

        return score

    def classify_source_url(
        self,
        url: str,
        anchor_text: str,
        source_type: str,
    ) -> str:
        text = f"{url} {anchor_text}".lower()

        if ".pdf" in text:
            if "circular" in text:
                return "regulatory_circular_pdf"
            if "regulation" in text:
                return "regulation_pdf"
            if "annual report" in text or "report" in text:
                return "industry_report_pdf"
            return "source_pdf_document"

        if "circular" in text or "master-circular" in text or "circulars" in text:
            return "regulatory_circular_page"

        if "regulation" in text or "guideline" in text:
            return "regulation_or_guideline_page"

        if "insurers" in text or "listofcompanies" in text or "list-of-companies" in text:
            return "insurer_directory"

        if "fund_nav" in text or "list_of_fund_navs" in text or "list-of-fund-navs" in text:
            return "fund_nav"

        if "complaint" in text or "grievance" in text or "bima bharosa" in text:
            return "consumer_grievance"

        if "public disclosure" in text or "disclosure" in text:
            return "public_disclosure"

        if source_type == "regulator":
            return "regulatory_source_page"

        if source_type == "industry_body":
            return "industry_source_page"

        return "source_page"

    def assign_source_knowledge_value(self, page_type: str) -> str:
        high_value = {
            "regulatory_circular_pdf",
            "regulation_pdf",
            "regulatory_circular_page",
            "regulation_or_guideline_page",
            "insurer_directory",
            "fund_nav",
        }

        medium_value = {
            "industry_report_pdf",
            "source_pdf_document",
            "consumer_grievance",
            "public_disclosure",
            "regulatory_source_page",
            "industry_source_page",
            "source_page",
        }

        if page_type in high_value:
            return "high"

        if page_type in medium_value:
            return "medium"

        return "low"

    def assign_source_priority(
        self,
        page_type: str,
        knowledge_value: str,
        default_priority: int,
    ) -> int:
        if page_type in {
            "regulatory_circular_pdf",
            "regulatory_circular_page",
            "regulation_pdf",
            "regulation_or_guideline_page",
        }:
            return 1

        if page_type in {"insurer_directory", "fund_nav"}:
            return 1

        if knowledge_value == "high":
            return min(default_priority, 2)

        if knowledge_value == "medium":
            return max(default_priority, 2)

        return 99

    def is_allowed_domain(
        self,
        url: str,
        allowed_domains: list[str],
    ) -> bool:
        if not allowed_domains:
            return True

        parsed = urlparse(url)
        host = parsed.netloc.lower()
        full = f"{host}{parsed.path}".lower()

        for allowed in allowed_domains:
            allowed_l = allowed.lower().replace("https://", "").replace("http://", "").strip("/")

            if host == allowed_l:
                return True

            if host.endswith("." + allowed_l):
                return True

            if allowed_l in full:
                return True

        return False

    def normalize_url_for_source_dedupe(self, url: str) -> str:
        """
        v0.6:
        Normalize obvious URL variants before dedupe.

        We intentionally do not collapse document-detail URLs and PDF download URLs yet,
        because both can be useful for regulatory provenance.

        Added:
        - IRDAI /web/guest path normalization
        - HTTP → HTTPS normalization for known source domains
        - www host normalization for selected source domains
        """

        url = self.repair_malformed_external_url(url)
        parsed = urlparse(url)
        host = parsed.netloc.lower().strip()
        path = parsed.path.rstrip("/")

        # Prefer https for known official/approved source domains.
        https_preferred_hosts = {
            "irdai.gov.in",
            "www.irdai.gov.in",
            "bimabharosa.irdai.gov.in",
            "lifeinscouncil.org",
            "www.lifeinscouncil.org",
            "sabsepehlelifeinsurance.com",
            "www.sabsepehlelifeinsurance.com",
            "gicouncil.in",
            "www.gicouncil.in",
            "idv.gicouncil.in",
        }

        scheme = "https" if host in https_preferred_hosts else (parsed.scheme.lower() or "https")

        # Normalize www for controlled domains where both variants occur.
        www_to_root = {
            "www.irdai.gov.in": "irdai.gov.in",
            "www.lifeinscouncil.org": "lifeinscouncil.org",
            "www.sabsepehlelifeinsurance.com": "sabsepehlelifeinsurance.com",
            "www.gicouncil.in": "gicouncil.in",
        }

        host = www_to_root.get(host, host)

        # IRDAI exposes same document detail pages in both formats:
        # /web/guest/document-detail?documentId=...
        # /document-detail?documentId=...
        if host == "irdai.gov.in" and path.startswith("/web/guest"):
            path = path.replace("/web/guest", "", 1) or "/"

        normalized = f"{scheme}://{host}{path}"

        # Keep meaningful query params like documentId, version, download.
        # Drop known noisy IRDAI/Liferay pagination params.
        query = parse_qs(parsed.query, keep_blank_values=True)
        noisy_query_keys = {
            "_com_irdai_document_media_IRDAIDocumentMediaPortlet_cur",
            "_com_irdai_document_media_IRDAIDocumentMediaPortlet_delta",
            "_com_irdai_document_media_IRDAIDocumentMediaPortlet_orderByCol",
            "_com_irdai_document_media_IRDAIDocumentMediaPortlet_orderByType",
            "_com_irdai_document_media_IRDAIDocumentMediaPortlet_resetCur",
            "p_p_id",
            "p_p_lifecycle",
            "p_p_state",
            "p_p_mode",
        }

        clean_pairs = []

        for key, values in query.items():
            if key in noisy_query_keys:
                continue

            for value in values:
                clean_pairs.append((key, value))

        # Stable ordering avoids duplicate keys due to query param order.
        clean_pairs = sorted(clean_pairs, key=lambda x: (x[0], x[1]))

        if clean_pairs:
            from urllib.parse import urlencode
            normalized = normalized + "?" + urlencode(clean_pairs)

        return normalized

    def dedupe_merge_with_existing(
        self,
        source_id: str,
        new_items: list[dict],
    ) -> list[dict]:
        output_file = self.queue_dir / f"{source_id}_discovered_urls.json"
        existing_items = load_json(output_file, default=[])

        by_url = {}

        # Keep existing status/capture metadata where present.
        for item in existing_items:
            url = item.get("discovered_url")
            if url:
                key = self.normalize_url_for_source_dedupe(url)
                by_url[key] = item

        for item in new_items:
            url = item.get("discovered_url")
            if not url:
                continue

            key = self.normalize_url_for_source_dedupe(url)
            item["dedupe_key"] = key

            if key in by_url:
                existing = by_url[key]
                preserved_fields = {
                    "status",
                    "last_attempted_at",
                    "capture_count",
                    "last_capture_hash",
                    "last_capture_strategy",
                    "last_capture_status",
                    "last_error",
                }

                merged = dict(item)

                for field in preserved_fields:
                    if field in existing:
                        merged[field] = existing[field]

                by_url[key] = merged
            else:
                by_url[key] = item

        return sorted(
            by_url.values(),
            key=lambda x: (
                x.get("priority", 99),
                x.get("source_id", ""),
                x.get("discovered_url", ""),
            ),
        )


def run_source_discovery():
    runner = SourceDiscoveryRunner()
    return runner.run()


if __name__ == "__main__":
    run_source_discovery()
