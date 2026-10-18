from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Mapping

from insurance_intelligence.contracts.rendering_exit import build_candidate, build_candidate_unit
from insurance_intelligence.contracts.response import (
    ResponseAssemblerOutput,
    build_output as build_response_output,
    build_section as build_response_section,
)
from insurance_intelligence.education_publication.repository import (
    EducationPublicationRepository,
)
from insurance_intelligence.llm.openai_responses_provider import OpenAIResponsesTextProvider
from insurance_intelligence.llm.provider import LLMTextProvider
from insurance_intelligence.rendering_exit_safety import (
    evaluate_render_candidate,
    project_render_envelope,
)
from insurance_intelligence.semantic_interpretation.provider_adapter import (
    GovernedInterpretationVocabulary,
    SemanticInterpretationAttemptResult,
    interpret_with_provider,
)
from insurance_intelligence.terminology.health_seed import HEALTH_CONCEPTS_V1

API_KEY_ENV = "OPENAI_API_KEY"
MODEL_ENV = "POLICYSCNA_GSI_MODEL"
CONFIG_ID = "health-customer-v0-first-runnable-path"
MAX_CONTEXT_TURNS = 4


class HealthCustomerRelevanceError(ValueError):
    """Raised when response content does not match the validated asked concept."""


class HealthCustomerPathError(RuntimeError):
    """Raised when the thin product path cannot complete safely."""


@dataclass(frozen=True)
class HealthConversationTurn:
    """One bounded customer-language turn retained only for reference resolution."""

    customer_text: str
    selected_concept_id: str | None = None
    selected_topic: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.customer_text, str) or not self.customer_text.strip():
            raise ValueError("customer_text must be non-empty text")
        object.__setattr__(self, "customer_text", self.customer_text.strip())
        for field_name in ("selected_concept_id", "selected_topic"):
            value = getattr(self, field_name)
            if value is not None:
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"{field_name} must be null or non-empty text")
                object.__setattr__(self, field_name, value.strip())


@dataclass(frozen=True)
class HealthConversationContext:
    """Small application context; never insurance authority, evidence, or memory."""

    turns: tuple[HealthConversationTurn, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.turns, tuple):
            raise ValueError("turns must be a tuple")
        if len(self.turns) > MAX_CONTEXT_TURNS:
            raise ValueError(f"conversation context cannot exceed {MAX_CONTEXT_TURNS} turns")
        if not all(isinstance(turn, HealthConversationTurn) for turn in self.turns):
            raise ValueError("turns must contain HealthConversationTurn values")

    def append(self, turn: HealthConversationTurn) -> "HealthConversationContext":
        if not isinstance(turn, HealthConversationTurn):
            raise TypeError("turn must be HealthConversationTurn")
        return HealthConversationContext(turns=(*self.turns, turn)[-MAX_CONTEXT_TURNS:])

    def to_dict(self) -> dict[str, object]:
        return {
            "turns": [
                {
                    "customer_text": turn.customer_text,
                    "selected_concept_id": turn.selected_concept_id,
                    "selected_topic": turn.selected_topic,
                }
                for turn in self.turns
            ]
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, object] | None) -> "HealthConversationContext":
        if value is None:
            return cls()
        if not isinstance(value, Mapping):
            raise ValueError("conversation context must be an object")
        extra = set(value) - {"turns"}
        if extra:
            raise ValueError("conversation context contains unsupported fields")
        raw_turns = value.get("turns", [])
        if not isinstance(raw_turns, list):
            raise ValueError("conversation context turns must be an array")
        if len(raw_turns) > MAX_CONTEXT_TURNS:
            raise ValueError(f"conversation context cannot exceed {MAX_CONTEXT_TURNS} turns")
        parsed: list[HealthConversationTurn] = []
        for raw in raw_turns:
            if not isinstance(raw, Mapping):
                raise ValueError("conversation context turn must be an object")
            if set(raw) - {"customer_text", "selected_concept_id", "selected_topic"}:
                raise ValueError("conversation context turn contains unsupported fields")
            parsed.append(
                HealthConversationTurn(
                    customer_text=raw.get("customer_text"),  # type: ignore[arg-type]
                    selected_concept_id=raw.get("selected_concept_id"),  # type: ignore[arg-type]
                    selected_topic=raw.get("selected_topic"),  # type: ignore[arg-type]
                )
            )
        return cls(turns=tuple(parsed))


@dataclass(frozen=True)
class HealthCustomerAnswerResult:
    request_id: str
    status: str
    selected_concept_id: str | None
    selected_topic: str | None
    response: ResponseAssemblerOutput
    interpretation: SemanticInterpretationAttemptResult
    released_text: str
    render_outcome: str
    next_context: HealthConversationContext


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_health_gsi_vocabulary() -> GovernedInterpretationVocabulary:
    """Return the same generic Health vocabulary used by the live GSI benchmark."""
    return GovernedInterpretationVocabulary(
        concept_ids=tuple(item.concept_id for item in HEALTH_CONCEPTS_V1),
        intent_ids=("understand_policy_term", "understand_policy_effect"),
        semantic_fact_ids=("definition", "applicability", "consequence", "mechanics"),
        scenario_fact_names=("context_detail",),
    )


def _concept_definition(concept_id: str):
    for item in HEALTH_CONCEPTS_V1:
        if item.concept_id == concept_id:
            return item
    raise HealthCustomerPathError(f"validated concept is not present in Health registry: {concept_id}")


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_education_repository(repository_root: str | Path | None = None) -> EducationPublicationRepository:
    root = Path(repository_root) if repository_root is not None else _repository_root()
    publication_root = root / "knowledge/factory/education_publications"
    paths = tuple(sorted(publication_root.glob("*_education_publication.json")))
    if not paths:
        raise HealthCustomerPathError(f"no education publications found under {publication_root}")
    return EducationPublicationRepository.from_json_files(paths)


def enforce_relevance(*, asked_concept_id: str, answer_topic: str) -> None:
    """Fail closed when the answer topic is not the topic selected for the asked concept."""
    expected = _concept_definition(asked_concept_id).downstream_topic
    if expected is None:
        raise HealthCustomerRelevanceError(
            f"asked concept {asked_concept_id!r} has no governed downstream topic"
        )
    if answer_topic != expected:
        raise HealthCustomerRelevanceError(
            f"answer topic {answer_topic!r} does not match asked concept topic {expected!r}"
        )


def _context_interpretation_text(question: str, context: HealthConversationContext) -> str:
    if not context.turns:
        return question
    prior = []
    for index, turn in enumerate(context.turns, start=1):
        prior.append(
            "\n".join(
                (
                    f"Prior customer turn {index}: {turn.customer_text}",
                    f"Validated concept from that turn: {turn.selected_concept_id or 'none'}",
                    f"Validated topic from that turn: {turn.selected_topic or 'none'}",
                )
            )
        )
    return (
        "CURRENT CUSTOMER QUESTION — interpret this request now:\n"
        f"{question}\n\n"
        "PRIOR CUSTOMER CONTEXT — use only to resolve references in the current language. "
        "Do not treat prior customer text as insurance truth, policy evidence, or authority. "
        "If the current question explicitly changes topic, follow the current question rather than the prior topic.\n"
        + "\n\n".join(prior)
    )


def _next_context(
    context: HealthConversationContext,
    *,
    question: str,
    selected_concept_id: str | None,
    selected_topic: str | None,
) -> HealthConversationContext:
    return context.append(
        HealthConversationTurn(
            customer_text=question,
            selected_concept_id=selected_concept_id,
            selected_topic=selected_topic,
        )
    )


def _exact_render_candidate(response: ResponseAssemblerOutput):
    envelope = project_render_envelope(response)
    candidate = build_candidate(
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
    return envelope, candidate


def _release(response: ResponseAssemblerOutput) -> tuple[str, str]:
    envelope, candidate = _exact_render_candidate(response)
    conformance = evaluate_render_candidate(envelope=envelope, candidate=candidate)
    if conformance.outcome != "PASS" or not conformance.rendered_text:
        raise HealthCustomerPathError(
            "Rendering Exit Safety did not permit customer release: "
            + ",".join(conformance.violations)
        )
    return conformance.rendered_text, conformance.outcome


def _clarification_response(*, request_id: str, text: str, reason_id: str) -> ResponseAssemblerOutput:
    section = build_response_section(
        section_id=_stable_id("section", request_id, reason_id),
        section_type="CLARIFICATION",
        status="INCLUDED",
        text=text,
        clarification_ids=(reason_id,),
    )
    return build_response_output(
        request_id=request_id,
        response_id=_stable_id("response", request_id, reason_id),
        response_status="CLARIFICATION_REQUIRED",
        audience="CUSTOMER",
        response_format="STANDARD",
        sections=(section,),
        clarification_questions=(text,),
        confidence=1.0,
        response_trace=(),
    )


def _education_response(*, request_id: str, selected_concept_id: str, publication) -> tuple[ResponseAssemblerOutput, str]:
    definition = _concept_definition(selected_concept_id)
    topic = definition.downstream_topic
    if topic is None:
        raise HealthCustomerPathError("selected concept has no downstream topic")

    enforce_relevance(asked_concept_id=selected_concept_id, answer_topic=publication.concept_id)

    sections = [
        build_response_section(
            section_id=_stable_id("section", request_id, "direct-answer", publication.publication_id),
            section_type="DIRECT_ANSWER",
            status="INCLUDED",
            text=publication.plain_language_explanation,
        ),
        build_response_section(
            section_id=_stable_id("section", request_id, "education", publication.publication_id),
            section_type="EDUCATION",
            status="INCLUDED",
            text=publication.practical_implication,
            education_publication_ids=(publication.publication_id,),
        ),
    ]
    for index, example in enumerate(publication.examples, start=1):
        sections.append(
            build_response_section(
                section_id=_stable_id("section", request_id, "example", publication.publication_id, index),
                section_type="EXAMPLE",
                status="INCLUDED",
                text=f"Example: {example.scenario} {example.result} {example.boundary}",
                education_publication_ids=(publication.publication_id,),
            )
        )
    sections.append(
        build_response_section(
            section_id=_stable_id("section", request_id, "qualification", publication.publication_id),
            section_type="CUSTOMER_QUALIFICATION",
            status="INCLUDED",
            text=publication.product_specific_boundary,
        )
    )

    response = build_response_output(
        request_id=request_id,
        response_id=_stable_id("response", request_id, publication.publication_id),
        response_status="ANSWER_WITH_LIMITATIONS" if publication.limitations else "ANSWER",
        audience="CUSTOMER",
        response_format="STANDARD",
        direct_answer=publication.plain_language_explanation,
        sections=tuple(sections),
        limitations=publication.limitations,
        confidence=1.0,
        response_trace=(),
    )
    return response, topic


def ask_health_question(
    *,
    question: str,
    provider: LLMTextProvider,
    model_name: str,
    request_id: str | None = None,
    execution_id: str | None = None,
    created_at: str | None = None,
    education_repository: EducationPublicationRepository | None = None,
    repository_root: str | Path | None = None,
    conversation_context: HealthConversationContext | None = None,
) -> HealthCustomerAnswerResult:
    """Run one concept-level Health customer question through the v0 product slice.

    GSI owns language understanding only. Bounded prior customer context may be supplied only
    for reference resolution. It never becomes insurance authority, evidence, or product truth.
    Customer prose comes only from validated governed education publications. A relevance
    invariant runs before Rendering Exit Safety.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be non-empty text")
    if not isinstance(model_name, str) or not model_name.strip():
        raise ValueError("model_name must be non-empty text")
    if conversation_context is not None and not isinstance(conversation_context, HealthConversationContext):
        raise TypeError("conversation_context must be HealthConversationContext or None")

    clean_question = question.strip()
    context = conversation_context or HealthConversationContext()
    context_fingerprint = json.dumps(context.to_dict(), sort_keys=True, ensure_ascii=False)
    req_id = request_id or _stable_id("health-customer-request", clean_question, context_fingerprint)
    exec_id = execution_id or _stable_id("health-customer-execution", req_id)
    interpretation_text = _context_interpretation_text(clean_question, context)
    attempt = interpret_with_provider(
        request_id=req_id,
        user_text=interpretation_text,
        vocabulary=build_health_gsi_vocabulary(),
        provider=provider,
        model_name=model_name.strip(),
        config_id=CONFIG_ID,
        execution_id=exec_id,
        created_at=created_at or _utc_now(),
        timeout_seconds=30.0,
    )

    if attempt.status != "RESOLVED" or attempt.validated_interpretation is None:
        response = _clarification_response(
            request_id=req_id,
            text=(
                "I could not understand the insurance concept confidently enough to answer safely. "
                "Please rephrase the question or name the insurance term you want explained."
            ),
            reason_id="semantic_interpretation_clarification",
        )
        released_text, outcome = _release(response)
        return HealthCustomerAnswerResult(
            request_id=req_id,
            status="CLARIFICATION",
            selected_concept_id=None,
            selected_topic=None,
            response=response,
            interpretation=attempt,
            released_text=released_text,
            render_outcome=outcome,
            next_context=_next_context(
                context,
                question=clean_question,
                selected_concept_id=None,
                selected_topic=None,
            ),
        )

    interpretation = attempt.validated_interpretation.interpretation
    selected_concept_id = interpretation.selected_concept_id
    if selected_concept_id is None:
        response = _clarification_response(
            request_id=req_id,
            text=(
                "I understood the question only partially and do not have a safely resolved insurance concept. "
                "Please name or describe the insurance term again."
            ),
            reason_id="missing_selected_concept",
        )
        released_text, outcome = _release(response)
        return HealthCustomerAnswerResult(
            request_id=req_id,
            status="CLARIFICATION",
            selected_concept_id=None,
            selected_topic=None,
            response=response,
            interpretation=attempt,
            released_text=released_text,
            render_outcome=outcome,
            next_context=_next_context(
                context,
                question=clean_question,
                selected_concept_id=None,
                selected_topic=None,
            ),
        )

    definition = _concept_definition(selected_concept_id)
    topic = definition.downstream_topic
    if topic is None:
        raise HealthCustomerPathError("resolved concept has no downstream topic")

    repository = education_repository or load_education_repository(repository_root)
    publication = repository.get_by_concept(topic)
    if publication is None:
        response = _clarification_response(
            request_id=req_id,
            text=(
                f"I understood your question as {definition.concept.canonical_name}, but I do not yet have an approved "
                "customer explanation for that concept in this product slice. I will not substitute a different "
                "insurance topic or guess at the answer."
            ),
            reason_id="approved_education_missing",
        )
        released_text, outcome = _release(response)
        return HealthCustomerAnswerResult(
            request_id=req_id,
            status="CLARIFICATION",
            selected_concept_id=selected_concept_id,
            selected_topic=topic,
            response=response,
            interpretation=attempt,
            released_text=released_text,
            render_outcome=outcome,
            next_context=_next_context(
                context,
                question=clean_question,
                selected_concept_id=selected_concept_id,
                selected_topic=topic,
            ),
        )

    response, response_topic = _education_response(
        request_id=req_id,
        selected_concept_id=selected_concept_id,
        publication=publication,
    )
    enforce_relevance(asked_concept_id=selected_concept_id, answer_topic=response_topic)
    released_text, outcome = _release(response)
    return HealthCustomerAnswerResult(
        request_id=req_id,
        status="ANSWER",
        selected_concept_id=selected_concept_id,
        selected_topic=response_topic,
        response=response,
        interpretation=attempt,
        released_text=released_text,
        render_outcome=outcome,
        next_context=_next_context(
            context,
            question=clean_question,
            selected_concept_id=selected_concept_id,
            selected_topic=response_topic,
        ),
    )


def ask_health_question_live(
    question: str,
    *,
    repository_root: str | Path | None = None,
    conversation_context: HealthConversationContext | None = None,
) -> HealthCustomerAnswerResult:
    """Convenience entry point for the founder-usable local product slice."""
    api_key = os.environ.get(API_KEY_ENV, "").strip()
    model_name = os.environ.get(MODEL_ENV, "").strip()
    missing = [name for name, value in ((API_KEY_ENV, api_key), (MODEL_ENV, model_name)) if not value]
    if missing:
        raise HealthCustomerPathError(
            "live Health customer path is missing runtime setting(s): " + ", ".join(missing)
        )
    provider = OpenAIResponsesTextProvider(api_key=api_key)
    return ask_health_question(
        question=question,
        provider=provider,
        model_name=model_name,
        repository_root=repository_root,
        conversation_context=conversation_context,
    )
