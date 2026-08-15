"""AR-2.5 C6 audit for historical comparison/recommendation/explanation artifacts.

The audit is intentionally non-destructive. It inventories files under the legacy
knowledge/health comparison, recommendation, and explanation output directories and
separates artifacts explicitly retained by the governed bypass inventory from other
historical outputs that require manual disposition.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from insurance_intelligence.bypass_inventory import build_default_bypass_inventory
from insurance_intelligence.contracts.bypass_inventory import BypassPathKind


LEGACY_OUTPUT_DIRS = (
    Path("knowledge/health/comparisons"),
    Path("knowledge/health/recommendations"),
    Path("knowledge/health/explanations"),
)


@dataclass(frozen=True)
class HistoricalArtifactFinding:
    path: str
    disposition: str
    reason: str


def _retained_fixture_paths() -> set[str]:
    inventory = build_default_bypass_inventory()
    return {
        item.repository_path
        for item in inventory.entries
        if item.path_kind is BypassPathKind.STATIC_ARTIFACT
    }


def audit(root: Path) -> tuple[HistoricalArtifactFinding, ...]:
    root = root.resolve()
    retained = _retained_fixture_paths()
    findings: list[HistoricalArtifactFinding] = []

    for relative_dir in LEGACY_OUTPUT_DIRS:
        directory = root / relative_dir
        if not directory.exists():
            continue
        for path in sorted(p for p in directory.rglob("*") if p.is_file()):
            relative = path.relative_to(root).as_posix()
            if relative in retained:
                findings.append(
                    HistoricalArtifactFinding(
                        path=relative,
                        disposition="RETAIN_FIREWALL_FIXTURE",
                        reason=(
                            "explicitly inventoried as an unreachable historical static artifact; "
                            "retain while bypass certification depends on it"
                        ),
                    )
                )
            else:
                findings.append(
                    HistoricalArtifactFinding(
                        path=relative,
                        disposition="REVIEW_REQUIRED",
                        reason=(
                            "historical intelligence output is not an explicit bypass fixture; "
                            "verify unique provenance/evaluation value before deletion"
                        ),
                    )
                )

    return tuple(findings)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit historical intelligence output artifacts")
    parser.add_argument("--root", default=".", help="repository root")
    args = parser.parse_args()

    findings = audit(Path(args.root))
    retained = [item for item in findings if item.disposition == "RETAIN_FIREWALL_FIXTURE"]
    review = [item for item in findings if item.disposition == "REVIEW_REQUIRED"]

    print("AR-2.5 C6 HISTORICAL INTELLIGENCE ARTIFACT AUDIT")
    print(
        f"Artifacts: {len(findings)} | retained firewall fixtures: {len(retained)} | "
        f"review required: {len(review)}"
    )
    for item in findings:
        print(f"[{item.disposition}] {item.path}")
        print(f"  {item.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
