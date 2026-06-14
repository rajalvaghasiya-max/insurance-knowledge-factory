import re
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urljoin, urldefrag, urlparse

from config.settings import BASE_DIR
from storage.registry_store import save_json


class PDFDiscoveryAgent:
    """
    PDF Discovery Agent v0.5.2

    Production quality improvements over v0.2:
    - Adds insurance relevance scoring
    - Adds noisy document filtering
    - Adds allowed-domain hints per insurer
    - Prevents raw regex over-capture from investor / financial / stock exchange pages
    - Adds confidence_score and skip_reason
    - Keeps only high-signal insurance documents in queue by default

    Inputs:
        archive/raw_html/<insurer_id>/*.html

    Outputs:
        discovery/pdf_queue/<insurer_id>_pdf_urls.json
        discovery/pdf_queue/_pdf_discovery_index.json
    """

    VERSION = "0.5.2"

    PDF_QUEUE_DIR = BASE_DIR / "discovery" / "pdf_queue"
    RAW_HTML_DIR = BASE_DIR / "archive" / "raw_html"

    # Keep v0.3 strict. We can loosen later if required.
    MIN_CONFIDENCE_TO_QUEUE = 35

    # v0.5.2:
    # Discovery must be offline and fast.
    # Do not perform HEAD/GET requests here.
    # URL verification will be handled by the PDF Download Agent.
    ENABLE_LIGHT_HTTP_VERIFICATION = False

    INSURER_DOMAIN_HINTS = {
        "aditya_birla_health": [
            "adityabirlacapital.com/healthinsurance",
            "healthinsuranceblob.abhicl.in",
        ],
        "bajaj_allianz_general": [
            "bajajgeneralinsurance.com/download-documents/health-insurance",
            "bajajgeneralinsurance.com/download-documents/claim",
        ],
        "hdfc_life": [
            "hdfclife.com/content/dam/hdfclifeinsurancecompany/products-page",
            "hdfclife.com/content/dam/hdfclifeinsurancecompany/customer-services",
        ],
        "lic_india": [
            "licindia.in/documents",
            "licindia.in/web",
            "licindia.in/",
        ],
        "star_health": [
            "starhealth.in",
            "starhealth.in/sites/default/files",
            "d28c6jni2fmamz.cloudfront.net",
        ],
    }

    HIGH_VALUE_DOCUMENT_TYPES = {
        "policy_wording",
        "customer_information_sheet",
        "brochure",
        "prospectus",
        "exclusion_annexure",
        "claim_form",
        "proposal_form",
    }

    INSURANCE_KEYWORDS = [
        "policy",
        "wording",
                    "policy_clause",
                    "policy-clause",
                    "policy clauses",
        "brochure",
        "prospectus",
        "customer information sheet",
        "cis",
        "claim",
        "proposal",
                    "application form",
                    "download proposal",
        "health insurance",
        "life insurance",
        "term insurance",
        "insurance",
        "product",
        "benefit",
        "coverage",
        "cover",
        "exclusion",
        "excluded",
        "non-medical expenses",
        "sum insured",
        "premium",
        "rider",
        "annexure",
        "hospital",
        "mediclaim",
        "renewal",
        "waiting period",
    ]

    NOISE_KEYWORDS = [
        "annual report",
        "audited financial",
        "financial result",
        "quarterly financial",
        "earnings call",
        "investor",
        "analyst meet",
        "press release",
        "newspaper publication",
        "agm",
        "postal ballot",
        "trading window",
        "record date",
        "stock exchange",
        "nse",
        "bse",
        "shareholder",
        "shareholding",
        "related party",
        "esop",
        "corporate governance",
        "board meeting",
        "composition of committees",
        "sustainability report",
        "brsr",
        "sexual harassment",
        "employee charter",
        "human rights",
        "partner code of conduct",
        "agent list",
        "active agent",
        "terminated agent",
        "cpi_pr",
        "mospi.gov.in",
        "privacy policy",
        "terms of use",
        "ombudsman notice board",
        "citizen charter",
        "grievance redressal policy",
        "grievance policy",
    ]

    def utc_now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def run(self) -> dict:
        self.PDF_QUEUE_DIR.mkdir(parents=True, exist_ok=True)

        if not self.RAW_HTML_DIR.exists():
            return {
                "status": "failed",
                "reason": f"Raw HTML directory not found: {self.RAW_HTML_DIR}",
            }

        overall_index = {
            "generated_at": self.utc_now_iso(),
            "agent": "pdf_discovery_agent",
            "agent_version": self.VERSION,
            "source_dir": str(self.RAW_HTML_DIR),
            "insurers": [],
            "total_pdf_urls": 0,
            "total_skipped_urls": 0,
        }

        insurer_results = []

        for insurer_folder in sorted(self.RAW_HTML_DIR.iterdir()):
            if not insurer_folder.is_dir():
                continue

            insurer_id = insurer_folder.name
            result = self.discover_for_insurer(insurer_id, insurer_folder)
            insurer_results.append(result)

            overall_index["insurers"].append(
                {
                    "insurer_id": insurer_id,
                    "html_files_scanned": result["html_files_scanned"],
                    "pdf_urls_found": result["pdf_urls_found"],
                    "pdf_urls_skipped": result["pdf_urls_skipped"],
                    "document_type_counts": result["document_type_counts"],
                    "skip_reason_counts": result["skip_reason_counts"],
                    "verification_counts": result.get("verification_counts", {}),
                    "output_file": result["output_file"],
                }
            )

            overall_index["total_pdf_urls"] += result["pdf_urls_found"]
            overall_index["total_skipped_urls"] += result["pdf_urls_skipped"]

        save_json(self.PDF_QUEUE_DIR / "_pdf_discovery_index.json", overall_index)

        return {
            "status": "completed",
            "insurers_scanned": len(insurer_results),
            "total_pdf_urls": overall_index["total_pdf_urls"],
            "total_skipped_urls": overall_index["total_skipped_urls"],
            "output_dir": str(self.PDF_QUEUE_DIR),
            "insurers": insurer_results,
        }

    def discover_for_insurer(self, insurer_id: str, insurer_folder: Path) -> dict:
        html_files = sorted(insurer_folder.glob("*.html"))
        discovered = {}
        skipped = {}

        for html_file in html_files:
            html = self.safe_read_text(html_file)
            if not html:
                continue

            base_url = self.detect_base_url(html) or self.infer_base_url_from_filename(html_file)
            page_is_noise = self.is_noise_source_page(base_url, html_file)

            links = self.extract_pdf_links(html)

            # v0.5.2 safety guard:
            # Investor pages may contain hundreds of raw PDF references.
            # Relevance scoring will still skip them, but we avoid excessive raw noise loops.
            links = self.limit_raw_regex_noise_links(
                links=links,
                insurer_id=insurer_id,
                source_page_url=base_url,
            )

            for link in links:
                raw_href = link.get("href", "")
                anchor_text = link.get("text", "")
                discovery_method = link.get("method", "unknown")

                normalized_url = self.normalize_url(raw_href, base_url)

                if not normalized_url or not self.is_pdf_url(normalized_url):
                    continue

                doc_type = self.classify_document_type(normalized_url, anchor_text)

                score_data = self.score_pdf_candidate(
                    insurer_id=insurer_id,
                    url=normalized_url,
                    anchor_text=anchor_text,
                    document_type=doc_type,
                    discovery_method=discovery_method,
                    source_page_url=base_url,
                    page_is_noise=page_is_noise,
                )

                key = normalized_url.lower()

                item = {
                    "insurer_id": insurer_id,
                    "url": normalized_url,
                    "document_type": doc_type,
                    "anchor_text": anchor_text,
                    "source_html_file": str(html_file),
                    "source_page_url": base_url,
                    "discovery_method": discovery_method,
                    "confidence_score": score_data["score"],
                    "confidence_reasons": score_data["reasons"],
                    "discovered_at": self.utc_now_iso(),
                    "status": "queued",
                    "priority": self.assign_priority(doc_type),
                }

                if not score_data["should_queue"]:
                    skipped[key] = {
                        **item,
                        "status": "skipped",
                        "skip_reason": score_data["skip_reason"],
                    }
                    continue

                if key not in discovered:
                    discovered[key] = item
                else:
                    existing = discovered[key]

                    if anchor_text and not existing.get("anchor_text"):
                        existing["anchor_text"] = anchor_text

                    better_doc_type = self.choose_better_document_type(
                        existing.get("document_type", "other_pdf"),
                        doc_type,
                    )

                    existing["document_type"] = better_doc_type
                    existing["priority"] = self.assign_priority(better_doc_type)

                    if score_data["score"] > existing.get("confidence_score", 0):
                        existing["confidence_score"] = score_data["score"]
                        existing["confidence_reasons"] = score_data["reasons"]

                    if discovery_method != "raw_pdf_regex":
                        existing["discovery_method"] = discovery_method

        queue_items = sorted(
            discovered.values(),
            key=lambda item: (
                item["priority"],
                -item["confidence_score"],
                item["document_type"],
                item["url"],
            ),
        )

        skipped_items = sorted(
            skipped.values(),
            key=lambda item: (
                item.get("skip_reason", ""),
                item["url"],
            ),
        )

        document_type_counts = self.count_by_document_type(queue_items)
        skip_reason_counts = self.count_by_skip_reason(skipped_items)
        verification_counts = {
            "verification_disabled": len(queue_items),
            "verified_pdf_like": 0,
            "not_verified_but_accepted": len(queue_items),
        }

        output_record = {
            "generated_at": self.utc_now_iso(),
            "agent": "pdf_discovery_agent",
            "agent_version": self.VERSION,
            "insurer_id": insurer_id,
            "html_files_scanned": len(html_files),
            "pdf_urls_found": len(queue_items),
            "pdf_urls_skipped": len(skipped_items),
            "document_type_counts": document_type_counts,
            "skip_reason_counts": skip_reason_counts,
            "verification_counts": verification_counts,
            "items": queue_items,
            "skipped_items_sample": skipped_items[:50],
        }

        output_file = self.PDF_QUEUE_DIR / f"{insurer_id}_pdf_urls.json"
        save_json(output_file, output_record)

        return {
            "insurer_id": insurer_id,
            "html_files_scanned": len(html_files),
            "pdf_urls_found": len(queue_items),
            "pdf_urls_skipped": len(skipped_items),
            "document_type_counts": document_type_counts,
            "skip_reason_counts": skip_reason_counts,
            "verification_counts": verification_counts,
            "output_file": str(output_file),
        }

    def limit_raw_regex_noise_links(
        self,
        links: list[dict],
        insurer_id: str,
        source_page_url: str,
    ) -> list[dict]:
        """
        v0.5.2:
        Keep structured links fully.
        Limit raw regex links only on known noise pages.
        """

        if not self.is_noise_source_page(source_page_url, Path(source_page_url.replace("/", "_"))):
            return links

        structured = [
            item for item in links
            if item.get("method") != "raw_pdf_regex"
        ]

        raw = [
            item for item in links
            if item.get("method") == "raw_pdf_regex"
        ]

        # For noise pages, raw links are usually investor/financial PDFs.
        # Keep only first 50 for audit/skipped sample; avoid processing 900+.
        raw_limited = raw[:50]

        return structured + raw_limited

    def score_pdf_candidate(
        self,
        insurer_id: str,
        url: str,
        anchor_text: str,
        document_type: str,
        discovery_method: str,
        source_page_url: str,
        page_is_noise: bool,
    ) -> dict:
        combined = f"{url} {anchor_text} {source_page_url}".lower()
        score = 0
        reasons = []

        if document_type in self.HIGH_VALUE_DOCUMENT_TYPES:
            score += 45
            reasons.append(f"high_value_document_type:{document_type}")
        elif document_type == "terms_conditions":
            score += 15
            reasons.append("terms_conditions")

        keyword_hits = self.find_keyword_hits(combined, self.INSURANCE_KEYWORDS, whole_word=False)
        if keyword_hits:
            boost = min(30, len(keyword_hits) * 5)
            score += boost
            reasons.append(f"insurance_keywords:{keyword_hits[:6]}")

        if self.matches_allowed_domain(insurer_id, url):
            score += 15
            reasons.append("allowed_domain_match")
        else:
            score -= 25
            reasons.append("allowed_domain_miss")

        noise_hits = self.find_keyword_hits(combined, self.NOISE_KEYWORDS, whole_word=True)
        if noise_hits:
            penalty = min(60, len(noise_hits) * 15)
            score -= penalty
            reasons.append(f"noise_keywords:{noise_hits[:6]}")

        if page_is_noise and discovery_method == "raw_pdf_regex":
            score -= 40
            reasons.append("raw_pdf_from_noise_page")

        if discovery_method == "raw_pdf_regex":
            score -= 5
            reasons.append("raw_regex_lower_trust")
        else:
            score += 5
            reasons.append("structured_link")

        # Star Health stores genuine and noisy PDFs on CloudFront.
        # v0.4 rejects only unknown CloudFront PDFs with no insurance signal.
        if (
            insurer_id == "star_health"
            and "d28c6jni2fmamz.cloudfront.net" in url.lower()
            and document_type == "other_pdf"
            and not keyword_hits
        ):
            score -= 50
            reasons.append("star_health_cloudfront_unknown_pdf_without_signal")

        if document_type == "other_pdf" and not keyword_hits:
            score -= 25
            reasons.append("other_pdf_without_insurance_keywords")

        score = max(0, min(100, score))

        should_queue = score >= self.MIN_CONFIDENCE_TO_QUEUE

        skip_reason = None
        if not should_queue:
            if noise_hits:
                skip_reason = "noise_document"
            elif not self.matches_allowed_domain(insurer_id, url):
                skip_reason = "domain_not_allowed"
            elif document_type == "other_pdf":
                skip_reason = "low_relevance_other_pdf"
            else:
                skip_reason = "low_confidence"

        return {
            "score": score,
            "reasons": reasons,
            "should_queue": should_queue,
            "skip_reason": skip_reason,
        }

    def matches_allowed_domain(self, insurer_id: str, url: str) -> bool:
        hints = self.INSURER_DOMAIN_HINTS.get(insurer_id, [])
        lower_url = url.lower()

        if not hints:
            return True

        return any(hint.lower() in lower_url for hint in hints)

    def is_noise_source_page(self, source_page_url: str, html_file: Path) -> bool:
        combined = f"{source_page_url} {html_file.name}".lower()

        noise_page_markers = [
            "investor",
            "financial-information",
            "disclosures",
            "company-policies",
            "sustainability",
            "about-us",
            "irda-public-disclosure",
        ]

        return any(marker in combined for marker in noise_page_markers)

    def safe_read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

    def detect_base_url(self, html: str) -> str:
        patterns = [
            r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']',
            r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:url["\']',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, flags=re.IGNORECASE)
            if match:
                url = match.group(1).strip()
                if url.startswith("http"):
                    return url

        return ""

    def infer_base_url_from_filename(self, html_file: Path) -> str:
        name = html_file.name
        if name.endswith(".html"):
            name = name[:-5]

        parts = name.split("_")
        if not parts:
            return ""

        domain = parts[0]
        if "." not in domain:
            return ""

        path = "/".join(part for part in parts[1:] if part)
        return f"https://{domain}/{path}" if path else f"https://{domain}/"

    def extract_pdf_links(self, html: str) -> list[dict]:
        links = []
        links.extend(self.extract_links_with_bs4(html))
        links.extend(self.extract_pdf_links_regex(html))
        links.extend(self.extract_pdf_urls_from_attributes(html))
        links.extend(self.extract_pdf_urls_from_onclick(html))
        links.extend(self.extract_pdf_urls_from_raw_text(html))
        return self.dedupe_link_candidates(links)

    def extract_links_with_bs4(self, html: str) -> list[dict]:
        try:
            from bs4 import BeautifulSoup  # type: ignore

            soup = BeautifulSoup(html, "html.parser")
            links = []
            candidate_attrs = [
                "href",
                "src",
                "data-url",
                "data-href",
                "data-file",
                "data-src",
                "data-download",
                "download-url",
            ]

            for tag in soup.find_all(True):
                text = " ".join(tag.get_text(" ", strip=True).split())

                for attr in candidate_attrs:
                    value = tag.get(attr)
                    if not value:
                        continue

                    value = str(value).strip()
                    if self.looks_like_document_candidate(value, text):
                        links.append(
                            {
                                "href": value,
                                "text": text,
                                "method": f"bs4_{attr}",
                            }
                        )

                onclick = tag.get("onclick")
                if onclick and ".pdf" in str(onclick).lower():
                    for url in self.extract_pdf_urls_from_string(str(onclick)):
                        links.append(
                            {
                                "href": url,
                                "text": text,
                                "method": "bs4_onclick",
                            }
                        )

            return links

        except Exception:
            return []

    def extract_pdf_links_regex(self, html: str) -> list[dict]:
        links = []
        anchor_pattern = re.compile(
            r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            flags=re.IGNORECASE | re.DOTALL,
        )

        for match in anchor_pattern.finditer(html):
            href = match.group(1).strip()
            text = self.strip_html(match.group(2))

            if self.looks_like_document_candidate(href, text):
                links.append(
                    {
                        "href": href,
                        "text": text,
                        "method": "regex_anchor_href",
                    }
                )

        return links

    def extract_pdf_urls_from_attributes(self, html: str) -> list[dict]:
        links = []
        attr_pattern = re.compile(
            r'(?:href|src|data-url|data-href|data-file|data-src|data-download|download-url)\s*=\s*["\']([^"\']*?\.pdf(?:\?[^"\']*)?)["\']',
            flags=re.IGNORECASE,
        )

        for match in attr_pattern.finditer(html):
            links.append(
                {
                    "href": match.group(1).strip(),
                    "text": "",
                    "method": "regex_attribute",
                }
            )

        return links

    def extract_pdf_urls_from_onclick(self, html: str) -> list[dict]:
        links = []
        onclick_pattern = re.compile(
            r'onclick\s*=\s*["\']([^"\']*?\.pdf[^"\']*)["\']',
            flags=re.IGNORECASE | re.DOTALL,
        )

        for match in onclick_pattern.finditer(html):
            for url in self.extract_pdf_urls_from_string(match.group(1)):
                links.append(
                    {
                        "href": url,
                        "text": "",
                        "method": "regex_onclick",
                    }
                )

        return links

    def extract_pdf_urls_from_raw_text(self, html: str) -> list[dict]:
        return [
            {
                "href": url,
                "text": "",
                "method": "raw_pdf_regex",
            }
            for url in self.extract_pdf_urls_from_string(html)
        ]

    def extract_pdf_urls_from_string(self, value: str) -> list[str]:
        urls = []

        absolute_pattern = re.compile(
            r'https?://[^\s"\'<>\\]+?\.pdf(?:\?[^\s"\'<>\\]*)?',
            flags=re.IGNORECASE,
        )

        for match in absolute_pattern.finditer(value):
            urls.append(match.group(0).strip())

        relative_pattern = re.compile(
            r'["\']([^"\']*?\.pdf(?:\?[^"\']*)?)["\']',
            flags=re.IGNORECASE,
        )

        for match in relative_pattern.finditer(value):
            candidate = match.group(1).strip()

            if candidate.startswith(("http://", "https://")):
                continue

            if candidate.lower().startswith(("javascript:", "mailto:", "tel:")):
                continue

            urls.append(candidate)

        return urls

    def looks_like_document_candidate(self, href: str, text: str) -> bool:
        """
        v0.4:
        Discover normal PDFs plus non-.pdf download/document handlers.
        This helps LIC-style document URLs and JavaScript download links.
        """

        href_l = str(href or "").lower()
        text_l = str(text or "").lower()
        combined = f"{href_l} {text_l}"

        if ".pdf" in combined:
            return True

        document_words = [
            "brochure",
            "policy wording",
            "policy document",
            "customer information sheet",
            "cis",
            "claim form",
            "proposal form",
            "prospectus",
            "download",
            "document",
            "form",
        ]

        handler_words = [
            "/documents/",
            "/download/",
            "download?",
            "downloadfile",
            "documentid=",
            "fileid=",
            "attachment",
        ]

        return (
            any(word in combined for word in document_words)
            and any(word in combined for word in handler_words)
        )

    def find_keyword_hits(
        self,
        text: str,
        keywords: list[str],
        whole_word: bool = False,
    ) -> list[str]:
        """
        v0.4:
        Avoid false matches like:
        'expenses' matching noise keyword 'nse'.
        """

        hits = []

        for keyword in keywords:
            keyword_l = keyword.lower().strip()

            if not keyword_l:
                continue

            if whole_word and re.fullmatch(r"[a-z0-9_]+", keyword_l):
                pattern = r"(?<![a-z0-9_])" + re.escape(keyword_l) + r"(?![a-z0-9_])"
                if re.search(pattern, text):
                    hits.append(keyword)
            else:
                if keyword_l in text:
                    hits.append(keyword)

        return hits

    def strip_html(self, value: str) -> str:
        value = re.sub(r"<[^>]+>", " ", value)
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    def dedupe_link_candidates(self, links: list[dict]) -> list[dict]:
        seen = set()
        unique = []

        for link in links:
            href = (link.get("href") or "").strip()
            text = (link.get("text") or "").strip()
            method = link.get("method", "unknown")

            if not href:
                continue

            marker = (href.lower(), text.lower(), method)

            if marker in seen:
                continue

            seen.add(marker)
            unique.append(
                {
                    "href": href,
                    "text": text,
                    "method": method,
                }
            )

        return unique

    def normalize_url(self, href: str, base_url: str) -> str:
        if not href:
            return ""

        href = href.strip().replace("\\/", "/").replace("&amp;", "&")

        if href.lower().startswith(("javascript:", "mailto:", "tel:")):
            return ""

        if href.startswith("//"):
            href = "https:" + href

        if not href.startswith("http"):
            if not base_url:
                return ""
            href = urljoin(base_url, href)

        href, _fragment = urldefrag(href)
        parsed = urlparse(href)

        if parsed.scheme not in {"http", "https"}:
            return ""

        return href.strip()

    def is_pdf_url(self, url: str) -> bool:
        """
        v0.4:
        Keep normal .pdf URLs.
        Also allow insurer download/document handlers where the URL may not end in .pdf,
        but clearly represents a downloadable document.
        """

        lower = url.lower()

        if ".pdf" in lower:
            return True

        document_handler_markers = [
            "/documents/",
            "/download/",
            "download?",
            "downloadfile",
            "download-document",
            "download-documents",
            "documentid=",
            "fileid=",
            "attachment",
        ]

        return any(marker in lower for marker in document_handler_markers)

    def classify_document_type(self, url: str, text: str) -> str:
        combined = f"{url} {text}".lower()

        rules = [
            (
                "exclusion_annexure",
                [
                    "excluded-items",
                    "excluded items",
                    "exclusion annexure",
                    "non-medical expenses",
                    "list_of_non-medical",
                    "list-of-non-medical",
                    "product-wise-specific-list-of-excluded-items",
                    "specific-list-of-excluded-items",
                ],
            ),
            (
                "customer_information_sheet",
                [
                    "customer information sheet",
                    "customer info sheet",
                    "customer-information-sheet",
                    "cis wordings",
                    "_cis.pdf",
                    "-cis.pdf",
                    "cis.pdf",
                    "/health-cis/",
                    "cis document",
                ],
            ),
            (
                "policy_wording",
                [
                    "policy-wording",
                    "policy wording",
                    "policywording",
                    "policy wordings",
                    "policy-document",
                    "policy document",
                    "/health-pw/",
                    "_pw.pdf",
                    "-pw.pdf",
                    "wording",
                    "policy_clause",
                    "policy-clause",
                    "policy clauses",
                ],
            ),
            ("brochure", [
                "brochure",
                "leaflet",
                "retail-brochure",
                "sales-brochure",
                "product-brochure",
                "star-comprehensive",
                "family-health-optima",
                "senior-citizens-red-carpet",
                "young-star",
                "super-surplus",
                "medi-classic",
                "health-assure",
            ]),
            ("prospectus", ["prospectus", "sales prospectus"]),
            (
                "claim_form",
                [
                    "claim form",
                    "claims form",
                    "claim-form",
                    "claimform",
                    "reimbursementform",
                    "reimbursement form",
                    "reimbursementforma",
                    "reimbursement",
                    "claims-form",
                    "claim document",
                    "death claim",
                    "maturity claim",
                    "surrender form",
                ],
            ),
            (
                "complaint_form",
                [
                    "complaint form",
                    "complain-form",
                    "complaint-registration",
                    "grievance form",
                    "grievance",
                ],
            ),
            (
                "proposal_form",
                [
                    "proposal-form",
                    "proposal form",
                    "proposalform",
                    "-pf.pdf",
                    "_pf.pdf",
                    "proposal",
                    "application form",
                    "download proposal",
                ],
            ),
            ("sales_literature", ["sales-literature", "sales literature"]),
            (
                "terms_conditions",
                [
                    "terms-condition",
                    "terms condition",
                    "terms-and-conditions",
                    "t-and-c",
                    "t&c",
                    "policy loan",
                ],
            ),
        ]

        for doc_type, keywords in rules:
            if any(keyword in combined for keyword in keywords):
                return doc_type

        return "other_pdf"

    def assign_priority(self, document_type: str) -> int:
        priorities = {
            "policy_wording": 1,
            "customer_information_sheet": 2,
            "brochure": 3,
            "prospectus": 4,
            "exclusion_annexure": 5,
            "claim_form": 6,
            "complaint_form": 7,
            "proposal_form": 8,
            "terms_conditions": 9,
            "sales_literature": 10,
            "other_pdf": 99,
        }

        return priorities.get(document_type, 99)

    def choose_better_document_type(self, existing: str, candidate: str) -> str:
        if self.assign_priority(candidate) < self.assign_priority(existing):
            return candidate

        return existing

    def count_by_document_type(self, items: list[dict]) -> dict:
        counts = {}

        for item in items:
            doc_type = item.get("document_type", "unknown")
            counts[doc_type] = counts.get(doc_type, 0) + 1

        return dict(sorted(counts.items()))

    def count_by_skip_reason(self, items: list[dict]) -> dict:
        counts = {}

        for item in items:
            reason = item.get("skip_reason", "unknown")
            counts[reason] = counts.get(reason, 0) + 1

        return dict(sorted(counts.items()))
