"""Deterministic AR-2.5 repository-cleanup candidate audit.

This utility is intentionally conservative. It does not delete or move anything. It identifies
obvious backup/temp/generated-looking files and reports whether their path/text name is referenced
elsewhere in the repository so cleanup can be reviewed before physical deletion.

The audit is repository-structure tooling, not insurance intelligence.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import Iterable


DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
}

# High-confidence filename/path signals only. We deliberately do not classify files merely for
# being old, versioned, JSON, Markdown, or under historical packages.
BACKUP_TOKENS = (
    "_backup",
    ".backup",
    ".bak",
    "~",
    ".orig",
    ".rej",
)
TEMP_TOKENS = (
    ".tmp",
    ".temp",
    "_tmp",
    "_temp",
)
DUPLICATE_EXTENSION_TOKENS = (
    ".py.py",
    ".json.json",
    ".md.md",
    ".txt.txt",
)


@dataclass(frozen=True)
class CleanupCandidate:
    path: str
    category: str
    reason: str
    reference_count: int
    referenced_by: tuple[str, ...]

    @property
    def deletion_confidence(self) -> str:
        # Reference-free obvious backups/temp files are the only automatic HIGH candidates.
        if self.reference_count == 0 and self.category in {
            "BACKUP_COPY",
            "TEMPORARY_FILE",
            "DUPLICATE_EXTENSION",
        }:
            return "HIGH"
        return "REVIEW_REQUIRED"


def _iter_files(root: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in DEFAULT_EXCLUDED_DIRS for part in relative.parts):
            continue
        files.append(path)
    return tuple(sorted(files, key=lambda p: p.relative_to(root).as_posix()))


def _candidate_reason(relative: str) -> tuple[str, str] | None:
    lowered = relative.lower()
    name = Path(relative).name.lower()

    if any(token in name for token in DUPLICATE_EXTENSION_TOKENS):
        return ("DUPLICATE_EXTENSION", "filename contains a duplicated extension")
    if any(token in name for token in BACKUP_TOKENS):
        return ("BACKUP_COPY", "filename has an explicit backup/copy suffix")
    if any(token in name for token in TEMP_TOKENS):
        return ("TEMPORARY_FILE", "filename has an explicit temporary-file suffix")

    # IDE/editor artefacts are safe to flag but still require the same reference check.
    if name in {"thumbs.db", ".ds_store", "desktop.ini"}:
        return ("EDITOR_OS_ARTIFACT", "operating-system/editor artefact")
    if lowered.endswith(".swp") or lowered.endswith(".swo"):
        return ("EDITOR_OS_ARTIFACT", "editor swap file")
    return None


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def _references_for(
    *, root: Path, candidate: Path, all_files: Iterable[Path]
) -> tuple[str, ...]:
    relative = candidate.relative_to(root).as_posix()
    filename = candidate.name
    refs: list[str] = []
    for other in all_files:
        if other == candidate:
            continue
        text = _read_text(other)
        if text is None:
            continue
        if relative in text or filename in text:
            refs.append(other.relative_to(root).as_posix())
    return tuple(sorted(set(refs)))


def audit(root: Path) -> tuple[CleanupCandidate, ...]:
    root = root.resolve()
    all_files = _iter_files(root)
    candidates: list[CleanupCandidate] = []
    for path in all_files:
        relative = path.relative_to(root).as_posix()
        finding = _candidate_reason(relative)
        if finding is None:
            continue
        category, reason = finding
        references = _references_for(root=root, candidate=path, all_files=all_files)
        candidates.append(
            CleanupCandidate(
                path=relative,
                category=category,
                reason=reason,
                reference_count=len(references),
                referenced_by=references,
            )
        )
    return tuple(candidates)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit high-confidence repository cleanup candidates")
    parser.add_argument("--root", default=".", help="repository root (default: current directory)")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args()

    findings = audit(Path(args.root))
    if args.json:
        print(
            json.dumps(
                [
                    {
                        **asdict(item),
                        "deletion_confidence": item.deletion_confidence,
                    }
                    for item in findings
                ],
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    high = [item for item in findings if item.deletion_confidence == "HIGH"]
    review = [item for item in findings if item.deletion_confidence != "HIGH"]
    print("AR-2.5 REPOSITORY CLEANUP AUDIT")
    print(f"Candidates: {len(findings)} | HIGH deletion confidence: {len(high)} | Review: {len(review)}")
    for item in findings:
        print(
            f"[{item.deletion_confidence}] {item.path} | {item.category} | refs={item.reference_count}"
        )
        for ref in item.referenced_by:
            print(f"  referenced by: {ref}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
