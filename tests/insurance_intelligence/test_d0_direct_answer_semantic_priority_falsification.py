from __future__ import annotations

from insurance_intelligence.contracts.decision import (
    build_approved_response_packet,
    build_finding_disposition,
    build_output as build_decision_output,
)
from insurance_intelligence.contracts.explanation import (
    ExplanationGeneratorOutput,
    build_section as explanation_section,
)
from insurance_intelligence.contracts.response import build_input as build_response_input
from insurance_intelligence.response.registry import (
    ResponseFormatRegistry,
    build_format_definition,
)
from insurance_intelligence.response.service import assemble_response


def _decision():
    packet = build_approved_response_packet(
        packet_id="packet-1",
        approved_finding_ids=("finding-duration", "finding-continuity"),
        approved_evidence_ids=("ev-duration", "ev-continuity"),
    )
    return build_decision_output(
        request_id="req-1",
        decision_id="decision-1",
        decision="APPROVED",
        finding_dispositions=(
            build_finding_disposition(
                finding_id="finding-duration",
                disposition="APPROVED",
                basis="governed duration fact",
                approved_evidence_ids=("ev-duration",),
                confidence=1.0,
            ),
            build_finding_disposition(
                finding_id="finding-continuity",
                disposition="APPROVED",
                basis="governed continuity qualification",
                approved_evidence_ids=("ev-continuity",),
                confidence=1.0,
            ),
        ),
        response_packet=packet,
        confidence=1.0,
    )


def _format():
    return ResponseFormatRegistry((
        build_format_definition(
            format_id="customer-standard-v1",
            format_version="1.0",
            response_format="STANDARD",
            audiences=("CUSTOMER",),
            response_statuses=("ANSWER",),
            section_order=("DIRECT_ANSWER", "EDUCATION", "EXPLANATION", "CONDITION"),
            allowed_section_types=("DIRECT_ANSWER", "EDUCATION", "EXPLANATION", "CONDITION"),
            direct_answer_policy="REQUIRED",
            evidence_policy="WHEN_AVAILABLE",
            limitation_policy="REQUIRED_WHEN_PRESENT",
            clarification_policy="FORBIDDEN",
        ),
    ))


def _explanation(*, reverse: bool):
    duration = explanation_section(
        section_id="zz-duration" if not reverse else "aa-duration",
        section_type="MEANING",
        status="DRAFTED",
        text="The waiting period duration is 36 MONTHS.",
        approved_finding_ids=("finding-duration",),
        evidence_ids=("ev-duration",),
    )
    continuity = explanation_section(
        section_id="aa-continuity" if not reverse else "zz-continuity",
        section_type="MEANING",
        status="DRAFTED",
        text=(
            "If you have continuous prior coverage under applicable portability norms, "
            "the waiting period can be reduced to the extent of prior coverage."
        ),
        approved_finding_ids=("finding-continuity",),
        evidence_ids=("ev-continuity",),
    )
    sections = (duration, continuity)
    return ExplanationGeneratorOutput(
        contract_version="1.0",
        request_id="req-1",
        explanation_id="exp-1",
        audience="CUSTOMER",
        reading_level="SIMPLE",
        explanation_mode="PLAIN_LANGUAGE",
        sections=sections,
        terminology_substitutions=(),
        fidelity_checks=(),
        fidelity_status="VERIFIED",
        limitations=(),
        explanation_status="DRAFTED",
        confidence=1.0,
        explanation_trace=(),
    )


def test_direct_answer_selection_is_semantic_not_section_id_order() -> None:
    outputs = []
    for reverse in (False, True):
        assembled = assemble_response(
            build_response_input(
                request_id="req-1",
                decision_output=_decision(),
                explanation_output=_explanation(reverse=reverse),
                response_format="STANDARD",
            ),
            _format(),
        )
        outputs.append(assembled.direct_answer)

    assert outputs == [
        "The waiting period duration is 36 MONTHS.",
        "The waiting period duration is 36 MONTHS.",
    ]
