"""Generic repository-local source locator by immutable SHA-256.

This utility is onboarding plumbing only. It locates retained files under approved
repository roots by content hash; it does not infer document identity, currentness,
authority, facts, or publication state.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Iterable


class SourceHashLocatorError(ValueError):
    """Raised when source-hash localization input is unsafe or invalid."""


@dataclass(frozen=True)
class SourceHashMatch:
    sha256: str
    relative_path: str
    size_bytes: int


def _valid_sha(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())


def _safe_relative(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SourceHashLocatorError(f"{label} must be a non-empty string")
    raw = value.strip()
    if (
        Path(raw).is_absolute()
        or PurePosixPath(raw).is_absolute()
        or PureWindowsPath(raw).is_absolute()
        or raw.startswith("\\\\")
        or ":" in raw[:3]
        or ".." in PurePosixPath(raw).parts
        or ".." in PureWindowsPath(raw).parts
    ):
        raise SourceHashLocatorError(f"{label} must be a safe repository-relative path")
    return PurePosixPath(raw.replace("\\", "/")).as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class SourceHashLocator:
    """Find retained repository files matching one or more immutable hashes."""

    DEFAULT_SEARCH_ROOTS = ("archive", "knowledge")

    @classmethod
    def locate(
        cls,
        *,
        repository_root: str | Path,
        sha256_values: Iterable[str],
        search_roots: Iterable[str] | None = None,
    ) -> dict[str, list[SourceHashMatch]]:
        root = Path(repository_root).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"repository_root was not found: {root}")

        requested: list[str] = []
        for raw in sha256_values:
            if not isinstance(raw, str) or not _valid_sha(raw.strip().lower()):
                raise SourceHashLocatorError("each sha256 value must be a 64-character hexadecimal digest")
            value = raw.strip().lower()
            if value not in requested:
                requested.append(value)
        if not requested:
            raise SourceHashLocatorError("at least one sha256 value is required")

        roots = tuple(search_roots or cls.DEFAULT_SEARCH_ROOTS)
        resolved_roots: list[Path] = []
        for index, raw_search_root in enumerate(roots):
            relative = _safe_relative(raw_search_root, f"search_roots[{index}]")
            candidate = (root / relative).resolve()
            try:
                candidate.relative_to(root)
            except ValueError as exc:
                raise SourceHashLocatorError("search root must remain under repository_root") from exc
            if candidate.is_dir():
                resolved_roots.append(candidate)

        matches: dict[str, list[SourceHashMatch]] = {value: [] for value in requested}
        wanted = set(requested)
        seen_paths: set[Path] = set()
        for search_root in resolved_roots:
            for path in search_root.rglob("*"):
                if not path.is_file() or path in seen_paths:
                    continue
                seen_paths.add(path)
                digest = _sha256(path)
                if digest not in wanted:
                    continue
                relative = path.relative_to(root).as_posix()
                matches[digest].append(
                    SourceHashMatch(sha256=digest, relative_path=relative, size_bytes=path.stat().st_size)
                )

        for value in matches:
            matches[value].sort(key=lambda item: item.relative_path)
        return matches


__all__ = ["SourceHashLocator", "SourceHashLocatorError", "SourceHashMatch"]
