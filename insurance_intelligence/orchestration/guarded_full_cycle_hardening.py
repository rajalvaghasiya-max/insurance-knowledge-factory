"""Hardening suite for the post-C5.36 guarded Star certification path.

The historical MO-023I hardening suite remains unchanged. This successor
repeats the guarded certification across supported applicability states and
proves deterministic identity/snapshot/release lineage on the repaired path.
Negative guard proofs live in the guarded-pilot adversarial test module.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Callable, Mapping

from insurance_intelligence.orchestration.guarded_full_cycle_certification import (
    GuardedFullCycleCertificationError,
    GuardedFullKnowledgeToExplanationResult,
    run_guarded_full_knowledge_to_explanation_certification,
    validate_guarded_response,
)
from insurance_intelligence.orchestration.star_comprehensive_pilot import PRODUCT_REFERENCE, TOPIC


class GuardedFullCycleHardeningError(ValueError):
    """Raised when guarded hardening inputs or results are unsafe."""


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


@dataclass(frozen=True)
class GuardedHardeningScenarioResult:
    scenario_id: str
    scenario_name: str
    status: str
    certification_id: str | None
    knowledge_snapshot_id: str | None
    released_response_id: str | None
    failure_reason: str | None


@dataclass(frozen=True)
class GuardedFullCycleHardeningReport:
    report_id: str
    product_reference: str
    topic: str
    scenario_results: tuple[GuardedHardeningScenarioResult, ...]
    passed_count: int
    failed_count: int
    deterministic: bool
    status: str


GuardedFullCycleRunner = Callable[..., GuardedFullKnowledgeToExplanationResult]


def validate_guarded_certification_result(
    result: GuardedFullKnowledgeToExplanationResult,
    *,
    expected_snapshot_id: str | None = None,
) -> None:
    if not isinstance(result, GuardedFullKnowledgeToExplanationResult):
        raise GuardedFullCycleHardeningError("result is not guarded certification output")
    if result.status != "CERTIFIED_GUARDED":
        raise GuardedFullCycleHardeningError("guarded full cycle is not certified")
    if result.product_reference != PRODUCT_REFERENCE or result.topic != TOPIC:
        raise GuardedFullCycleHardeningError("guarded certification scope mismatch")
    if expected_snapshot_id is not None and result.knowledge_snapshot_id != expected_snapshot_id:
        raise GuardedFullCycleHardeningError("stale or mismatched knowledge snapshot")
    if result.response.knowledge_snapshot_id != result.knowledge_snapshot_id:
        raise GuardedFullCycleHardeningError("guarded response snapshot linkage mismatch")
    if result.released_response_id != result.response.response.response_id:
        raise GuardedFullCycleHardeningError("guarded released response identity mismatch")
    if not result.build.receipts or not result.build.publication_ids:
        raise GuardedFullCycleHardeningError("guarded certification build lineage is incomplete")
    if not result.response.response.evidence_references:
        raise GuardedFullCycleHardeningError("guarded response evidence lineage is missing")
    if result.response.used_llm:
        raise GuardedFullCycleHardeningError("guarded hardening must remain LLM-independent")
    try:
        validate_guarded_response(result.response)
    except GuardedFullCycleCertificationError as exc:
        raise GuardedFullCycleHardeningError(str(exc)) from exc


def _signature(result: GuardedFullKnowledgeToExplanationResult) -> tuple[object, ...]:
    response = result.response.response
    return (
        result.certification_id,
        result.knowledge_snapshot_id,
        result.response.identity_record_ref,
        result.response.identity_record_hash,
        result.response.temporal_status,
        result.response.authority.authority_class,
        result.response.intent.primary_intent,
        result.response.reconciliation.reconciliation_status,
        result.response.instance_sufficiency.outcome,
        result.response.evidence_enforcement.outcome,
        result.response.authority_enforcement.enforcement_outcome,
        result.response.render_conformance.outcome,
        result.released_response_id,
        response.response_id,
        response.response_status,
        response.direct_answer,
        tuple((item.section_type, item.text) for item in response.sections),
        tuple(result.limitations),
    )


def run_guarded_full_cycle_hardening_suite(
    *,
    repository_root: str | Path,
    build_request_id_prefix: str,
    response_request_id_prefix: str,
    question: str,
    artifact_paths: Mapping[str, str] | None = None,
    response_repository_root: str | Path | None = None,
    identity_reference_path: str | Path | None = None,
    document_identity_overlay_path: str | Path | None = None,
    runner: GuardedFullCycleRunner = run_guarded_full_knowledge_to_explanation_certification,
) -> GuardedFullCycleHardeningReport:
    for value, label in (
        (build_request_id_prefix, "build_request_id_prefix"),
        (response_request_id_prefix, "response_request_id_prefix"),
        (question, "question"),
    ):
        if not isinstance(value, str) or not value.strip():
            raise GuardedFullCycleHardeningError(f"{label} must be non-empty")

    scenario_results: list[GuardedHardeningScenarioResult] = []
    completed: list[GuardedFullKnowledgeToExplanationResult] = []
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
                identity_reference_path=identity_reference_path,
                document_identity_overlay_path=document_identity_overlay_path,
            )
            validate_guarded_certification_result(result)
            completed.append(result)
            scenario_results.append(
                GuardedHardeningScenarioResult(
                    scenario_id=_stable_id("guarded-hardening-scenario", name, result.certification_id),
                    scenario_name=name,
                    status="PASSED",
                    certification_id=result.certification_id,
                    knowledge_snapshot_id=result.knowledge_snapshot_id,
                    released_response_id=result.released_response_id,
                    failure_reason=None,
                )
            )
        except (GuardedFullCycleCertificationError, GuardedFullCycleHardeningError, ValueError) as exc:
            scenario_results.append(
                GuardedHardeningScenarioResult(
                    scenario_id=_stable_id("guarded-hardening-scenario", name, "FAILED", str(exc)),
                    scenario_name=name,
                    status="FAILED",
                    certification_id=None,
                    knowledge_snapshot_id=None,
                    released_response_id=None,
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
                identity_reference_path=identity_reference_path,
                document_identity_overlay_path=document_identity_overlay_path,
            )
            validate_guarded_certification_result(repeat, expected_snapshot_id=first.knowledge_snapshot_id)
            deterministic = _signature(repeat) == _signature(first)
        except (GuardedFullCycleCertificationError, GuardedFullCycleHardeningError, ValueError):
            deterministic = False

    passed_count = sum(item.status == "PASSED" for item in scenario_results)
    failed_count = sum(item.status == "FAILED" for item in scenario_results)
    status = "CERTIFIED_GUARDED" if passed_count == 3 and failed_count == 0 and deterministic else "FAILED"
    report_id = _stable_id(
        "guarded-full-cycle-hardening",
        PRODUCT_REFERENCE,
        TOPIC,
        *(item.scenario_id for item in scenario_results),
        deterministic,
        status,
    )
    return GuardedFullCycleHardeningReport(
        report_id=report_id,
        product_reference=PRODUCT_REFERENCE,
        topic=TOPIC,
        scenario_results=tuple(scenario_results),
        passed_count=passed_count,
        failed_count=failed_count,
        deterministic=deterministic,
        status=status,
    )
