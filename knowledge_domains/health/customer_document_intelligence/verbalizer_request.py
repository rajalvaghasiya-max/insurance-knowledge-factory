"""Deterministic prompt payload for a constrained insurance verbalizer."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


class VerbalizerRequestError(ValueError):
    """Raised when an approved content bundle cannot form a safe LLM request."""


class VerbalizerRequestAssembler:
    VERSION = "1.0"
    SCHEMA_VERSION = "1.0"
    RECORD_TYPE = "health_llm_verbalizer_request_v1"

    def assemble(self, bundle: Mapping[str, Any]) -> dict[str, Any]:
        self._validate_bundle(bundle)

        request = {
            "schema_version": self.SCHEMA_VERSION,
            "record_type": self.RECORD_TYPE,
            "contract_version": self.VERSION,
            "request_id": self._request_id(
                bundle_id=str(bundle["bundle_id"]),
                route=str(bundle["route"]),
                language=str(bundle["language"]),
            ),
            "bundle_id": bundle["bundle_id"],
            "packet_id": bundle["packet_id"],
            "route_decision_id": bundle["route_decision_id"],
            "concept_id": bundle["concept_id"],
            "route": bundle["route"],
            "target_audience": bundle["target_audience"],
            "language": bundle["language"],
            "llm_role": "verbalizer_not_source_of_insurance_truth",
            "system_instruction": (
                "You are a constrained insurance verbalizer. Rewrite only the "
                "approved content supplied in this request. Do not add insurance "
                "facts, product mechanics, claim outcomes, legal conclusions, or "
                "recommendations. Preserve all required caveats. Clearly label any "
                "runtime-created example as an illustration."
            ),
            "task_instruction": bundle["verbalizer_instruction"],
            "approved_content": {
                "allowed_facts": [dict(item) for item in bundle["allowed_facts"]],
                "required_caveats": list(bundle["required_caveats"]),
                "required_clarifications": list(
                    bundle["required_clarifications"]
                ),
                "example_policy": dict(bundle["example_policy"]),
                "blocked_claims": list(bundle["blocked_claims"]),
            },
            "output_requirements": {
                "format": "plain_text",
                "maximum_paragraphs": 4,
                "maximum_words": 220,
                "must_not_include_markdown_table": True,
                "must_not_claim_validation_or_publication": True,
                "must_preserve_source_boundaries": True,
            },
            "source_refs": dict(bundle["source_refs"]),
            "draft_state": "not_created",
            "publication_state": "not_published",
            "entitlement_state": "not_evaluated",
            "recommendation_state": "not_created",
        }
        self.validate(request)
        return request

    @classmethod
    def validate(cls, request: Mapping[str, Any]) -> None:
        if not isinstance(request, Mapping):
            raise VerbalizerRequestError("verbalizer request must be an object")
        if request.get("schema_version") != cls.SCHEMA_VERSION:
            raise VerbalizerRequestError("schema_version must be 1.0")
        if request.get("record_type") != cls.RECORD_TYPE:
            raise VerbalizerRequestError("unsupported record_type")
        if request.get("contract_version") != cls.VERSION:
            raise VerbalizerRequestError("unsupported contract_version")
        cls._require_prefixed(request.get("request_id"), "vreq_", "request_id")
        cls._require_prefixed(request.get("bundle_id"), "acbundle_", "bundle_id")
        cls._require_prefixed(request.get("packet_id"), "ipacket_", "packet_id")
        cls._require_prefixed(
            request.get("route_decision_id"), "aroute_", "route_decision_id"
        )
        if request.get("concept_id") != "deductible":
            raise VerbalizerRequestError("concept_id must be deductible")
        if request.get("llm_role") != "verbalizer_not_source_of_insurance_truth":
            raise VerbalizerRequestError("invalid llm_role")
        cls._require_nonempty(
            request.get("system_instruction"), "system_instruction"
        )
        cls._require_nonempty(request.get("task_instruction"), "task_instruction")

        approved = request.get("approved_content")
        if not isinstance(approved, Mapping):
            raise VerbalizerRequestError("approved_content must be an object")
        for key in (
            "allowed_facts",
            "required_caveats",
            "required_clarifications",
            "blocked_claims",
        ):
            if not isinstance(approved.get(key), list):
                raise VerbalizerRequestError(
                    f"approved_content.{key} must be a list"
                )
        if not isinstance(approved.get("example_policy"), Mapping):
            raise VerbalizerRequestError(
                "approved_content.example_policy must be an object"
            )

        output = request.get("output_requirements")
        if not isinstance(output, Mapping):
            raise VerbalizerRequestError("output_requirements must be an object")
        if output.get("format") != "plain_text":
            raise VerbalizerRequestError("output format must be plain_text")
        if (
            not isinstance(output.get("maximum_words"), int)
            or output["maximum_words"] < 1
        ):
            raise VerbalizerRequestError("maximum_words must be positive")

        required_states = {
            "draft_state": "not_created",
            "publication_state": "not_published",
            "entitlement_state": "not_evaluated",
            "recommendation_state": "not_created",
        }
        for key, expected in required_states.items():
            if request.get(key) != expected:
                raise VerbalizerRequestError(f"{key} must be {expected}")

    @staticmethod
    def _validate_bundle(bundle: Mapping[str, Any]) -> None:
        if not isinstance(bundle, Mapping):
            raise VerbalizerRequestError("content bundle must be an object")
        if bundle.get("record_type") != (
            "health_approved_answer_content_bundle_v1"
        ):
            raise VerbalizerRequestError("unsupported content bundle type")
        VerbalizerRequestAssembler._require_prefixed(
            bundle.get("bundle_id"), "acbundle_", "bundle_id"
        )
        if bundle.get("route") not in {
            "answerable_from_grounded_packet",
            "clarification_required",
            "not_answerable",
            "blocked",
        }:
            raise VerbalizerRequestError("unsupported bundle route")

    @staticmethod
    def _request_id(*, bundle_id: str, route: str, language: str) -> str:
        material = {
            "bundle_id": bundle_id,
            "route": route,
            "language": language,
        }
        digest = hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()[:20]
        return f"vreq_{digest}"

    @staticmethod
    def _require_nonempty(value: Any, name: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise VerbalizerRequestError(f"{name} must be non-empty")

    @classmethod
    def _require_prefixed(cls, value: Any, prefix: str, name: str) -> None:
        cls._require_nonempty(value, name)
        if not value.startswith(prefix):
            raise VerbalizerRequestError(f"{name} must start with {prefix}")
