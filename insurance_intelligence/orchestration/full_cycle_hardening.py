"""Full-cycle certification hardening for MO-023I.

This module does not add insurance reasoning. It repeatedly exercises and
validates the existing governed knowledge-to-explanation certification cycle
under supported, unresolved, mismatched, and repeatability scenarios.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Callable, Mapping

from insurance_intelligence.orchestration.full_cycle_certification import (
    FullCycleCertificationError,
    FullKnowledgeToExplanationResult,
    run_full_knowledge_to_explanation_certification,
)
from insurance_intelligence.orchestration.star_comprehensive_pilot import (
    PRODUCT_REFERENCE,
    TOPIC,
)


class FullCycleHardeningError(ValueError):
    """Raised when hardening inputs or a certification result are unsafe."""


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


@dataclass(frozen=True)
class HardeningScenarioResult:
    scenario_id: str
    scenario_name: str
    status: str
    certification_id: str | None
    knowledge_snapshot_id: str | None
    released_response_id: str | None
    direct_answer: str
    failure_reason: str | None
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class FullCycleHardeningReport:
    report_id: str
    product_reference: str
    topic: str
    scenario_results: tuple[HardeningScenarioResult, ...]
    passed_count: int
    blocked_count: int
    failed_count: int
    deterministic: bool
    status: str


FullCycleRunner = Callable[..., FullKnowledgeToExplanationResult]


def _validate_supported_scope(*, product_reference: str, topic: str) -> None:
    if product_reference != PRODUCT_REFERENCE:
        raise FullCycleHardeningError("unsupported product_reference")
    if topic != TOPIC:
        raise FullCycleHardeningError("unsupported topic")


def validate_certification_result(
    result: FullKnowledgeToExplanationResult,
    *,
    expected_product_reference: str = PRODUCT_REFERENCE,
    expected_topic: str = TOPIC,
    expected_snapshot_id: str | None = None,
) -> None:
    """Validate release, scope, snapshot, lineage and no-LLM invariants."""
    if result.status != "CERTIFIED":
        raise FullCycleHardeningError("full cycle is not certified")
    if result.product_reference != expected_product_reference:
        raise FullCycleHardeningError("product scope mismatch")
    if result.topic != expected_topic:
        raise FullCycleHardeningError("topic scope mismatch")
    if not result.knowledge_snapshot_id:
        raise FullCycleHardeningError("knowledge snapshot identity is missing")
    if expected_snapshot_id is not None and result.knowledge_snapshot_id != expected_snapshot_id:
        raise FullCycleHardeningError("stale or mismatched knowledge snapshot")
    if result.response.knowledge_snapshot_id != result.knowledge_snapshot_id:
        raise FullCycleHardeningError("response snapshot linkage mismatch")
    if result.released_response_id != result.response.response.response_id:
        raise FullCycleHardeningError("released response identity mismatch")
    if not result.released_response_id:
        raise FullCycleHardeningError("released response identity is missing")
    if not result.build.receipts:
        raise FullCycleHardeningError("governed build receipts are missing")
    if not result.build.publication_ids:
        raise FullCycleHardeningError("publication lineage is missing")
    if not result.response.response.evidence_references:
        raise FullCycleHardeningError("response evidence lineage is missing")
    if result.response.used_llm:
        raise FullCycleHardeningError("hardening certification must remain LLM-independent")
    if any(
        section.status == "INCLUDED" and not section.text.strip()
        for section in result.response.response.sections
    ):
        raise FullCycleHardeningError("empty released response section")


def _response_signature(
    result: FullKnowledgeToExplanationResult,
) -> tuple[object, ...]:
    response = result.response.response
    section_signature = tuple(
        (
            getattr(section, "section_id", None),
            getattr(section, "section_type", None),
            getattr(section, "status", None),
            getattr(section, "text", None),
            tuple(getattr(section, "approved_finding_ids", ()) or ()),
            tuple(getattr(section, "evidence_reference_ids", ()) or ()),
            tuple(getattr(section, "limitation_ids", ()) or ()),
            tuple(getattr(section, "clarification_ids", ()) or ()),
        )
        for section in response.sections
    )
    evidence_signature = tuple(
        (
            getattr(reference, "reference_id", None),
            getattr(reference, "reference_type", None),
            getattr(reference, "source_id", None),
            getattr(reference, "label", None),
            getattr(reference, "locator", None),
            tuple(getattr(reference, "approved_finding_ids", ()) or ()),
        )
        for reference in response.evidence_references
    )
    return (
        result.certification_id,
        result.knowledge_snapshot_id,
        result.released_response_id,
        getattr(response, "response_id", None),
        getattr(response, "response_status", None),
        getattr(response, "direct_answer", None),
        section_signature,
        evidence_signature,
        tuple(result.limitations),
    )


def _scenario_result(
    *,
    name: str,
    status: str,
    certification: FullKnowledgeToExplanationResult | None = None,
    failure_reason: str | None = None,
) -> HardeningScenarioResult:
    return HardeningScenarioResult(
        scenario_id=_stable_id(
            "hardening-scenario",
            name,
            status,
            certification.certification_id if certification else failure_reason or "",
        ),
        scenario_name=name,
        status=status,
        certification_id=certification.certification_id if certification else None,
        knowledge_snapshot_id=certification.knowledge_snapshot_id if certification else None,
        released_response_id=certification.released_response_id if certification else None,
        direct_answer=(
            certification.response.response.direct_answer if certification else ""
        ),
        failure_reason=failure_reason,
        limitations=certification.limitations if certification else (),
    )


def run_full_cycle_hardening_suite(
    *,
    repository_root: str | Path,
    build_request_id_prefix: str,
    response_request_id_prefix: str,
    question: str,
    product_reference: str = PRODUCT_REFERENCE,
    topic: str = TOPIC,
    artifact_paths: Mapping[str, str] | None = None,
    response_repository_root: str | Path | None = None,
    runner: FullCycleRunner = run_full_knowledge_to_explanation_certification,
) -> FullCycleHardeningReport:
    """Run supported full-cycle cases and certify deterministic repeatability."""
    _validate_supported_scope(product_reference=product_reference, topic=topic)
    if not isinstance(build_request_id_prefix, str) or not build_request_id_prefix.strip():
        raise FullCycleHardeningError("build_request_id_prefix must be non-empty")
    if not isinstance(response_request_id_prefix, str) or not response_request_id_prefix.strip():
        raise FullCycleHardeningError("response_request_id_prefix must be non-empty")
    if not isinstance(question, str) or not question.strip():
        raise FullCycleHardeningError("question must be non-empty")

    scenario_results: list[HardeningScenarioResult] = []
    completed: list[FullKnowledgeToExplanationResult] = []

    cases = (
        ("CONFIRMED", {"trigger_status": "CONFIRMED"}),
        ("NOT_TRIGGERED", {"trigger_status": "NOT_TRIGGERED"}),
        ("UNRESOLVED", {"trigger_status": "UNRESOLVED"}),
    )
    for index, (name, context) in enumerate(cases, start=1):
        try:
            result = runner(
                repository_root=repository_root,
                build_request_id=f"{build_request_id_prefix}-{index}",
                response_request_id=f"{response_request_id_prefix}-{index}",
                question=question,
                customer_context=context,
                artifact_paths=artifact_paths,
                response_repository_root=response_repository_root,
            )
            validate_certification_result(result)
            completed.append(result)
            scenario_results.append(
                _scenario_result(name=name, status="PASSED", certification=result)
            )
        except (FullCycleCertificationError, FullCycleHardeningError, ValueError) as exc:
            scenario_results.append(
                _scenario_result(
                    name=name,
                    status="FAILED",
                    failure_reason=str(exc),
                )
            )

    deterministic = False
    if completed:
        first = completed[0]
        try:
            repeat = runner(
                repository_root=repository_root,
                build_request_id=f"{build_request_id_prefix}-1",
                response_request_id=f"{response_request_id_prefix}-1",
                question=question,
                customer_context={"trigger_status": "CONFIRMED"},
                artifact_paths=artifact_paths,
                response_repository_root=response_repository_root,
            )
            validate_certification_result(
                repeat,
                expected_snapshot_id=first.knowledge_snapshot_id,
            )
            deterministic = _response_signature(repeat) == _response_signature(first)
        except (FullCycleCertificationError, FullCycleHardeningError):
            deterministic = False

    passed_count = sum(item.status == "PASSED" for item in scenario_results)
    blocked_count = sum(item.status == "BLOCKED" for item in scenario_results)
    failed_count = sum(item.status == "FAILED" for item in scenario_results)
    status = (
        "CERTIFIED"
        if failed_count == 0 and blocked_count == 0 and deterministic
        else "FAILED"
    )
    report_id = _stable_id(
        "full-cycle-hardening",
        product_reference,
        topic,
        *(item.scenario_id for item in scenario_results),
        deterministic,
        status,
    )
    return FullCycleHardeningReport(
        report_id=report_id,
        product_reference=product_reference,
        topic=topic,
        scenario_results=tuple(scenario_results),
        passed_count=passed_count,
        blocked_count=blocked_count,
        failed_count=failed_count,
        deterministic=deterministic,
        status=status,
    )
