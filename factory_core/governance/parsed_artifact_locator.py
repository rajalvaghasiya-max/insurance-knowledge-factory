"""Read-only locator for parsed PDF JSON artifacts bound to one source SHA-256.

Phase-2 onboarding frequently starts from an immutable registered source version,
while parsed artifacts may live under different retained archive roots.  This
locator removes path guessing without inferring product identity, currentness,
facts, review decisions, or publication state.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable, Mapping


class ParsedArtifactLocatorError(ValueError):
    """Raised when locator inputs are unsafe or malformed."""


@dataclass(frozen=True)
class ParsedArtifactLocatorResult:
    manifest: Mapping[str, Any]


def _sha256(value: object) -> str:
    if not isinstance(value, str):
        raise ParsedArtifactLocatorError("source_sha256 must be a string")
    raw = value.strip().lower()
    if len(raw) != 64 or any(ch not in "0123456789abcdef" for ch in raw):
        raise ParsedArtifactLocatorError("source_sha256 must be a 64-character SHA-256 hex digest")
    return raw


def _safe_root(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ParsedArtifactLocatorError("search roots must be non-empty strings")
    raw = value.strip().replace("\\", "/")
    if (
        Path(raw).is_absolute()
        or PurePosixPath(raw).is_absolute()
        or PureWindowsPath(raw).is_absolute()
        or raw.startswith("//")
        or ":" in raw[:3]
        or ".." in PurePosixPath(raw).parts
        or ".." in PureWindowsPath(raw).parts
    ):
        raise ParsedArtifactLocatorError("search roots must be safe repository-relative paths")
    return PurePosixPath(raw).as_posix()


def _looks_like_parsed_artifact(document: object, source_sha256: str) -> tuple[bool, int]:
    if not isinstance(document, Mapping):
        return False, 0
    sha = document.get("sha256")
    pages = document.get("pages")
    if not isinstance(sha, str) or sha.strip().lower() != source_sha256 or not isinstance(pages, list):
        return False, 0
    valid_pages = sum(
        1
        for page in pages
        if isinstance(page, Mapping)
        and isinstance(page.get("page_number"), int)
        and page.get("page_number") > 0
        and isinstance(page.get("text"), str)
    )
    return True, valid_pages


class ParsedArtifactLocator:
    """Locate retained parsed-PDF JSON by immutable source SHA only."""

    DEFAULT_ROOTS = (
        "archive",
        "knowledge",
        "processed",
    )

    @classmethod
    def locate(
        cls,
        *,
        repository_root: str | Path,
        source_sha256: str,
        search_roots: Iterable[str] | None = None,
    ) -> ParsedArtifactLocatorResult:
        root = Path(repository_root).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"repository_root was not found: {root}")
        target_sha = _sha256(source_sha256)
        roots = tuple(_safe_root(item) for item in (search_roots or cls.DEFAULT_ROOTS))
        if not roots:
            raise ParsedArtifactLocatorError("at least one search root is required")

        matches: list[dict[str, Any]] = []
        scanned_json_files = 0
        skipped_invalid_json = 0
        for relative_root in dict.fromkeys(roots):
            search_root = (root / relative_root).resolve()
            try:
                search_root.relative_to(root)
            except ValueError as exc:
                raise ParsedArtifactLocatorError("search root must remain under repository_root") from exc
            if not search_root.is_dir():
                continue
            for path in sorted(search_root.rglob("*.json")):
                if path.is_symlink() or not path.is_file():
                    continue
                scanned_json_files += 1
                try:
                    document = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    skipped_invalid_json += 1
                    continue
                matched, valid_page_count = _looks_like_parsed_artifact(document, target_sha)
                if not matched:
                    continue
                relative = path.relative_to(root).as_posix()
                matches.append({
                    "path": relative,
                    "page_count": len(document["pages"]),
                    "valid_text_page_count": valid_page_count,
                    "entity_id": document.get("entity_id"),
                    "document_type": document.get("document_type"),
                    "source_document_id": document.get("source_document_id"),
                    "provenance_status": document.get("provenance_status"),
                })

        matches.sort(key=lambda item: item["path"])
        manifest = {
            "schema_version": "1.0",
            "locator_type": "parsed_pdf_artifact_sha_locator_v1",
            "locator_status": "located" if matches else "not_found",
            "source_sha256": target_sha,
            "search_roots": list(dict.fromkeys(roots)),
            "scanned_json_files": scanned_json_files,
            "skipped_invalid_json": skipped_invalid_json,
            "match_count": len(matches),
            "matches": matches,
            "guardrails": [
                "Localization is by immutable source SHA-256 and parsed-artifact shape only.",
                "A located parse artifact does not establish product identity, currentness, semantic correctness, review acceptance, or publication eligibility.",
                "This locator is read-only and does not mutate source, parsed, candidate, review, or fact artifacts.",
            ],
        }
        return ParsedArtifactLocatorResult(manifest=manifest)


__all__ = [
    "ParsedArtifactLocator",
    "ParsedArtifactLocatorError",
    "ParsedArtifactLocatorResult",
]
