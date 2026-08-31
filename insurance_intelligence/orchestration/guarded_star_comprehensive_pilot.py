"""Guarded Star Comprehensive conditional co-payment response pilot.

This module repairs the pre-safety-foundation MO-023F pilot by composing the
already-governed request-authority, intent, context, instance-sufficiency,
evidence-enforcement, decision-enforcement, explanation-enforcement and
rendering-exit boundaries around the existing deterministic insurance
semantics. It does not add recommendation authority or new insurance facts.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import json
from pathlib import Path
from typing import Mapping, Sequence

from insurance_intelligence.authority_enforced_decision_gate import AuthorityEnforcedDecisionGate
from insurance_intelligence.authority_enforced_explanation import AuthorityEnforcedExplanationGenerator
from insurance_intelligence.authority_intent_reconciliation import reconcile_authority_and_intent
from insurance_intelligence.context.builder import ContextBuilder
from insurance_intelligence.contracts.authority_enforcement import build_input as build_authority_enforcement_input
from insurance_intelligence.contracts.authority_intent_reconciliation import build_input as build_reconciliation_input
from insurance_intelligence.contracts.context import (
    ResolvedContextItem,
    build_input as build_context_input,
    build_resolved_context_item,
)
from insurance_intelligence.contracts.decision import build_input as build_decision_input
from insurance_intelligence.contracts.evidence import build_input as build_evidence_input
from insurance_intelligence.contracts.evidence_instance_enforcement import (
    build_input as build_evidence_enforcement_input,
)
from insurance_intelligence.contracts.instance_sufficiency import (
    InstanceResolutionAttestation,
    build_attestation,
    build_input as build_instance_input,
)
from insurance_intelligence.contracts.intent import build_input as build_intent_input
from insurance_intelligence.contracts.reasoning import build_input as build_reasoning_input
from insurance_intelligence.contracts.reasoning_plan import build_evidence_requirement, build_plan
from insurance_intelligence.contracts.rendering_exit import build_candidate, build_candidate_unit
from insurance_intelligence.contracts.request_authority import build_input as build_authority_input
from insurance_intelligence.contracts.response import (
    ResponseAssemblerOutput,
    build_input as build_response_input,
    build_output as build_response_output,
    build_section as build_response_section,
)
from insurance_intelligence.entity_resolution.product_resolver import ProductEntityResolver
from insurance_intelligence.entity_resolution.registry_adapter import load_runtime_registry_from_files
from insurance_intelligence.evidence_instance_enforcement import EvidenceInstanceEnforcer
from insurance_intelligence.intent.analyzer import IntentAnalyzer
from insurance_intelligence.instance_sufficiency import InstanceSufficiencyGuard
from insurance_intelligence.orchestration.star_comprehensive_pilot import (
    COPAY_SCOPE,
    PRODUCT_REFERENCE,
    TOPIC,
    _harden_case_response,
    _response_registry,
    _stable_id,
    _style_registry,
)
from insurance_intelligence.reasoning.engine import ReasoningEngine
from insurance_intelligence.rendering_exit_safety import evaluate_render_candidate, project_render_envelope
from insurance_intelligence.request_authority import classify_request_authority
from insurance_intelligence.response.service import assemble_response

IDENTITY_REFERENCE_RELATIVE_PATH = (
    "docs/architecture/star_health_star_comprehensive_product_identity_reference_spec.json"
)
DOCUMENT_IDENTITY_OVERLAY_RELATIVE_PATH = (
    "docs/architecture/star_health_star_comprehensive_document_identity_resolution_spec.json"
)
CURRENTNESS_LIMITATION_ID = "star_comprehensive_identity_currentness_unverified"
CURRENTNESS_LIMITATION_TEXT = (
    "Star Comprehensive product identity is reviewed, but compatibility/currentness of the registered "
    "policy wording remains unverified; confirm the current policy wording before relying on this answer "
    "for current entitlement."
)


class GuardedStarComprehensivePilotError(ValueError):
    """Raised when the guarded Star pilot cannot complete safely."""


@dataclass(frozen=True)
class GuardedStarComprehensivePilotResult:
    pilot_id: str
    request_id: str
    product_reference: str
    topic: str
    question: str
    knowledge_snapshot_id: str
    authority: object
    intent: object
    reconciliation: object
    context: object
    identity_resolution: object
    identity_record_ref: str
    identity_record_hash: str
    temporal_status: str
    instance_sufficiency: object
    evidence_enforcement: object
    plan: object
    evidence: object
    reasoning: object
    authority_enforcement: object
    decision: object
    explanation: object
    response: ResponseAssemblerOutput
    render_conformance: object
    released_response_id: str
    used_llm: bool
    limitations: tuple[str, ...]
    guard_status: str


def _module_repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_governance_path(
    *,
    supplied: str | Path | None,
    relative_path: str,
) -> Path:
    path = Path(supplied) if supplied is not None else _module_repository_root() / relative_path
    path = path.resolve()
    if not path.is_file():
        raise GuardedStarComprehensivePilotError(f"governed artifact not found: {path}")
    return path


def _identity_record_ref(path: Path) -> str:
    root = _module_repository_root()
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _load_temporal_status(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GuardedStarComprehensivePilotError("invalid document identity overlay JSON") from exc
    documents = payload.get("documents")
    if not isinstance(documents, list) or len(documents) != 1 or not isinstance(documents[0], dict):
        raise GuardedStarComprehensivePilotError("document identity overlay must contain one reviewed document")
    status = documents[0].get("temporal_status")
    if not isinstance(status, str) or not status.strip():
        raise GuardedStarComprehensivePilotError("document identity overlay temporal_status is missing")
    return status.strip()


def _resolve_product_identity(path: Path):
    try:
        registry = load_runtime_registry_from_files((path,))
        resolution = ProductEntityResolver(registry).resolve(PRODUCT_REFERENCE)
    except Exception as exc:
        raise GuardedStarComprehensivePilotError(f"governed product identity could not be loaded: {exc}") from exc
    if resolution.status != "RESOLVED" or resolution.selected_entity is None:
        raise GuardedStarComprehensivePilotError(
            f"Star Comprehensive product identity did not resolve: status={resolution.status}"
        )
    if resolution.selected_entity.canonical_entity_id != PRODUCT_REFERENCE:
        raise GuardedStarComprehensivePilotError("resolved product identity does not match pilot scope")
    return resolution


def _product_context_key(intent: str) -> str:
    mapping = {
        "CLAIM_SCENARIO": "policy_or_product_reference",
        "CLAUSE_IMPLICATION": "policy_or_product_reference",
        "COVERAGE_CHECK": "policy_or_product_reference",
        "EXCLUSION_CHECK": "policy_or_product_reference",
        "PRODUCT_EXPLANATION": "product_reference",
        "TERM_EXPLANATION": "product_reference",
    }
    try:
        return mapping[intent]
    except KeyError as exc:
        raise GuardedStarComprehensivePilotError(
            f"guarded Star pilot does not support intent {intent!r}"
        ) from exc


def _context_inputs(intent: str, question: str) -> tuple[tuple[dict[str, object], ...], tuple[ResolvedContextItem, ...]]:
    user_context: list[dict[str, object]] = []
    if intent == "CLAIM_SCENARIO":
        user_context.append(
            {
                "key": "claim_scenario",
                "value": question,
                "source_reference": "request.question",
                "sequence": 1,
            }
        )
    elif intent == "CLAUSE_IMPLICATION":
        user_context.append(
            {
                "key": "clause_or_feature",
                "value": "co-payment",
                "source_reference": "guarded_star_pilot.topic_scope",
                "sequence": 1,
            }
        )
        user_context.append(
            {
                "key": "scenario_context",
                "value": question,
                "source_reference": "request.question",
                "sequence": 2,
            }
        )
    elif intent == "COVERAGE_CHECK":
        user_context.append(
            {
                "key": "coverage_subject",
                "value": "conditional co-payment applicability",
                "source_reference": "guarded_star_pilot.topic_scope",
                "sequence": 1,
            }
        )
    elif intent == "EXCLUSION_CHECK":
        user_context.append(
            {
                "key": "exclusion_subject",
                "value": "conditional co-payment applicability",
                "source_reference": "guarded_star_pilot.topic_scope",
                "sequence": 1,
            }
        )
    elif intent == "TERM_EXPLANATION":
        user_context.append(
            {
                "key": "term_or_concept",
                "value": "co-payment",
                "source_reference": "guarded_star_pilot.topic_scope",
                "sequence": 1,
            }
        )
    elif intent != "PRODUCT_EXPLANATION":
        raise GuardedStarComprehensivePilotError(
            f"guarded Star pilot does not support intent {intent!r}"
        )

    product_key = _product_context_key(intent)
    session_context = (
        build_resolved_context_item(
            key=product_key,
            value=PRODUCT_REFERENCE,
            category="PRODUCT",
            provenance="SYSTEM_DERIVED",
            source_reference="guarded_star_pilot.product_scope",
            confidence=1.0,
            materiality="high",
        ),
    )
    return tuple(user_context), session_context


def _build_identity_attestation(
    *,
    context_key: str,
    resolution: object,
    identity_path: Path,
) -> InstanceResolutionAttestation:
    selected = getattr(resolution, "selected_entity", None)
    if selected is None:
        raise GuardedStarComprehensivePilotError("resolved product identity is missing selected_entity")
    return build_attestation(
        instance_kind="PRODUCT",
        context_key=context_key,
        resolution_status="RESOLVED",
        canonical_identity=selected.canonical_entity_id,
        identity_record_ref=_identity_record_ref(identity_path),
        identity_record_hash=sha256(identity_path.read_bytes()).hexdigest(),
        resolution_basis=(
            "runtime registry admitted the reviewed product_identity_reference_v1 and resolved "
            f"the pilot scope by {getattr(resolution, 'match_method', 'governed precedence')}"
        ),
    )


def _evaluate_instance_sufficiency(
    *,
    request_id: str,
    reconciliation: object,
    context: object,
    attestations: Sequence[InstanceResolutionAttestation],
):
    return InstanceSufficiencyGuard().evaluate(
        build_instance_input(
            request_id=request_id,
            reconciliation=reconciliation,
            context=context,
            attestations=tuple(attestations),
        )
    )


def _exact_render_candidate(envelope):
    return build_candidate(
        request_id=envelope.request_id,
        response_id=envelope.response_id,
        units=tuple(
            build_candidate_unit(
                render_unit_id=unit.render_unit_id,
                rendered_text=unit.source_text,
                sequence=unit.sequence,
            )
            for unit in envelope.units
        ),
    )


def _evaluate_release(response: ResponseAssemblerOutput, *, candidate=None):
    envelope = project_render_envelope(response)
    selected = candidate if candidate is not None else _exact_render_candidate(envelope)
    return evaluate_render_candidate(envelope=envelope, candidate=selected)


def _apply_currentness_limitation(
    response: ResponseAssemblerOutput,
    *,
    temporal_status: str,
) -> ResponseAssemblerOutput:
    if temporal_status == "current":
        return response

    limitations = tuple(dict.fromkeys((*response.limitations, CURRENTNESS_LIMITATION_TEXT)))
    if response.response_status == "CLARIFICATION_REQUIRED":
        return build_response_output(
            request_id=response.request_id,
            response_id=_stable_id("response", response.response_id, temporal_status),
            response_status=response.response_status,
            audience=response.audience,
            response_format=response.response_format,
            direct_answer=None,
            sections=response.sections,
            evidence_references=response.evidence_references,
            limitations=limitations,
            assumptions=response.assumptions,
            clarification_questions=response.clarification_questions,
            confidence=response.confidence,
            response_trace=(),
        )

    limitation_section = build_response_section(
        section_id=_stable_id("section", response.response_id, CURRENTNESS_LIMITATION_ID),
        section_type="LIMITATION",
        status="INCLUDED",
        text=CURRENTNESS_LIMITATION_TEXT,
        limitation_ids=(CURRENTNESS_LIMITATION_ID,),
    )
    return build_response_output(
        request_id=response.request_id,
        response_id=_stable_id("response", response.response_id, temporal_status, CURRENTNESS_LIMITATION_ID),
        response_status="ANSWER_WITH_LIMITATIONS",
        audience=response.audience,
        response_format=response.response_format,
        direct_answer=response.direct_answer,
        sections=(*response.sections, limitation_section),
        evidence_references=response.evidence_references,
        limitations=limitations,
        assumptions=response.assumptions,
        clarification_questions=(),
        confidence=response.confidence,
        response_trace=(),
    )


def run_guarded_star_comprehensive_copay_pilot(
    *,
    request_id: str,
    question: str,
    repository_root: str | Path,
    knowledge_snapshot_id: str,
    customer_context: Mapping[str, object] | None = None,
    audience: str = "CUSTOMER",
    reading_level: str = "SIMPLE",
    identity_reference_path: str | Path | None = None,
    document_identity_overlay_path: str | Path | None = None,
) -> GuardedStarComprehensivePilotResult:
    """Run the Star conditional co-payment pilot through the current guarded path."""
    if not isinstance(request_id, str) or not request_id.strip():
        raise GuardedStarComprehensivePilotError("request_id must be a non-empty string")
    if not isinstance(question, str) or not question.strip():
        raise GuardedStarComprehensivePilotError("question must be a non-empty string")
    if not isinstance(knowledge_snapshot_id, str) or not knowledge_snapshot_id.strip():
        raise GuardedStarComprehensivePilotError("knowledge_snapshot_id must be a non-empty string")
    root = Path(repository_root)
    if not root.exists() or not root.is_dir():
        raise GuardedStarComprehensivePilotError("repository_root must be an existing directory")

    clean_question = question.strip()
    context_values = dict(customer_context or {})

    authority = classify_request_authority(
        build_authority_input(request_id=request_id, text=clean_question)
    )
    intent = IntentAnalyzer().analyze(
        build_intent_input(
            request_id=request_id,
            text=clean_question,
            domain_hint="health",
        )
    )
    reconciliation = reconcile_authority_and_intent(
        build_reconciliation_input(
            request_id=request_id,
            authority=authority,
            intent=intent,
        )
    )

    user_context, session_context = _context_inputs(intent.primary_intent, clean_question)
    built_context = ContextBuilder().build(
        build_context_input(
            request_id=request_id,
            intent_analysis=intent,
            user_context=user_context,
            session_context=session_context,
        )
    )

    identity_path = _resolve_governance_path(
        supplied=identity_reference_path,
        relative_path=IDENTITY_REFERENCE_RELATIVE_PATH,
    )
    overlay_path = _resolve_governance_path(
        supplied=document_identity_overlay_path,
        relative_path=DOCUMENT_IDENTITY_OVERLAY_RELATIVE_PATH,
    )
    temporal_status = _load_temporal_status(overlay_path)
    identity_resolution = _resolve_product_identity(identity_path)
    product_key = _product_context_key(intent.primary_intent)
    attestation = _build_identity_attestation(
        context_key=product_key,
        resolution=identity_resolution,
        identity_path=identity_path,
    )
    instance_sufficiency = _evaluate_instance_sufficiency(
        request_id=request_id,
        reconciliation=reconciliation,
        context=built_context,
        attestations=(attestation,),
    )
    if instance_sufficiency.outcome != "PASS" or not instance_sufficiency.planning_authorized:
        raise GuardedStarComprehensivePilotError(
            "instance sufficiency blocked the guarded pilot: "
            f"outcome={instance_sufficiency.outcome}; basis={instance_sufficiency.basis}"
        )

    reasoning_context = dict(context_values)
    decision_context = {
        "domain": "health",
        "topic": TOPIC if context_values else "copay",
        "case_specific_applicability": bool(context_values),
    }
    decision_context.update(context_values)
    if "trigger_status" in context_values:
        reasoning_context["conditional_copayment_trigger_status"] = context_values["trigger_status"]

    plan = build_plan(
        request_id=request_id,
        plan_id=_stable_id("guarded-plan", request_id, PRODUCT_REFERENCE, TOPIC, intent.primary_intent),
        plan_type="CLAUSE_IMPACT_PLAN",
        execution_mode="INTERPRETIVE",
        goal="derive the governed meaning and applicability of conditional co-payment",
        expected_outcome="CLAUSE_IMPACT_EXPLANATION",
        plan_status="READY",
        confidence=0.9,
        required_evidence=(
            build_evidence_requirement(
                requirement_id="req_star_comprehensive_conditional_copay",
                evidence_category="NORMALIZED_PRODUCT_FACT",
                subject_reference=PRODUCT_REFERENCE,
                required=True,
                authority_requirement="BINDING",
                version_requirement="ANY_GOVERNED",
                reason="resolve the governed conditional co-payment clause",
                requested_by_step="guarded_star_comprehensive_copay_pilot",
            ),
        ),
    )
    evidence_enforcement = EvidenceInstanceEnforcer().resolve(
        build_evidence_enforcement_input(
            request_id=request_id,
            instance_sufficiency=instance_sufficiency,
            evidence_input=build_evidence_input(
                request_id=request_id,
                reasoning_plan=plan,
                repository_roots=(str(root),),
                resolution_context={"knowledge_snapshot_id": knowledge_snapshot_id},
                strict_mode="STRICT",
            ),
        )
    )
    if (
        evidence_enforcement.outcome != "EVIDENCE_RESOLUTION_AUTHORIZED"
        or not evidence_enforcement.evidence_resolver_called
        or evidence_enforcement.evidence_output is None
    ):
        raise GuardedStarComprehensivePilotError(
            f"evidence instance enforcement blocked the pilot: {evidence_enforcement.basis}"
        )
    evidence = evidence_enforcement.evidence_output

    reasoning = ReasoningEngine().reason(
        build_reasoning_input(
            request_id=request_id,
            reasoning_plan=plan,
            evidence_resolution=evidence,
            reasoning_context=reasoning_context,
            strict_mode="STRICT",
        )
    )
    authority_enforcement = AuthorityEnforcedDecisionGate().decide(
        build_authority_enforcement_input(
            request_id=request_id,
            reconciliation=reconciliation,
            decision_gate_input=build_decision_input(
                request_id=request_id,
                reasoning_plan=plan,
                evidence_resolution=evidence,
                reasoning_output=reasoning,
                decision_context=decision_context,
                strict_mode="STRICT",
            ),
        )
    )
    if (
        authority_enforcement.enforcement_outcome != "DELEGATED_TO_DECISION_GATE"
        or not authority_enforcement.decision_gate_called
        or authority_enforcement.decision_output is None
    ):
        raise GuardedStarComprehensivePilotError(
            "authority enforcement withheld the ordinary answer path: "
            f"outcome={authority_enforcement.enforcement_outcome}; basis={authority_enforcement.basis}"
        )
    decision = authority_enforcement.decision_output
    if decision.decision not in {"APPROVED", "APPROVED_WITH_LIMITATIONS", "CLARIFICATION_REQUIRED"}:
        raise GuardedStarComprehensivePilotError(
            f"decision is not eligible for response generation: {decision.decision}"
        )

    mode = "CLARIFICATION_REQUEST" if decision.decision == "CLARIFICATION_REQUIRED" else "PLAIN_LANGUAGE"
    communication_context = {
        "domain_scope": "HEALTH",
        "question": clean_question,
        "knowledge_snapshot_id": knowledge_snapshot_id,
    }
    communication_context.update(context_values)
    if decision.clarifications:
        communication_context.setdefault(
            "trigger_status",
            "Did the documented conditional co-payment trigger apply to this treatment?",
        )
    findings = {
        item.finding_id: (item if item.condition is not None else replace(item, condition=""))
        for item in reasoning.findings
    }
    explanation = AuthorityEnforcedExplanationGenerator().generate(
        authority_result=authority_enforcement,
        findings_by_id=findings,
        style_registry=_style_registry(audience, reading_level, mode),
        audience=audience,
        reading_level=reading_level,
        explanation_mode=mode,
        communication_context=communication_context,
    )

    labels = {
        item.evidence_id: item.source_type.replace("_", " ").title()
        for item in evidence.evidence_packages
    }
    locators = {
        item.evidence_id: f"page {item.page}" if item.page is not None else item.document_id
        for item in evidence.evidence_packages
    }
    response = assemble_response(
        build_response_input(
            request_id=request_id,
            decision_output=decision,
            explanation_output=explanation,
            response_format="STANDARD",
            assembly_context={
                "evidence_labels": labels,
                "evidence_locators": locators,
                "knowledge_snapshot_id": knowledge_snapshot_id,
            },
        ),
        _response_registry(audience),
    )
    response = _harden_case_response(
        response,
        trigger_status=(
            str(context_values.get("trigger_status"))
            if context_values.get("trigger_status")
            else None
        ),
    )
    if not isinstance(response, ResponseAssemblerOutput):
        raise GuardedStarComprehensivePilotError("pilot hardening did not return ResponseAssemblerOutput")
    response = _apply_currentness_limitation(response, temporal_status=temporal_status)

    render_conformance = _evaluate_release(response)
    if render_conformance.outcome != "PASS" or render_conformance.rendered_text is None:
        raise GuardedStarComprehensivePilotError(
            "rendering exit safety blocked release: " + ",".join(render_conformance.violations)
        )

    limitations = tuple(
        dict.fromkeys(
            tuple(evidence.limitations)
            + tuple(reasoning.limitations)
            + tuple(decision.limitations)
            + tuple(explanation.limitations)
            + tuple(response.limitations)
        )
    )
    pilot_id = _stable_id(
        "guarded-star-copay-pilot",
        request_id,
        knowledge_snapshot_id,
        authority.authority_class,
        intent.primary_intent,
        reconciliation.reconciliation_status,
        identity_resolution.resolution_id,
        sha256(identity_path.read_bytes()).hexdigest(),
        temporal_status,
        plan.plan_id,
        evidence.resolution_id,
        reasoning.reasoning_id,
        decision.decision_id,
        explanation.explanation_id,
        response.response_id,
        render_conformance.outcome,
    )
    return GuardedStarComprehensivePilotResult(
        pilot_id=pilot_id,
        request_id=request_id,
        product_reference=PRODUCT_REFERENCE,
        topic=TOPIC,
        question=clean_question,
        knowledge_snapshot_id=knowledge_snapshot_id,
        authority=authority,
        intent=intent,
        reconciliation=reconciliation,
        context=built_context,
        identity_resolution=identity_resolution,
        identity_record_ref=_identity_record_ref(identity_path),
        identity_record_hash=sha256(identity_path.read_bytes()).hexdigest(),
        temporal_status=temporal_status,
        instance_sufficiency=instance_sufficiency,
        evidence_enforcement=evidence_enforcement,
        plan=plan,
        evidence=evidence,
        reasoning=reasoning,
        authority_enforcement=authority_enforcement,
        decision=decision,
        explanation=explanation,
        response=response,
        render_conformance=render_conformance,
        released_response_id=response.response_id,
        used_llm=False,
        limitations=limitations,
        guard_status="GUARDED",
    )
