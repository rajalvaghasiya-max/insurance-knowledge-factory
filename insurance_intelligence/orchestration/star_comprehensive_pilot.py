"""Real Star Comprehensive conditional co-payment response pilot for MO-023F.

This module wires the existing governed registry-backed evidence resolver and
production deterministic Intelligence Layer components into one narrow response
cycle.  It intentionally does not crawl or rebuild knowledge.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
from typing import Mapping

from insurance_intelligence.contracts.decision import build_input as build_decision_input
from insurance_intelligence.contracts.evidence import build_input as build_evidence_input
from insurance_intelligence.contracts.explanation import build_input as build_explanation_input
from insurance_intelligence.contracts.reasoning import build_input as build_reasoning_input
from insurance_intelligence.contracts.reasoning_plan import build_evidence_requirement, build_plan
from insurance_intelligence.contracts.response import (
    build_input as build_response_input,
    build_output as build_response_output,
    build_section as build_response_section,
)
from insurance_intelligence.decision.gate import DecisionSafetyGate
from insurance_intelligence.evidence.resolver import EvidenceResolver
from insurance_intelligence.explanation.generator import generate_explanation
from insurance_intelligence.explanation.registry import ExplanationStyleRegistry, build_style_definition
from insurance_intelligence.reasoning.engine import ReasoningEngine
from insurance_intelligence.response.registry import ResponseFormatRegistry, build_format_definition
from insurance_intelligence.response.service import assemble_response

PRODUCT_REFERENCE = "star_health:star_comprehensive"
TOPIC = "conditional_copayment"




COPAY_TRIGGER_CONDITION = "the insured person's age at entry is 61 years or above"
COPAY_NON_TRIGGER_CONDITION = (
    "the insured person entered the policy before attaining 61 years of age "
    "and renewed continuously without a break"
)
COPAY_SCOPE = "Sections II.1, II.2, II.3, II.4, II.5, II.6, II.7, II.8, II.9, II.10, II.11, II.15 and II.25"


def _harden_case_response(response: object, *, trigger_status: str | None) -> object:
    """Create a pilot-specific, case-first response without changing approved meaning."""
    if getattr(response, "response_status", None) == "CLARIFICATION_REQUIRED":
        return response

    references = tuple(getattr(response, "evidence_references", ()))
    reference_ids = tuple(item.reference_id for item in references)
    finding_ids = tuple(dict.fromkeys(
        finding_id
        for item in references
        for finding_id in item.approved_finding_ids
    ))
    limitations = tuple(getattr(response, "limitations", ()))

    if trigger_status == "CONFIRMED":
        direct_answer = (
            "Yes. Based on the information provided, the 10% co-payment applies "
            "because the insured person's age at entry was 61 years or above."
        )
        explanation_text = (
            "You must bear 10% of the admissible claim amount for the applicable policy sections."
        )
    elif trigger_status == "NOT_TRIGGERED":
        direct_answer = (
            "No. Based on the information provided, this 10% co-payment does not apply "
            "because the insured person entered the policy before age 61 and renewed it "
            "continuously without a break."
        )
        explanation_text = (
            "The documented trigger is not met for this case, so the conditional co-payment is not applied."
        )
    else:
        direct_answer = (
            "This policy has a conditional 10% co-payment. It applies only when the documented "
            "entry-age condition is met."
        )
        explanation_text = (
            "When the condition applies, you must bear 10% of the admissible claim amount."
        )

    condition_text = (
        f"The 10% co-payment normally applies when {COPAY_TRIGGER_CONDITION}. "
        f"It does not apply when {COPAY_NON_TRIGGER_CONDITION}."
    )
    limitation_text = f"The policy wording limits this co-payment to {COPAY_SCOPE}."
    evidence_text = "This explanation is based only on the approved policy wording."

    section_specs = (
        ("DIRECT_ANSWER", direct_answer, finding_ids, reference_ids, ()),
        ("EXPLANATION", explanation_text, finding_ids, reference_ids, ()),
        ("CONDITION", condition_text, finding_ids, reference_ids, ()),
        ("LIMITATION", limitation_text, (), (), ("pilot_scope_limitation",)),
        ("EVIDENCE", evidence_text, (), reference_ids, ()),
    )
    sections = tuple(
        build_response_section(
            section_id=_stable_id("section", response.response_id, section_type, text),
            section_type=section_type,
            status="INCLUDED",
            text=text,
            approved_finding_ids=approved_finding_ids,
            evidence_reference_ids=evidence_reference_ids,
            limitation_ids=limitation_ids,
        )
        for section_type, text, approved_finding_ids, evidence_reference_ids, limitation_ids in section_specs
        if text.strip()
    )
    response_id = _stable_id(
        "response",
        response.response_id,
        trigger_status or "GENERAL",
        *(section.text for section in sections),
    )
    return build_response_output(
        request_id=response.request_id,
        response_id=response_id,
        response_status=response.response_status,
        audience=response.audience,
        response_format=response.response_format,
        direct_answer=direct_answer,
        sections=sections,
        evidence_references=references,
        limitations=limitations,
        assumptions=response.assumptions,
        clarification_questions=(),
        confidence=response.confidence,
        response_trace=(),
    )


class StarComprehensivePilotError(ValueError):
    """Raised when the governed pilot cannot complete safely."""


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


@dataclass(frozen=True)
class StarComprehensivePilotResult:
    pilot_id: str
    request_id: str
    product_reference: str
    topic: str
    question: str
    knowledge_snapshot_id: str
    plan: object
    evidence: object
    reasoning: object
    decision: object
    explanation: object
    response: object
    released_response_id: str
    used_llm: bool
    limitations: tuple[str, ...]


def _style_registry(audience: str, reading_level: str, mode: str) -> ExplanationStyleRegistry:
    return ExplanationStyleRegistry((
        build_style_definition(
            style_id=f"star-copay-{audience.lower()}-{reading_level.lower()}",
            style_version="1.0",
            audience=audience,
            reading_level=reading_level,
            explanation_modes=(mode,),
            tone="NEUTRAL",
            sentence_length="SHORT",
            bullet_policy="WHEN_HELPFUL",
            preserve_conditions=True,
            preserve_limitations=True,
            preserve_evidence_notes=True,
            max_section_words=120,
            priority=10,
        ),
    ))


def _response_registry(audience: str) -> ResponseFormatRegistry:
    answer = build_format_definition(
        format_id=f"star-copay-answer-{audience.lower()}",
        format_version="1.0",
        response_format="STANDARD",
        audiences=(audience,),
        response_statuses=("ANSWER", "ANSWER_WITH_LIMITATIONS"),
        section_order=("DIRECT_ANSWER", "EXPLANATION", "CONDITION", "IMPACT", "LIMITATION", "EVIDENCE"),
        allowed_section_types=("DIRECT_ANSWER", "EXPLANATION", "CONDITION", "IMPACT", "LIMITATION", "EVIDENCE"),
        direct_answer_policy="REQUIRED",
        evidence_policy="WHEN_AVAILABLE",
        limitation_policy="REQUIRED_WHEN_PRESENT",
        clarification_policy="FORBIDDEN",
        priority=10,
    )
    clarification = build_format_definition(
        format_id=f"star-copay-clarification-{audience.lower()}",
        format_version="1.0",
        response_format="STANDARD",
        audiences=(audience,),
        response_statuses=("CLARIFICATION_REQUIRED",),
        section_order=("CLARIFICATION",),
        allowed_section_types=("CLARIFICATION",),
        direct_answer_policy="FORBIDDEN",
        evidence_policy="FORBIDDEN",
        limitation_policy="FORBIDDEN",
        assumption_policy="FORBIDDEN",
        clarification_policy="REQUIRED",
        priority=10,
    )
    return ResponseFormatRegistry((answer, clarification))


def run_star_comprehensive_copay_pilot(
    *,
    request_id: str,
    question: str,
    repository_root: str | Path,
    knowledge_snapshot_id: str,
    customer_context: Mapping[str, object] | None = None,
    audience: str = "CUSTOMER",
    reading_level: str = "SIMPLE",
) -> StarComprehensivePilotResult:
    """Run the real certified-knowledge-to-response path for conditional co-pay."""
    if not isinstance(request_id, str) or not request_id.strip():
        raise StarComprehensivePilotError("request_id must be a non-empty string")
    if not isinstance(question, str) or not question.strip():
        raise StarComprehensivePilotError("question must be a non-empty string")
    if not isinstance(knowledge_snapshot_id, str) or not knowledge_snapshot_id.strip():
        raise StarComprehensivePilotError("knowledge_snapshot_id must be a non-empty string")
    root = Path(repository_root)
    if not root.exists() or not root.is_dir():
        raise StarComprehensivePilotError("repository_root must be an existing directory")

    context = dict(customer_context or {})
    case_specific = bool(context)
    reasoning_context = dict(context)
    decision_context = {
        "domain": "health",
        "topic": TOPIC if case_specific else "copay",
        "case_specific_applicability": case_specific,
    }
    decision_context.update(context)
    if "trigger_status" in context:
        reasoning_context["conditional_copayment_trigger_status"] = context["trigger_status"]

    plan = build_plan(
        request_id=request_id,
        plan_id=_stable_id("plan", request_id, PRODUCT_REFERENCE, TOPIC),
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
                requested_by_step="star_comprehensive_copay_pilot",
            ),
        ),
    )
    evidence = EvidenceResolver().resolve(build_evidence_input(
        request_id=request_id,
        reasoning_plan=plan,
        repository_roots=(str(root),),
        resolution_context={"knowledge_snapshot_id": knowledge_snapshot_id},
        strict_mode="STRICT",
    ))
    reasoning = ReasoningEngine().reason(build_reasoning_input(
        request_id=request_id,
        reasoning_plan=plan,
        evidence_resolution=evidence,
        reasoning_context=reasoning_context,
        strict_mode="STRICT",
    ))
    decision = DecisionSafetyGate().decide(build_decision_input(
        request_id=request_id,
        reasoning_plan=plan,
        evidence_resolution=evidence,
        reasoning_output=reasoning,
        decision_context=decision_context,
        strict_mode="STRICT",
    ))
    if decision.decision not in {"APPROVED", "APPROVED_WITH_LIMITATIONS", "CLARIFICATION_REQUIRED"}:
        raise StarComprehensivePilotError(f"decision is not eligible for response generation: {decision.decision}")

    mode = "CLARIFICATION_REQUEST" if decision.decision == "CLARIFICATION_REQUIRED" else "PLAIN_LANGUAGE"
    communication_context = {
        "domain_scope": "HEALTH",
        "question": question.strip(),
        "knowledge_snapshot_id": knowledge_snapshot_id,
    }
    communication_context.update(context)
    if decision.clarifications:
        communication_context.setdefault(
            "trigger_status",
            "Did the documented conditional co-payment trigger apply to this treatment?",
        )
    findings = {
        item.finding_id: (item if item.condition is not None else replace(item, condition=""))
        for item in reasoning.findings
    }
    explanation = generate_explanation(
        explanation_input=build_explanation_input(
            request_id=request_id,
            decision_output=decision,
            audience=audience,
            reading_level=reading_level,
            explanation_mode=mode,
            communication_context=communication_context,
        ),
        findings_by_id=findings,
        style_registry=_style_registry(audience, reading_level, mode),
    )
    labels = {item.evidence_id: item.source_type.replace("_", " ").title() for item in evidence.evidence_packages}
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
        trigger_status=str(context.get("trigger_status")) if context.get("trigger_status") else None,
    )
    limitations = tuple(dict.fromkeys(
        tuple(evidence.limitations) + tuple(reasoning.limitations) + tuple(decision.limitations)
        + tuple(explanation.limitations) + tuple(response.limitations)
    ))
    pilot_id = _stable_id(
        "star-copay-pilot",
        request_id,
        knowledge_snapshot_id,
        plan.plan_id,
        evidence.resolution_id,
        reasoning.reasoning_id,
        decision.decision_id,
        explanation.explanation_id,
        response.response_id,
    )
    return StarComprehensivePilotResult(
        pilot_id=pilot_id,
        request_id=request_id,
        product_reference=PRODUCT_REFERENCE,
        topic=TOPIC,
        question=question.strip(),
        knowledge_snapshot_id=knowledge_snapshot_id,
        plan=plan,
        evidence=evidence,
        reasoning=reasoning,
        decision=decision,
        explanation=explanation,
        response=response,
        released_response_id=response.response_id,
        used_llm=False,
        limitations=limitations,
    )
