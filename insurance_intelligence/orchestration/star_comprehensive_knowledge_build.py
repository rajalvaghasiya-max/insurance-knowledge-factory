"""Governed Star Comprehensive knowledge-build certification pilot.

The pilot does not recrawl or reinterpret documents. It validates the existing
reviewed Knowledge Factory artifact chain and emits a deterministic certified
snapshot receipt consumable by the MO-023F response pilot.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

PRODUCT_REFERENCE = "star_health:star_comprehensive"
TOPIC = "conditional_copayment"


class StarKnowledgeBuildError(ValueError):
    """Raised when the governed artifact chain is incomplete or inconsistent."""


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _file_digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _load(root: Path, relative: str) -> Mapping[str, Any]:
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise StarKnowledgeBuildError("artifact path escaped repository root") from exc

    if not path.is_file():
        raise StarKnowledgeBuildError(
            f"required governed artifact is missing: {relative}"
        )

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StarKnowledgeBuildError(
            f"invalid governed JSON artifact: {relative}"
        ) from exc

    if not isinstance(value, dict):
        raise StarKnowledgeBuildError(
            f"governed artifact must be a JSON object: {relative}"
        )

    return value


@dataclass(frozen=True)
class KnowledgeArtifactReceipt:
    stage: str
    relative_path: str
    sha256: str
    status: str


@dataclass(frozen=True)
class StarKnowledgeBuildResult:
    build_id: str
    product_reference: str
    topic: str
    knowledge_snapshot_id: str
    receipts: tuple[KnowledgeArtifactReceipt, ...]
    evidence_ids: tuple[str, ...]
    assertion_ids: tuple[str, ...]
    publication_ids: tuple[str, ...]
    limitations: tuple[str, ...]
    status: str


_DEFAULT_PATHS = {
    "SOURCE_REGISTRATION": (
        "knowledge/factory/registry_backed/"
        "star_health_star_comprehensive/generic_source_registration/"
        "star_health_star_comprehensive_generic_source_bundle.json"
    ),
    "DOCUMENT_IDENTITY": (
        "knowledge/factory/registry_backed/"
        "star_health_star_comprehensive/governance/"
        "star_health_star_comprehensive_document_identity_resolution.json"
    ),
    "DOCUMENT_CLASSIFICATION": (
        "knowledge/factory/registry_backed/"
        "star_health_star_comprehensive/governance/"
        "star_health_star_comprehensive_document_classification.json"
    ),
    "LEGAL_BINDING": (
        "knowledge/factory/registry_backed/"
        "star_health_star_comprehensive/generic_legal_condition_binding/"
        "star_health_star_comprehensive_conditional_copayment.json"
    ),
    "CANONICAL_PROJECTION": (
        "knowledge/factory/registry_backed/"
        "star_health_star_comprehensive/"
        "generic_legal_condition_canonical_projection/"
        "star_health_star_comprehensive_conditional_copayment.canonical.json"
    ),
    "PUBLICATION_DECISION": (
        "knowledge/factory/registry_backed/"
        "star_health_star_comprehensive/publication_decision/"
        "star_comprehensive_conditional_copayment.eligibility.json"
    ),
    "AUTHORITATIVE_PUBLICATION": (
        "knowledge/factory/registry_backed/"
        "star_health_star_comprehensive/authoritative/"
        "star_comprehensive_conditional_copayment.authoritative.json"
    ),
}


def _status(value: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return "present"


def _collect_ids(value: object, key_names: frozenset[str]) -> tuple[str, ...]:
    found: list[str] = []

    def visit(item: object) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if key in key_names and isinstance(child, str) and child.strip():
                    found.append(child.strip())
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return tuple(dict.fromkeys(found))


def build_star_comprehensive_copay_snapshot(
    *,
    repository_root: str | Path,
    build_request_id: str,
    artifact_paths: Mapping[str, str] | None = None,
) -> StarKnowledgeBuildResult:
    """Validate the reviewed build chain and issue a deterministic snapshot receipt."""
    if not isinstance(build_request_id, str) or not build_request_id.strip():
        raise StarKnowledgeBuildError(
            "build_request_id must be a non-empty string"
        )

    root = Path(repository_root).resolve()
    if not root.is_dir():
        raise StarKnowledgeBuildError(
            "repository_root must be an existing directory"
        )

    paths = dict(_DEFAULT_PATHS)
    if artifact_paths:
        unknown = set(artifact_paths) - set(paths)
        if unknown:
            raise StarKnowledgeBuildError(
                f"unknown artifact stages: {sorted(unknown)}"
            )
        paths.update(artifact_paths)

    loaded: dict[str, Mapping[str, Any]] = {}
    receipts: list[KnowledgeArtifactReceipt] = []

    for stage, relative in paths.items():
        value = _load(root, relative)
        loaded[stage] = value
        receipts.append(
            KnowledgeArtifactReceipt(
                stage=stage,
                relative_path=relative,
                sha256=_file_digest(root / relative),
                status=_status(
                    value,
                    "publication_status",
                    "decision_status",
                    "eligibility_status",
                    "binding_status",
                    "classification_status",
                    "registration_status",
                    "status",
                ),
            )
        )

    bundle = loaded["SOURCE_REGISTRATION"]
    context = bundle.get("product_context")
    if (
        not isinstance(context, dict)
        or context.get("insurer_id") != "star_health"
        or context.get("product_id") != "star_comprehensive"
    ):
        raise StarKnowledgeBuildError(
            "source bundle product identity does not match Star Comprehensive"
        )

    if context.get("source_scope") != "reusable_generic":
        raise StarKnowledgeBuildError(
            "source bundle is not reusable generic knowledge"
        )

    binding = loaded["LEGAL_BINDING"]
    if binding.get("reviewed_by_human") is not True:
        raise StarKnowledgeBuildError(
            "legal binding must be human reviewed"
        )

    assertions = binding.get("assertions")
    if not isinstance(assertions, list) or not assertions:
        raise StarKnowledgeBuildError(
            "legal binding contains no governed assertions"
        )

    if not any(
        isinstance(item, dict)
        and item.get("assertion_type") == "conditional_copayment_rule"
        for item in assertions
    ):
        raise StarKnowledgeBuildError(
            "conditional co-payment assertion is missing"
        )

    authoritative = loaded["AUTHORITATIVE_PUBLICATION"]
    publication_text = json.dumps(authoritative, sort_keys=True).lower()
    if "authoritative" not in publication_text and "published" not in publication_text:
        raise StarKnowledgeBuildError(
            "authoritative publication is not publication-ready"
        )

    evidence_ids = _collect_ids(
        loaded,
        frozenset({"evidence_id", "source_id", "candidate_id"}),
    )
    assertion_ids = _collect_ids(
        loaded,
        frozenset({"assertion_id"}),
    )
    publication_ids = _collect_ids(
        loaded,
        frozenset(
            {
                "publication_id",
                "publication_decision_id",
                "decision_id",
                "canonical_record_id",
            }
        ),
    )

    chain_digest = sha256(
        "\n".join(receipt.sha256 for receipt in receipts).encode("utf-8")
    ).hexdigest()
    snapshot_id = _stable_id(
        "knowledge-snapshot",
        PRODUCT_REFERENCE,
        TOPIC,
        chain_digest,
    )
    build_id = _stable_id(
        "knowledge-build",
        build_request_id,
        snapshot_id,
    )

    return StarKnowledgeBuildResult(
        build_id=build_id,
        product_reference=PRODUCT_REFERENCE,
        topic=TOPIC,
        knowledge_snapshot_id=snapshot_id,
        receipts=tuple(receipts),
        evidence_ids=evidence_ids,
        assertion_ids=assertion_ids,
        publication_ids=publication_ids,
        limitations=(
            "Snapshot certifies the reviewed conditional co-payment artifact chain only.",
        ),
        status="CERTIFIED",
    )