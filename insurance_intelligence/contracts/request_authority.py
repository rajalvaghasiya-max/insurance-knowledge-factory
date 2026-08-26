"""Executable contract for the Assertion / Advisory request boundary."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

SUPPORTED_CONTRACT_VERSION = "1.0"
AUTHORITY_CLASSES = frozenset({"ASSERTIVE", "ADVISORY", "MIXED", "UNRESOLVED"})
DOWNSTREAM_GUARDS = frozenset(
    {
        "STANDARD_ASSERTION_GROUNDING",
        "ADVISORY_CONTEXT_AND_SAFETY_REQUIRED",
        "SPLIT_ASSERTIVE_AND_ADVISORY_WITH_ADVISORY_SAFETY_REQUIRED",
        "CLARIFY_REQUESTED_AUTHORITY",
    }
)


class RequestAuthorityError(ValueError):
    """Raised when the request-authority contract is invalid."""


def _require_nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RequestAuthorityError(f"{label} must be a non-empty string")
    return value


@dataclass(frozen=True)
class RequestAuthorityInput:
    contract_version: str
    request_id: str
    text: str


@dataclass(frozen=True)
class RequestAuthorityOutput:
    contract_version: str
    request_id: str
    authority_class: str
    matched_assertive_cues: tuple[str, ...]
    matched_advisory_cues: tuple[str, ...]
    classification_basis: str
    downstream_guard: str
    intent_analysis_authorized: bool
    recommendation_authorized: bool


def build_input(
    *, request_id: str, text: str, contract_version: str = SUPPORTED_CONTRACT_VERSION
) -> RequestAuthorityInput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise RequestAuthorityError(
            f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}"
        )
    return RequestAuthorityInput(
        contract_version=contract_version,
        request_id=_require_nonempty(request_id, "request_id"),
        text=_require_nonempty(text, "text"),
    )


def build_output(
    *,
    request_id: str,
    authority_class: str,
    matched_assertive_cues: Sequence[str] = (),
    matched_advisory_cues: Sequence[str] = (),
    classification_basis: str,
    downstream_guard: str,
    intent_analysis_authorized: bool,
    recommendation_authorized: bool = False,
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> RequestAuthorityOutput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise RequestAuthorityError(
            f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}"
        )
    if authority_class not in AUTHORITY_CLASSES:
        raise RequestAuthorityError("unsupported authority_class")
    if downstream_guard not in DOWNSTREAM_GUARDS:
        raise RequestAuthorityError("unsupported downstream_guard")
    if not isinstance(intent_analysis_authorized, bool):
        raise RequestAuthorityError("intent_analysis_authorized must be boolean")
    if recommendation_authorized is not False:
        raise RequestAuthorityError(
            "request-authority boundary may never authorize a recommendation"
        )
    assertive = tuple(_require_nonempty(cue, "matched_assertive_cues[]") for cue in matched_assertive_cues)
    advisory = tuple(_require_nonempty(cue, "matched_advisory_cues[]") for cue in matched_advisory_cues)
    basis = _require_nonempty(classification_basis, "classification_basis")

    expected_guard = {
        "ASSERTIVE": "STANDARD_ASSERTION_GROUNDING",
        "ADVISORY": "ADVISORY_CONTEXT_AND_SAFETY_REQUIRED",
        "MIXED": "SPLIT_ASSERTIVE_AND_ADVISORY_WITH_ADVISORY_SAFETY_REQUIRED",
        "UNRESOLVED": "CLARIFY_REQUESTED_AUTHORITY",
    }[authority_class]
    if downstream_guard != expected_guard:
        raise RequestAuthorityError(
            f"downstream_guard must be {expected_guard} for {authority_class}"
        )
    if authority_class == "UNRESOLVED" and intent_analysis_authorized:
        raise RequestAuthorityError("UNRESOLVED must withhold intent analysis")
    if authority_class != "UNRESOLVED" and not intent_analysis_authorized:
        raise RequestAuthorityError(
            "resolved authority classes must authorize intent analysis"
        )
    if authority_class == "ASSERTIVE" and advisory:
        raise RequestAuthorityError("ASSERTIVE output cannot contain advisory cues")
    if authority_class == "ADVISORY" and assertive:
        raise RequestAuthorityError("ADVISORY output cannot contain assertive cues")
    if authority_class == "MIXED" and (not assertive or not advisory):
        raise RequestAuthorityError("MIXED requires both cue families")
    if authority_class == "UNRESOLVED" and (assertive or advisory):
        raise RequestAuthorityError("UNRESOLVED cannot contain matched cues")

    return RequestAuthorityOutput(
        contract_version=contract_version,
        request_id=_require_nonempty(request_id, "request_id"),
        authority_class=authority_class,
        matched_assertive_cues=assertive,
        matched_advisory_cues=advisory,
        classification_basis=basis,
        downstream_guard=downstream_guard,
        intent_analysis_authorized=intent_analysis_authorized,
        recommendation_authorized=False,
    )
