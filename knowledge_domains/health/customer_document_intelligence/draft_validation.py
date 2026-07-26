"""Deterministic validation gate for constrained LLM drafts."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping


class DraftValidationError(ValueError):
    """Raised when validation inputs or outputs violate the contract."""


class DraftValidationEngine:
    VERSION = "1.0"
    RECORD_TYPE = "health_llm_draft_validation_result_v1"

    APPROVED = "approved"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review_required"

    _GUARANTEE = (
        re.compile(r"\bwill definitely pay\b", re.I),
        re.compile(r"\bguaranteed(?:ly)?\s+(?:pay|payment|covered|coverage)\b", re.I),
        re.compile(r"\binsurer will pay\b", re.I),
    )
    _RECOMMENDATION = (
        re.compile(r"\byou should (?:buy|switch|retain|cancel|choose)\b", re.I),
        re.compile(r"\bthis (?:policy|plan) is (?:good|bad|best|better|suitable)\b", re.I),
    )
    _UNSUPPORTED_FREQUENCY = (
        re.compile(r"\bapplies per claim\b", re.I),
        re.compile(r"\bapplies annually\b", re.I),
        re.compile(r"\bannual deductible\b", re.I),
        re.compile(r"\bper-claim deductible\b", re.I),
    )
    _NEGATION_OR_UNCERTAINTY = (
        "does not establish",
        "doesn't establish",
        "not established",
        "does not determine",
        "doesn't determine",
        "not determined",
        "does not confirm",
        "doesn't confirm",
        "not confirmed",
        "not known",
        "unknown",
        "unclear",
        "whether",
    )

    def validate_draft(
        self,
        *,
        bundle: Mapping[str, Any],
        request: Mapping[str, Any],
        draft: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._validate_inputs(bundle, request, draft)
        self._cross_bind(bundle, request, draft)

        text = draft["draft_text"].strip()
        findings: list[dict[str, Any]] = []

        if draft["word_count"] > draft["maximum_words"]:
            findings.append(self._finding("word_limit_exceeded", "error"))

        amount = self._expected_amount(bundle)
        if amount is not None and not self._amount_present(text, amount):
            findings.append(self._finding("customer_value_missing_or_changed", "error"))

        missing = [
            caveat for caveat in bundle.get("required_caveats", [])
            if not self._caveat_present(text, str(caveat))
        ]
        if missing:
            findings.append({
                **self._finding("required_caveat_missing", "error"),
                "details": {"missing_caveats": missing},
            })

        if any(pattern.search(text) for pattern in self._GUARANTEE):
            findings.append(self._finding("guaranteed_payment_claim", "error"))

        if any(pattern.search(text) for pattern in self._RECOMMENDATION):
            findings.append(self._finding("recommendation_language_present", "error"))

        if self._unsupported_frequency_asserted(text):
            findings.append(
                self._finding("unsupported_frequency_or_applicability_claim", "error")
            )

        if self._contains_example(text):
            allowed = bundle.get("example_policy", {}).get(
                "runtime_generation_allowed"
            ) is True
            if not allowed:
                findings.append(self._finding("runtime_example_not_allowed", "error"))
            elif not self._example_labelled(text):
                findings.append(
                    self._finding("runtime_example_not_labelled", "manual_review")
                )

        if any(item["severity"] == "error" for item in findings):
            state = self.REJECTED
            answer_state = "rejected_not_deliverable"
        elif findings:
            state = self.MANUAL_REVIEW
            answer_state = "manual_review_required"
        else:
            state = self.APPROVED
            answer_state = "approved_for_delivery"

        result = {
            "schema_version": "1.0",
            "record_type": self.RECORD_TYPE,
            "contract_version": self.VERSION,
            "validation_id": self._id(
                bundle["bundle_id"],
                request["request_id"],
                draft["draft_id"],
                state,
                [item["code"] for item in findings],
            ),
            "bundle_id": bundle["bundle_id"],
            "request_id": request["request_id"],
            "draft_id": draft["draft_id"],
            "packet_id": draft["packet_id"],
            "route_decision_id": draft["route_decision_id"],
            "concept_id": draft["concept_id"],
            "validation_state": state,
            "finding_count": len(findings),
            "findings": findings,
            "validated_draft_text": text if state == self.APPROVED else None,
            "customer_answer_state": answer_state,
            "publication_state": "not_published",
            "entitlement_state": "not_evaluated",
            "recommendation_state": "not_created",
        }
        self.validate_result(result)
        return result

    @classmethod
    def validate_result(cls, result: Mapping[str, Any]) -> None:
        if result.get("record_type") != cls.RECORD_TYPE:
            raise DraftValidationError("unsupported validation result")
        cls._prefix(result.get("validation_id"), "vcheck_", "validation_id")
        if result.get("validation_state") not in {
            cls.APPROVED, cls.REJECTED, cls.MANUAL_REVIEW
        }:
            raise DraftValidationError("unsupported validation_state")
        findings = result.get("findings")
        if not isinstance(findings, list) or result.get("finding_count") != len(findings):
            raise DraftValidationError("invalid findings")
        if result["validation_state"] == cls.APPROVED:
            if not result.get("validated_draft_text"):
                raise DraftValidationError("approved result requires validated text")
            if result.get("customer_answer_state") != "approved_for_delivery":
                raise DraftValidationError("invalid approved answer state")
        elif result.get("validated_draft_text") is not None:
            raise DraftValidationError("non-approved result cannot expose validated text")
        for key, expected in {
            "publication_state": "not_published",
            "entitlement_state": "not_evaluated",
            "recommendation_state": "not_created",
        }.items():
            if result.get(key) != expected:
                raise DraftValidationError(f"{key} must be {expected}")

    @classmethod
    def _validate_inputs(cls, bundle, request, draft):
        if bundle.get("record_type") != "health_approved_answer_content_bundle_v1":
            raise DraftValidationError("unsupported bundle")
        if request.get("record_type") != "health_llm_verbalizer_request_v1":
            raise DraftValidationError("unsupported request")
        if draft.get("record_type") != "health_llm_verbalized_draft_v1":
            raise DraftValidationError("unsupported draft")
        if draft.get("validation_state") != "not_validated":
            raise DraftValidationError("draft must be not_validated")
        if draft.get("customer_answer_state") != "draft_not_approved":
            raise DraftValidationError("draft must be unapproved")
        if not isinstance(draft.get("draft_text"), str) or not draft["draft_text"].strip():
            raise DraftValidationError("draft_text must be non-empty")

    @staticmethod
    def _cross_bind(bundle, request, draft):
        checks = {
            "bundle_id": (bundle.get("bundle_id"), request.get("bundle_id"), draft.get("bundle_id")),
            "packet_id": (bundle.get("packet_id"), request.get("packet_id"), draft.get("packet_id")),
            "route_decision_id": (
                bundle.get("route_decision_id"),
                request.get("route_decision_id"),
                draft.get("route_decision_id"),
            ),
            "concept_id": (bundle.get("concept_id"), request.get("concept_id"), draft.get("concept_id")),
            "route": (bundle.get("route"), request.get("route"), draft.get("route")),
        }
        for label, values in checks.items():
            if len(set(values)) != 1:
                raise DraftValidationError(f"cross-binding mismatch for {label}")
        if request.get("request_id") != draft.get("request_id"):
            raise DraftValidationError("cross-binding mismatch for request_id")

    @staticmethod
    def _expected_amount(bundle):
        for item in bundle.get("allowed_facts", []):
            value = item.get("structured_value")
            if (
                item.get("scope") == "customer_specific"
                and isinstance(value, Mapping)
                and value.get("kind") == "currency"
                and value.get("unit") == "INR"
                and isinstance(value.get("value"), int)
            ):
                return value["value"]
        return None

    @staticmethod
    def _amount_present(text: str, amount: int) -> bool:
        compact = re.sub(r"[,\s₹]|INR|Rs\.?", "", text, flags=re.I)
        return str(amount) in compact

    @staticmethod
    def _caveat_present(text: str, caveat: str) -> bool:
        lowered = text.casefold()
        c = caveat.casefold()
        if "frequency" in c or "applicability" in c:
            return (
                "does not establish" in lowered
                and any(x in lowered for x in ("per claim", "annually", "specific benefit", "frequency", "applicability"))
            )
        if "claim admissibility" in c or "final insurer payment" in c:
            return (
                "admissibility" in lowered
                and any(x in lowered for x in ("final amount payable", "final insurer payment", "final payment"))
                and any(x in lowered for x in ("does not determine", "not determined", "does not establish"))
            )
        if "taken from the supplied customer document" in c:
            return any(x in lowered for x in ("policy schedule shows", "supplied policy schedule", "supplied customer document"))
        tokens = [x for x in re.findall(r"[a-z0-9]+", c) if len(x) >= 5]
        return not tokens or sum(x in lowered for x in tokens) / len(tokens) >= 0.6

    @classmethod
    def _unsupported_frequency_asserted(cls, text: str) -> bool:
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", text)
            if sentence.strip()
        ]
        for sentence in sentences:
            if not any(pattern.search(sentence) for pattern in cls._UNSUPPORTED_FREQUENCY):
                continue
            lowered = sentence.casefold()
            if any(marker in lowered for marker in cls._NEGATION_OR_UNCERTAINTY):
                continue
            return True
        return False

    @staticmethod
    def _contains_example(text: str) -> bool:
        lower = text.casefold()
        return any(x in lower for x in ("for example", "for illustration", "illustration:", "suppose", "hypothetical"))

    @staticmethod
    def _example_labelled(text: str) -> bool:
        lower = text.casefold()
        return any(x in lower for x in ("for illustration", "illustration:", "hypothetical example", "illustrative example"))

    @staticmethod
    def _finding(code: str, severity: str) -> dict[str, str]:
        return {"code": code, "severity": severity}

    @staticmethod
    def _id(bundle_id, request_id, draft_id, state, codes):
        material = {
            "bundle_id": bundle_id,
            "request_id": request_id,
            "draft_id": draft_id,
            "validation_state": state,
            "finding_codes": sorted(codes),
        }
        digest = hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:20]
        return f"vcheck_{digest}"

    @staticmethod
    def _prefix(value, prefix, name):
        if not isinstance(value, str) or not value.startswith(prefix):
            raise DraftValidationError(f"{name} must start with {prefix}")
