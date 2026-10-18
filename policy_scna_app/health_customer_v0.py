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
from insurance_intelligence.education_publication.repository import EducationPublicationRepository
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

_SEMANTIC_FACTS = frozenset({"definition", "applicability", "consequence", "mechanics"})
_OUTCOME_DEFAULT_FACT = {
    "POLICY_FACT_EXPLANATION": "definition",
    "INSURANCE_MECHANICS_EXPLANATION": "mechanics",
    "POLICY_FACT_COMPARISON": "mechanics",
    "CONTEXTUAL_POLICY_EXPLANATION": "applicability",
    "ADVISORY_DECISION_SUPPORT": "consequence",
}


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
        semantic_fact_ids=tuple(sorted(_SEMANTIC_FACTS)),
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


def _customer_facing_boundary(text: str) -> str:
    """Remove internal governance phrasing without changing the insurance boundary."""
    return (
        text.replace("governed product knowledge", "the applicable product wording")
        .replace("governed product evidence", "the applicable product wording")
        .replace("governed policy evidence", "the applicable policy wording")
    )


def _resolved_semantic_fact(*, requested_semantic_fact: str | None, requested_outcome: str | None) -> str:
    if requested_semantic_fact is not None:
        if requested_semantic_fact not in _SEMANTIC_FACTS:
            raise HealthCustomerPathError(
                f"validated semantic fact is unsupported by Health customer v0: {requested_semantic_fact}"
            )
        return requested_semantic_fact
    fallback = _OUTCOME_DEFAULT_FACT.get(requested_outcome or "")
    if fallback is None:
        raise HealthCustomerPathError("resolved interpretation has no usable semantic answer shape")
    return fallback


def _education_response(
    *,
    request_id: str,
    selected_concept_id: str,
    requested_semantic_fact: str | None,
    requested_outcome: str | None,
    publication,
) -> tuple[ResponseAssemblerOutput, str]:
    """Project only the governed education components relevant to the validated request shape."""
    definition = _concept_definition(selected_concept_id)
    topic = definition.downstream_topic
    if topic is None:
        raise HealthCustomerPathError("selected concept has no downstream topic")

    enforce_relevance(asked_concept_id=selected_concept_id, answer_topic=publication.concept_id)
    semantic_fact = _resolved_semantic_fact(
        requested_semantic_fact=requested_semantic_fact,
        requested_outcome=requested_outcome,
    )

    # The GSI chooses only the request shape. Insurance meaning still comes exclusively from
    # the authoritative education publication. The mapping is concept-neutral.
    components: list[tuple[str, str, str]] = []
    if requested_outcome == "POLICY_FACT_COMPARISON":
        components.extend(
            (
                ("DIRECT_ANSWER", "comparison-mechanic", publication.practical_implication),
                (
                    "CUSTOMER_QUALIFICATION",
                    "comparison-boundary",
                    _customer_facing_boundary(publication.product_specific_boundary),
                ),
            )
        )
    elif semantic_fact == "definition":
        components.append(("DIRECT_ANSWER", "definition", publication.plain_language_explanation))
    elif semantic_fact == "applicability":
        components.extend(
            (
                ("DIRECT_ANSWER", "applicability", publication.practical_implication),
                (
                    "CUSTOMER_QUALIFICATION",
                    "customer-boundary",
                    _customer_facing_boundary(publication.customer_document_boundary),
                ),
            )
        )
    elif semantic_fact == "consequence":
        components.extend(
            (
                ("DIRECT_ANSWER", "consequence", publication.practical_implication),
                (
                    "CUSTOMER_QUALIFICATION",
                    "consequence-boundary",
                    _customer_facing_boundary(publication.product_specific_boundary),
                ),
            )
        )
    elif semantic_fact == "mechanics":
        components.append(("DIRECT_ANSWER", "mechanics", publication.practical_implication))
        for index, example in enumerate(publication.examples, start=1):
            components.append(
                (
                    "EXAMPLE",
                    f"example-{index}",
                    f"Example: {example.scenario} {example.result} {example.boundary}",
                )
            )
        components.append(
            (
                "CUSTOMER_QUALIFICATION",
                "mechanics-boundary",
                _customer_facing_boundary(publication.product_specific_boundary),
            )
        )
    else:  # pragma: no cover - exhaustive guard for future enum changes
        raise HealthCustomerPathError(f"unsupported semantic answer shape: {semantic_fact}")

    if not components:
        raise HealthCustomerPathError("question-relative education projection produced no sections")

    sections = []
    for section_type, role, text in components:
        sections.append(
            build_response_section(
                section_id=_stable_id("section", request_id, role, publication.publication_id),
                section_type=section_type,
                status="INCLUDED",
                text=text,
                education_publication_ids=(publication.publication_id,),
            )
        )

    direct_answer = sections[0].text
    response = build_response_output(
        request_id=request_id,
        response_id=_stable_id(
            "response",
            request_id,
            publication.publication_id,
            semantic_fact,
            requested_outcome or "none",
        ),
        response_status="ANSWER_WITH_LIMITATIONS" if publication.limitations else "ANSWER",
        audience="CUSTOMER",
        response_format="STANDARD",
        direct_answer=direct_answer,
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
    Customer insurance meaning comes only from validated education publications. Validated GSI
    request-shape fields may select which governed education components are presented. A
    relevance invariant runs before Rendering Exit Safety.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be non-empty text")
    if not isinstance(model_name, str) or not model_name.strip():
        raise ValueError("model_name must be non-empty text")
    if conversation_context is not None and not isinstance(
        conversation_context, HealthConversationContext
    ):
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
        requested_semantic_fact=interpretation.requested_semantic_fact,
        requested_outcome=interpretation.requested_outcome,
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
