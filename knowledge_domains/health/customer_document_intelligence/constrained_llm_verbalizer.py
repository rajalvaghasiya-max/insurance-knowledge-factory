"""Provider-neutral constrained LLM verbalizer boundary."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Mapping

from .verbalizer_request import (
    VerbalizerRequestAssembler,
    VerbalizerRequestError,
)


class ConstrainedVerbalizerError(ValueError):
    """Raised when an LLM response cannot form a governed draft artifact."""


class ConstrainedLLMVerbalizer:
    VERSION = "1.0"
    SCHEMA_VERSION = "1.0"
    RECORD_TYPE = "health_llm_verbalized_draft_v1"

    def verbalize(
        self,
        *,
        request: Mapping[str, Any],
        llm_callable: Callable[[Mapping[str, Any]], str],
        provider_metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            VerbalizerRequestAssembler.validate(request)
        except VerbalizerRequestError as exc:
            raise ConstrainedVerbalizerError(str(exc)) from exc

        if not callable(llm_callable):
            raise ConstrainedVerbalizerError("llm_callable must be callable")

        response_text = llm_callable(request)
        if not isinstance(response_text, str) or not response_text.strip():
            raise ConstrainedVerbalizerError(
                "LLM response must be a non-empty string"
            )
        clean_text = response_text.strip()
        maximum_words = int(
            request["output_requirements"]["maximum_words"]
        )

        draft = {
            "schema_version": self.SCHEMA_VERSION,
            "record_type": self.RECORD_TYPE,
            "contract_version": self.VERSION,
            "draft_id": self._draft_id(
                request_id=str(request["request_id"]),
                response_text=clean_text,
            ),
            "request_id": request["request_id"],
            "bundle_id": request["bundle_id"],
            "packet_id": request["packet_id"],
            "route_decision_id": request["route_decision_id"],
            "concept_id": request["concept_id"],
            "route": request["route"],
            "language": request["language"],
            "target_audience": request["target_audience"],
            "draft_text": clean_text,
            "word_count": len(clean_text.split()),
            "maximum_words": maximum_words,
            "provider_metadata": dict(provider_metadata or {}),
            "validation_state": "not_validated",
            "customer_answer_state": "draft_not_approved",
            "publication_state": "not_published",
            "entitlement_state": "not_evaluated",
            "recommendation_state": "not_created",
            "guardrails": [
                "llm_draft_not_source_of_insurance_truth",
                "llm_draft_requires_output_validation",
                "llm_draft_not_customer_answer",
                "llm_draft_not_publishable",
            ],
        }
        self.validate(draft)
        return draft

    @classmethod
    def validate(cls, draft: Mapping[str, Any]) -> None:
        if not isinstance(draft, Mapping):
            raise ConstrainedVerbalizerError("verbalized draft must be an object")
        if draft.get("schema_version") != cls.SCHEMA_VERSION:
            raise ConstrainedVerbalizerError("schema_version must be 1.0")
        if draft.get("record_type") != cls.RECORD_TYPE:
            raise ConstrainedVerbalizerError("unsupported record_type")
        if draft.get("contract_version") != cls.VERSION:
            raise ConstrainedVerbalizerError("unsupported contract_version")
        cls._require_prefixed(draft.get("draft_id"), "vdraft_", "draft_id")
        cls._require_prefixed(draft.get("request_id"), "vreq_", "request_id")
        cls._require_prefixed(draft.get("bundle_id"), "acbundle_", "bundle_id")
        cls._require_prefixed(draft.get("packet_id"), "ipacket_", "packet_id")
        cls._require_prefixed(
            draft.get("route_decision_id"), "aroute_", "route_decision_id"
        )
        if draft.get("concept_id") != "deductible":
            raise ConstrainedVerbalizerError("concept_id must be deductible")
        cls._require_nonempty(draft.get("draft_text"), "draft_text")

        word_count = draft.get("word_count")
        maximum_words = draft.get("maximum_words")
        if (
            not isinstance(word_count, int)
            or word_count < 1
            or not isinstance(maximum_words, int)
            or maximum_words < 1
        ):
            raise ConstrainedVerbalizerError(
                "word_count and maximum_words must be positive integers"
            )
        if word_count > maximum_words:
            raise ConstrainedVerbalizerError(
                "LLM response exceeds maximum_words"
            )
        if not isinstance(draft.get("provider_metadata"), Mapping):
            raise ConstrainedVerbalizerError(
                "provider_metadata must be an object"
            )

        required_states = {
            "validation_state": "not_validated",
            "customer_answer_state": "draft_not_approved",
            "publication_state": "not_published",
            "entitlement_state": "not_evaluated",
            "recommendation_state": "not_created",
        }
        for key, expected in required_states.items():
            if draft.get(key) != expected:
                raise ConstrainedVerbalizerError(f"{key} must be {expected}")

    @staticmethod
    def _draft_id(*, request_id: str, response_text: str) -> str:
        material = {
            "request_id": request_id,
            "response_sha256": hashlib.sha256(
                response_text.encode("utf-8")
            ).hexdigest(),
        }
        digest = hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()[:20]
        return f"vdraft_{digest}"

    @staticmethod
    def _require_nonempty(value: Any, name: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ConstrainedVerbalizerError(f"{name} must be non-empty")

    @classmethod
    def _require_prefixed(cls, value: Any, prefix: str, name: str) -> None:
        cls._require_nonempty(value, name)
        if not value.startswith(prefix):
            raise ConstrainedVerbalizerError(f"{name} must start with {prefix}")
