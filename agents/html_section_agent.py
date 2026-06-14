import re
from pathlib import Path
from datetime import datetime, timezone

from storage.registry_store import load_json, save_json
from config.settings import BASE_DIR


class HtmlSectionAgent:
    """
    HTML/Text Section Agent v0.2

    Reads preserved text files and creates:
    - cleaned text
    - filtered logical sections
    - smaller chunks for future extraction/embedding
    """

    def utc_now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def clean_text(self, text: str) -> str:
        lines = text.splitlines()
        cleaned_lines = []

        for line in lines:
            line = line.strip()

            if not line:
                continue

            line = re.sub(r"\s+", " ", line)

            if len(line) <= 2:
                continue

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def detect_sections(self, text: str) -> list[dict]:
        lines = text.splitlines()

        sections = []
        current_heading = "Introduction"
        current_lines = []

        for line in lines:
            if self.is_heading(line):
                if current_lines:
                    sections.append({
                        "heading": current_heading,
                        "text": "\n".join(current_lines).strip(),
                    })

                current_heading = line.strip()
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            sections.append({
                "heading": current_heading,
                "text": "\n".join(current_lines).strip(),
            })

        return sections

    def is_heading(self, line: str) -> bool:
        line = line.strip()

        if not line:
            return False

        if len(line) > 100:
            return False

        lower = line.lower()

        heading_keywords = [
            "overview",
            "features",
            "benefits",
            "eligibility",
            "coverage",
            "cover",
            "inclusions",
            "exclusions",
            "waiting period",
            "claim",
            "documents",
            "premium",
            "sum insured",
            "policy details",
            "plan details",
            "why choose",
            "faq",
            "frequently asked questions",
            "terms",
            "conditions",
            "brochure",
            "download",
            "riders",
            "add-ons",
            "additional covers",
            "tax benefits",
            "how to buy",
            "renewal",
            "grievance",
            "contact",
            "room rent",
            "co-pay",
            "deductible",
            "maternity",
            "pre-existing",
            "day care",
            "hospitalisation",
            "hospitalization",
            "ambulance",
            "cashless",
            "reimbursement",
            "network hospital",
            "health check",
        ]

        for keyword in heading_keywords:
            if keyword in lower:
                return True

        words = line.split()

        if 2 <= len(words) <= 9:
            title_words = sum(
                1 for word in words
                if word[:1].isupper()
            )

            if title_words >= max(2, len(words) - 1):
                return True

        return False

    def filter_noise_sections(self, sections: list[dict]) -> list[dict]:
        clean_sections = []

        for section in sections:
            heading = section.get("heading", "")
            text = section.get("text", "")

            if self.is_noise_section(heading, text):
                continue

            clean_sections.append(section)

        return clean_sections

    def is_noise_section(self, heading: str, text: str) -> bool:
        combined = f"{heading} {text}".lower().strip()

        noise_keywords = [
            "login",
            "renew",
            "become an advisor",
            "become an agent",
            "scan to download",
            "playstore",
            "appstore",
            "whatsapp",
            "customer wallet",
            "quick quote",
            "payment lounge",
            "pay bills",
            "career",
            "careers",
            "crm",
            "mail",
            "ess",
            "partner",
            "vendor invoice",
            "my space",
            "profile completion",
            "notifications are empty",
            "sign in",
            "download app",
            "download the app",
            "callback",
            "get a call back",
            "connect with us",
            "enter full name",
            "mobile number",
            "phone number",
            "email id",
            "branch locator",
            "privacy policy",
            "terms of usage",
            "confirmation alert",
            "logout",
            "select product",
            "submit",
            "play store",
            "app store",
        ]

        for keyword in noise_keywords:
            if keyword in combined:
                return True

        words = combined.split()

        if len(words) <= 5:
            return True

        return False

    def chunk_sections(
        self,
        sections: list[dict],
        max_chars: int = 2500,
    ) -> list[dict]:

        chunks = []

        for section_index, section in enumerate(sections):
            heading = section["heading"]
            text = section["text"]

            if not text:
                continue

            paragraphs = text.split("\n")
            current_chunk = ""

            for paragraph in paragraphs:
                if len(current_chunk) + len(paragraph) + 1 <= max_chars:
                    current_chunk += paragraph + "\n"
                else:
                    if current_chunk.strip():
                        chunks.append({
                            "section_index": section_index,
                            "heading": heading,
                            "text": current_chunk.strip(),
                        })

                    current_chunk = paragraph + "\n"

            if current_chunk.strip():
                chunks.append({
                    "section_index": section_index,
                    "heading": heading,
                    "text": current_chunk.strip(),
                })

        for index, chunk in enumerate(chunks):
            chunk["chunk_index"] = index
            chunk["character_count"] = len(chunk["text"])

        return chunks

    def parse_metadata_file(self, metadata_file: Path) -> dict:
        metadata = load_json(metadata_file, default={})

        if metadata.get("status") not in ["captured", "partial_capture"]:
            return {
                "status": "skipped",
                "reason": "metadata status is not captured",
                "metadata_file": str(metadata_file),
            }

        text_path = metadata.get("text_path")

        if not text_path:
            return {
                "status": "skipped",
                "reason": "text_path missing",
                "metadata_file": str(metadata_file),
            }

        text_file = Path(text_path)

        if not text_file.exists():
            return {
                "status": "skipped",
                "reason": "text file not found",
                "metadata_file": str(metadata_file),
                "text_path": text_path,
            }

        raw_text = text_file.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        cleaned_text = self.clean_text(raw_text)
        sections_before_filter = self.detect_sections(cleaned_text)
        sections = self.filter_noise_sections(sections_before_filter)
        chunks = self.chunk_sections(sections)

        insurer_id = metadata.get("insurer_id", "unknown")
        content_hash = metadata.get("content_hash", "unknown")

        output_dir = (
            BASE_DIR
            / "parsed"
            / "html_sections"
            / insurer_id
        )

        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"{content_hash}.json"

        parsed_record = {
            "source_metadata_file": str(metadata_file),
            "insurer_id": insurer_id,
            "url": metadata.get("url"),
            "page_title": metadata.get("page_title"),
            "content_hash": content_hash,
            "parsed_at": self.utc_now_iso(),
            "raw_character_count": len(raw_text),
            "cleaned_character_count": len(cleaned_text),
            "section_count_before_filter": len(sections_before_filter),
            "section_count": len(sections),
            "chunk_count": len(chunks),
            "sections": sections,
            "chunks": chunks,
        }

        save_json(output_path, parsed_record)

        return {
            "status": "parsed",
            "insurer_id": insurer_id,
            "url": metadata.get("url"),
            "output_path": str(output_path),
            "section_count_before_filter": len(sections_before_filter),
            "section_count": len(sections),
            "chunk_count": len(chunks),
        }