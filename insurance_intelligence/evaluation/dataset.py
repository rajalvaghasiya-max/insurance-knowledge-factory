"""Versioned controlled-evaluation dataset loading for MO-022F.2."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from insurance_intelligence.contracts.llm_evaluation import (
    EvaluationCase,
    EvaluationCaseCategory,
    EvaluationExpectedOutcome,
    ExpectedSemanticRequirement,
    ForbiddenBehaviour,
    LLMEvaluationContractError,
    LLMResponsibility,
    SemanticComponent,
)


class EvaluationDatasetError(ValueError):
    """Raised when a controlled-evaluation dataset is malformed."""


@dataclass(frozen=True)
class EvaluationDataset:
    dataset_id: str
    dataset_version: str
    schema_version: str
    cases: tuple[EvaluationCase, ...]
    source_files: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("dataset_id", "dataset_version", "schema_version"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise EvaluationDatasetError(f"{name} must be non-empty text")
            object.__setattr__(self, name, value.strip())
        if not isinstance(self.cases, tuple) or not self.cases:
            raise EvaluationDatasetError("cases must be a non-empty tuple")
        if not all(isinstance(case, EvaluationCase) for case in self.cases):
            raise EvaluationDatasetError("cases must contain EvaluationCase values")
        case_ids = tuple(case.case_id for case in self.cases)
        if len(case_ids) != len(set(case_ids)):
            raise EvaluationDatasetError("case IDs must be unique across the dataset")
        if tuple(sorted(case_ids)) != case_ids:
            raise EvaluationDatasetError("cases must be deterministically ordered by case_id")
        if not isinstance(self.source_files, tuple) or not self.source_files:
            raise EvaluationDatasetError("source_files must be a non-empty tuple")

    def filter(
        self,
        *,
        category: EvaluationCaseCategory | None = None,
        responsibility: LLMResponsibility | None = None,
        tags: Iterable[str] = (),
    ) -> tuple[EvaluationCase, ...]:
        required_tags = frozenset(tag.strip() for tag in tags if tag.strip())
        return tuple(
            case
            for case in self.cases
            if (category is None or case.category is category)
            and (responsibility is None or case.responsibility is responsibility)
            and required_tags <= set(case.tags)
        )

    def summary(self) -> dict[str, object]:
        return {
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "schema_version": self.schema_version,
            "case_count": len(self.cases),
            "by_category": dict(sorted(Counter(c.category.value for c in self.cases).items())),
            "by_responsibility": dict(
                sorted(Counter(c.responsibility.value for c in self.cases).items())
            ),
        }


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvaluationDatasetError(f"dataset file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise EvaluationDatasetError(f"invalid JSON in {path}: {exc.msg}") from exc


def _enum(enum_type: type, value: object, field_name: str):
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise EvaluationDatasetError(f"invalid {field_name}: {value!r}") from exc


def _text_tuple(value: object, field_name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise EvaluationDatasetError(f"{field_name} must be a JSON array")
    result = tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
    if len(result) != len(value):
        raise EvaluationDatasetError(f"{field_name} must contain non-empty strings")
    if not allow_empty and not result:
        raise EvaluationDatasetError(f"{field_name} must not be empty")
    if len(result) != len(set(result)):
        raise EvaluationDatasetError(f"{field_name} must not contain duplicates")
    return result


def _parse_requirement(raw: object, case_id: str) -> ExpectedSemanticRequirement:
    if not isinstance(raw, dict):
        raise EvaluationDatasetError(f"{case_id}: semantic requirement must be an object")
    try:
        return ExpectedSemanticRequirement(
            requirement_id=raw["requirement_id"],
            component=_enum(SemanticComponent, raw["component"], "component"),
            expected_text=raw["expected_text"],
            evidence_ids=_text_tuple(raw["evidence_ids"], "evidence_ids", allow_empty=False),
            required=raw.get("required", True),
        )
    except KeyError as exc:
        raise EvaluationDatasetError(
            f"{case_id}: missing semantic requirement field {exc.args[0]}"
        ) from exc


def _parse_case(raw: object, declared_category: EvaluationCaseCategory) -> EvaluationCase:
    if not isinstance(raw, dict):
        raise EvaluationDatasetError("each dataset case must be a JSON object")
    case_id = str(raw.get("case_id", "<unknown>"))
    try:
        category = _enum(EvaluationCaseCategory, raw["category"], "category")
        if category is not declared_category:
            raise EvaluationDatasetError(
                f"{case_id}: category does not match its declared fixture file"
            )
        return EvaluationCase(
            case_id=raw["case_id"],
            title=raw["title"],
            category=category,
            responsibility=_enum(
                LLMResponsibility, raw["responsibility"], "responsibility"
            ),
            audience=raw["audience"],
            governed_evidence_ids=_text_tuple(
                raw["governed_evidence_ids"], "governed_evidence_ids", allow_empty=False
            ),
            approved_finding_ids=_text_tuple(
                raw["approved_finding_ids"], "approved_finding_ids", allow_empty=False
            ),
            semantic_requirements=tuple(
                _parse_requirement(item, case_id)
                for item in raw["semantic_requirements"]
            ),
            forbidden_behaviours=tuple(
                _enum(ForbiddenBehaviour, item, "forbidden_behaviour")
                for item in raw["forbidden_behaviours"]
            ),
            expected_outcome=_enum(
                EvaluationExpectedOutcome, raw["expected_outcome"], "expected_outcome"
            ),
            reference_output=raw.get("reference_output"),
            historical_defect_id=raw.get("historical_defect_id"),
            tags=_text_tuple(raw.get("tags", []), "tags"),
        )
    except KeyError as exc:
        raise EvaluationDatasetError(f"{case_id}: missing field {exc.args[0]}") from exc
    except LLMEvaluationContractError as exc:
        raise EvaluationDatasetError(f"{case_id}: {exc}") from exc


def load_evaluation_dataset(root: str | Path) -> EvaluationDataset:
    root_path = Path(root)
    manifest = _read_json(root_path / "manifest.json")
    if not isinstance(manifest, dict):
        raise EvaluationDatasetError("manifest must be a JSON object")
    try:
        files = manifest["files"]
        expected_case_count = manifest["case_count"]
    except KeyError as exc:
        raise EvaluationDatasetError(f"manifest missing field {exc.args[0]}") from exc
    if manifest.get("schema_version") != "1.0":
        raise EvaluationDatasetError("unsupported dataset schema_version")
    if not isinstance(files, list) or not files:
        raise EvaluationDatasetError("manifest files must be a non-empty array")
    if len(files) != len(set(files)):
        raise EvaluationDatasetError("manifest files must not contain duplicates")
    all_cases: list[EvaluationCase] = []
    for filename in files:
        if not isinstance(filename, str) or not filename.endswith(".json"):
            raise EvaluationDatasetError("manifest files must contain JSON filenames")
        payload = _read_json(root_path / filename)
        if not isinstance(payload, dict):
            raise EvaluationDatasetError(f"{filename} must contain a JSON object")
        declared = _enum(EvaluationCaseCategory, payload.get("category"), "category")
        raw_cases = payload.get("cases")
        if not isinstance(raw_cases, list) or not raw_cases:
            raise EvaluationDatasetError(f"{filename} cases must be a non-empty array")
        all_cases.extend(_parse_case(item, declared) for item in raw_cases)
    all_cases.sort(key=lambda case: case.case_id)
    if not isinstance(expected_case_count, int) or isinstance(expected_case_count, bool):
        raise EvaluationDatasetError("manifest case_count must be an integer")
    if expected_case_count != len(all_cases):
        raise EvaluationDatasetError("manifest case_count does not match loaded cases")
    return EvaluationDataset(
        dataset_id=manifest.get("dataset_id"),
        dataset_version=manifest.get("dataset_version"),
        schema_version=manifest.get("schema_version"),
        cases=tuple(all_cases),
        source_files=tuple(files),
    )
