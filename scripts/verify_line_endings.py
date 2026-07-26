#!/usr/bin/env python3
"""MO-011 — narrowly scoped line-ending validation.

Read-only. Does not modify, regenerate, or normalize any file. Checks:

1. The Star generic source bundle involved in the MO-010/MO-011
   incident is classified by Git as LF-controlled text
   (via `git check-attr`), and
2. its current working-tree bytes contain no CRLF sequences.

A general sweep is also offered (--all) to list any tracked file
under a `.gitattributes`-covered extension that currently contains
CRLF bytes, for visibility only -- it does not fail the primary
check and does not alter anything.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

STAR_BUNDLE_PATH = (
    "knowledge/factory/registry_backed/star_health_star_comprehensive/"
    "generic_source_registration/star_health_star_comprehensive_generic_source_bundle.json"
)

SWEEP_EXTENSIONS = (
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".toml",
    ".py",
    ".ps1",
    ".psm1",
    ".psd1",
    ".sh",
    ".bash",
    ".md",
    ".txt",
    ".rst",
)


class LineEndingVerificationError(RuntimeError):
    pass


def check_attr(relative_path: str) -> dict[str, str]:
    result = subprocess.run(
        ["git", "check-attr", "text", "eol", "--", relative_path],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    attrs: dict[str, str] = {}
    for line in result.stdout.splitlines():
        # Format: "<path>: <attribute>: <value>"
        _, attribute, value = line.split(":", 2)
        attrs[attribute.strip()] = value.strip()
    return attrs


def contains_crlf(path: Path) -> bool:
    return b"\r\n" in path.read_bytes()


def verify_star_bundle() -> None:
    absolute = REPO_ROOT / STAR_BUNDLE_PATH
    if not absolute.is_file():
        raise LineEndingVerificationError(f"Expected governed artifact not found: {STAR_BUNDLE_PATH}")

    attrs = check_attr(STAR_BUNDLE_PATH)
    if attrs.get("text") != "set":
        raise LineEndingVerificationError(f"{STAR_BUNDLE_PATH} is not classified as text by .gitattributes")
    if attrs.get("eol") != "lf":
        raise LineEndingVerificationError(
            f"{STAR_BUNDLE_PATH} is not LF-controlled by .gitattributes (eol={attrs.get('eol')!r})"
        )
    if contains_crlf(absolute):
        raise LineEndingVerificationError(
            f"{STAR_BUNDLE_PATH} currently contains CRLF bytes in the working tree"
        )
    print(f"OK: {STAR_BUNDLE_PATH} is LF-controlled and CRLF-free.")


def sweep_repository() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    offenders: list[str] = []
    for relative in result.stdout.splitlines():
        if not relative.endswith(SWEEP_EXTENSIONS):
            continue
        absolute = REPO_ROOT / relative
        if not absolute.is_file():
            continue
        try:
            if contains_crlf(absolute):
                offenders.append(relative)
        except (OSError, UnicodeDecodeError):
            continue
    return offenders


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--all", action="store_true", help="Also sweep all covered extensions for CRLF (report only)."
    )
    args = parser.parse_args()

    try:
        verify_star_bundle()
    except LineEndingVerificationError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    if args.all:
        offenders = sweep_repository()
        if offenders:
            print(f"\n{len(offenders)} tracked file(s) with CRLF bytes found (report only, not a failure):")
            for path in offenders:
                print(f"  - {path}")
        else:
            print("\nNo CRLF bytes found in any tracked file under the covered extensions.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
