"""Governed interpretation packet for a matched Health customer-document fact.

The packet is a deterministic handoff artifact between customer-document
intelligence and future answer routing. It does not manufacture prose, decide
entitlement, or recommend an insurance action.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


class InterpretationPacketError(ValueError):
    """Raised when packet inputs or output violate the handoff contract."""


class InterpretationPacketAssembler:
    VERSION = "1.0"
    SCHEMA_VERSION = "1.0"
    PACKET_TYPE = "health_customer_document_interpretation_packet_v1"

    READY = "grounded_but_not_answered"
    NOT_READY = "not_ready"
    ALLOWED_READINESS = {READY, NOT_READY}

    def assemble(
        self,
        *,
        customer_fact: Mapping[str, Any],
        understanding_match: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._validate_customer_fact(customer_fact)
        self._validate_match(understanding_match)
        self._validate_cross_binding(customer_fact, understanding_match)

        ready = (
            customer_fact.get("status") == "extracted"
            and understanding_match.get("status") == "matched"
        )
        answer_readiness = self.READY if ready else self.NOT_READY
        readiness_reason = (
            "customer_fact_and_certified_understanding_are_grounded"
            if ready
            else "customer_fact_or_understanding_match_is_not_ready"
        )

        understanding = understanding_match.get("understanding_asset")
        traceability = (
            dict(understanding.get("traceability") or {})
            if isinstance(understanding, Mapping)
            else {}
        )

        packet = {
            "schema_version": self.SCHEMA_VERSION,
            "packet_type": self.PACKET_TYPE,
            "contract_version": self.VERSION,
            "packet_id": self._packet_id(
                customer_fact_id=str(customer_fact["fact_id"]),
                match_id=str(understanding_match["match_id"]),
                answer_readiness=answer_readiness,
            ),
            "concept_id": customer_fact["concept_id"],
            "fact_scope": "customer_specific",
            "answer_readiness": answer_readiness,
            "readiness_reason": readiness_reason,
            "customer_fact_ref": {
                "fact_id": customer_fact["fact_id"],
                "field_key": customer_fact["field_key"],
                "status": customer_fact["status"],
                "normalized_value": (
                    dict(customer_fact["normalized_value"])
                    if isinstance(customer_fact.get("normalized_value"), Mapping)
                    else None
                ),
                "source_document_id": customer_fact["source"]["source_document_id"],
                "source_sha256": customer_fact["source"]["sha256"],
                "document_type": customer_fact["source"]["document_type"],
            },
            "customer_evidence": [
                dict(item) for item in customer_fact.get("evidence_items", [])
            ],
            "understanding_match_ref": {
                "match_id": understanding_match["match_id"],
                "status": understanding_match["status"],
            },
            "generic_understanding_ref": (
                {
                    "understanding_asset_id": understanding.get("asset_id"),
                    "understanding_asset_status": understanding.get("status"),
                    "meaning_asset_id": traceability.get("meaning_asset_id"),
                    "learning_primitive_collection_id": traceability.get(
                        "learning_primitive_collection_id"
                    ),
                    "learning_path_collection_id": traceability.get(
                        "learning_path_collection_id"
                    ),
                    "source_evidence_refs": list(
                        traceability.get("source_evidence_refs") or []
                    ),
                }
                if isinstance(understanding, Mapping)
                else None
            ),
            "scope_boundaries": {
                "generic_knowledge_scope": "generic_insurance_concept",
                "customer_fact_scope": "specific_customer_document",
                "product_fact_scope": "not_established_by_this_packet",
                "claim_entitlement_scope": "not_evaluated",
                "recommendation_scope": "not_created",
            },
            "unresolved_states": self._unresolved_states(
                customer_fact=customer_fact,
                understanding_match=understanding_match,
            ),
            "publication_state": "not_published",
            "customer_answer_state": "not_created",
            "entitlement_state": "not_evaluated",
            "recommendation_state": "not_created",
            "guardrails": [
                "interpretation_packet_not_customer_answer",
                "interpretation_packet_not_entitlement_decision",
                "interpretation_packet_not_recommendation",
                "generic_product_and_customer_scopes_remain_separate",
            ],
        }
        self.validate(packet)
        return packet

    @classmethod
    def validate(cls, packet: Mapping[str, Any]) -> None:
        if not isinstance(packet, Mapping):
            raise InterpretationPacketError("interpretation packet must be an object")
        if packet.get("schema_version") != cls.SCHEMA_VERSION:
            raise InterpretationPacketError("schema_version must be 1.0")
        if packet.get("packet_type") != cls.PACKET_TYPE:
            raise InterpretationPacketError("unsupported packet_type")
        if packet.get("contract_version") != cls.VERSION:
            raise InterpretationPacketError("unsupported contract_version")
        cls._require_prefixed(packet.get("packet_id"), "ipacket_", "packet_id")
        if packet.get("concept_id") != "deductible":
            raise InterpretationPacketError("concept_id must be deductible")
        if packet.get("fact_scope") != "customer_specific":
            raise InterpretationPacketError("fact_scope must be customer_specific")
        if packet.get("answer_readiness") not in cls.ALLOWED_READINESS:
            raise InterpretationPacketError("unsupported answer_readiness")
        cls._require_nonempty(packet.get("readiness_reason"), "readiness_reason")

        fact_ref = packet.get("customer_fact_ref")
        if not isinstance(fact_ref, Mapping):
            raise InterpretationPacketError("customer_fact_ref must be an object")
        cls._require_prefixed(fact_ref.get("fact_id"), "cdfact_", "customer_fact_ref.fact_id")
        if fact_ref.get("field_key") != "customer_selected_deductible":
            raise InterpretationPacketError("unexpected customer fact field_key")
        cls._require_sha(fact_ref.get("source_sha256"), "customer_fact_ref.source_sha256")
        cls._require_nonempty(
            fact_ref.get("source_document_id"),
            "customer_fact_ref.source_document_id",
        )
        cls._require_nonempty(fact_ref.get("document_type"), "customer_fact_ref.document_type")

        evidence = packet.get("customer_evidence")
        if not isinstance(evidence, list):
            raise InterpretationPacketError("customer_evidence must be a list")

        match_ref = packet.get("understanding_match_ref")
        if not isinstance(match_ref, Mapping):
            raise InterpretationPacketError("understanding_match_ref must be an object")
        cls._require_prefixed(match_ref.get("match_id"), "cumatch_", "understanding_match_ref.match_id")

        generic = packet.get("generic_understanding_ref")
        readiness = packet["answer_readiness"]
        if readiness == cls.READY:
            if fact_ref.get("status") != "extracted":
                raise InterpretationPacketError("ready packet requires extracted customer fact")
            normalized = fact_ref.get("normalized_value")
            cls._validate_currency(normalized)
            if match_ref.get("status") != "matched":
                raise InterpretationPacketError("ready packet requires matched understanding")
            if not isinstance(generic, Mapping):
                raise InterpretationPacketError("ready packet requires generic_understanding_ref")
            cls._require_prefixed(
                generic.get("understanding_asset_id"),
                "ua_",
                "generic_understanding_ref.understanding_asset_id",
            )
            for key, prefix in (
                ("meaning_asset_id", "meaning_"),
                ("learning_primitive_collection_id", "lpc_"),
                ("learning_path_collection_id", "lpathc_"),
            ):
                cls._require_prefixed(generic.get(key), prefix, f"generic_understanding_ref.{key}")
            refs = generic.get("source_evidence_refs")
            if not isinstance(refs, list) or not refs:
                raise InterpretationPacketError(
                    "ready packet requires generic source_evidence_refs"
                )

        boundaries = packet.get("scope_boundaries")
        if not isinstance(boundaries, Mapping):
            raise InterpretationPacketError("scope_boundaries must be an object")
        expected_boundaries = {
            "generic_knowledge_scope": "generic_insurance_concept",
            "customer_fact_scope": "specific_customer_document",
            "product_fact_scope": "not_established_by_this_packet",
            "claim_entitlement_scope": "not_evaluated",
            "recommendation_scope": "not_created",
        }
        for key, expected in expected_boundaries.items():
            if boundaries.get(key) != expected:
                raise InterpretationPacketError(f"scope_boundaries.{key} must be {expected}")

        unresolved = packet.get("unresolved_states")
        if not isinstance(unresolved, list):
            raise InterpretationPacketError("unresolved_states must be a list")

        required_states = {
            "publication_state": "not_published",
            "customer_answer_state": "not_created",
            "entitlement_state": "not_evaluated",
            "recommendation_state": "not_created",
        }
        for key, expected in required_states.items():
            if packet.get(key) != expected:
                raise InterpretationPacketError(f"{key} must be {expected}")

    @staticmethod
    def _validate_cross_binding(
        customer_fact: Mapping[str, Any],
        match: Mapping[str, Any],
    ) -> None:
        snapshot = match.get("customer_fact")
        if not isinstance(snapshot, Mapping):
            raise InterpretationPacketError("match.customer_fact must be an object")
        checks = {
            "fact_id": customer_fact.get("fact_id"),
            "fact_scope": customer_fact.get("fact_scope"),
            "field_key": customer_fact.get("field_key"),
            "status": customer_fact.get("status"),
            "source_sha256": customer_fact.get("source", {}).get("sha256"),
        }
        for key, expected in checks.items():
            if snapshot.get(key) != expected:
                raise InterpretationPacketError(
                    f"match customer fact snapshot mismatch for {key}"
                )
        if snapshot.get("normalized_value") != customer_fact.get("normalized_value"):
            raise InterpretationPacketError(
                "match customer fact normalized_value mismatch"
            )
        if match.get("concept_id") != customer_fact.get("concept_id"):
            raise InterpretationPacketError("match concept_id mismatch")

    @staticmethod
    def _validate_customer_fact(fact: Mapping[str, Any]) -> None:
        if not isinstance(fact, Mapping):
            raise InterpretationPacketError("customer_fact must be an object")
        if fact.get("record_type") != "health_customer_document_fact_v1":
            raise InterpretationPacketError("unsupported customer fact record_type")
        if fact.get("concept_id") != "deductible":
            raise InterpretationPacketError("customer fact concept_id must be deductible")
        if fact.get("fact_scope") != "customer_specific":
            raise InterpretationPacketError("customer fact must be customer_specific")
        InterpretationPacketAssembler._require_prefixed(
            fact.get("fact_id"), "cdfact_", "customer fact_id"
        )
        source = fact.get("source")
        if not isinstance(source, Mapping):
            raise InterpretationPacketError("customer fact source must be an object")
        InterpretationPacketAssembler._require_sha(
            source.get("sha256"), "customer fact source.sha256"
        )

    @staticmethod
    def _validate_match(match: Mapping[str, Any]) -> None:
        if not isinstance(match, Mapping):
            raise InterpretationPacketError("understanding_match must be an object")
        if match.get("record_type") != "health_customer_fact_understanding_match_v1":
            raise InterpretationPacketError("unsupported understanding match record_type")
        InterpretationPacketAssembler._require_prefixed(
            match.get("match_id"), "cumatch_", "match_id"
        )

    @staticmethod
    def _unresolved_states(
        *,
        customer_fact: Mapping[str, Any],
        understanding_match: Mapping[str, Any],
    ) -> list[str]:
        unresolved: list[str] = []
        if customer_fact.get("status") != "extracted":
            unresolved.append(f"customer_fact_status:{customer_fact.get('status')}")
        if understanding_match.get("status") != "matched":
            unresolved.append(
                f"understanding_match_status:{understanding_match.get('status')}"
            )
        unresolved.extend(
            [
                "product_specific_deductible_mechanics_not_established",
                "claim_admissibility_not_evaluated",
                "customer_answer_not_created",
                "recommendation_not_created",
            ]
        )
        return unresolved

    @staticmethod
    def _packet_id(
        *,
        customer_fact_id: str,
        match_id: str,
        answer_readiness: str,
    ) -> str:
        material = {
            "customer_fact_id": customer_fact_id,
            "match_id": match_id,
            "answer_readiness": answer_readiness,
        }
        digest = hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:20]
        return f"ipacket_{digest}"

    @staticmethod
    def _validate_currency(value: Any) -> None:
        if not isinstance(value, Mapping):
            raise InterpretationPacketError("normalized_value must be an object")
        if value.get("kind") != "currency" or value.get("unit") != "INR":
            raise InterpretationPacketError("normalized_value must be INR currency")
        amount = value.get("value")
        if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
            raise InterpretationPacketError("normalized_value must be positive integer INR")

    @staticmethod
    def _require_sha(value: Any, name: str) -> None:
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(ch not in "0123456789abcdef" for ch in value)
        ):
            raise InterpretationPacketError(f"{name} must be lowercase SHA-256")

    @staticmethod
    def _require_nonempty(value: Any, name: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise InterpretationPacketError(f"{name} must be non-empty")

    @classmethod
    def _require_prefixed(cls, value: Any, prefix: str, name: str) -> None:
        cls._require_nonempty(value, name)
        if not value.startswith(prefix):
            raise InterpretationPacketError(f"{name} must start with {prefix}")
