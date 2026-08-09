"""Safe product-entity-to-planner handoff for ER-4.

The handoff publishes only a governed product execution scope. It performs no
evidence retrieval, document selection, terminology resolution, reasoning,
comparison, ranking, or recommendation. Only a uniquely RESOLVED entity may
become READY for downstream planning.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from insurance_intelligence.entity_resolution.product_resolver import (
    ProductEntityResolution,
)

ENTITY_HANDOFF_STATUSES = frozenset({"READY", "BLOCKED", "INVALID_INPUT"})


@dataclass(frozen=True)
class ProductEntityPlannerHandoff:
    handoff_id: str
    resolution_id: str
    status: str
    canonical_entity_id: str | None
    insurer_id: str | None
    product_id: str | None
    uin: str | None
    candidate_entity_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status not in ENTITY_HANDOFF_STATUSES:
            raise ValueError(f"unsupported entity handoff status: {self.status!r}")
        if not self.reason_codes:
            raise ValueError("reason_codes must not be empty")
        if self.status == "READY":
            if not self.canonical_entity_id or not self.insurer_id or not self.product_id:
                raise ValueError(
                    "READY entity handoff requires canonical entity, insurer, and product ids"
                )
            if self.candidate_entity_ids != (self.canonical_entity_id,):
                raise ValueError(
                    "READY entity handoff must preserve exactly the selected entity"
                )
        else:
            if any(
                value is not None
                for value in (
                    self.canonical_entity_id,
                    self.insurer_id,
                    self.product_id,
                    self.uin,
                )
            ):
                raise ValueError(
                    f"{self.status} entity handoff cannot publish an execution scope"
                )

    @property
    def can_execute(self) -> bool:
        return self.status == "READY"

    @property
    def requires_clarification(self) -> bool:
        return self.status == "BLOCKED" and len(self.candidate_entity_ids) > 1


def _stable_id(*parts: object) -> str:
    payload = "\x1f".join("" if part is None else str(part) for part in parts)
    return f"entity_handoff_{sha256(payload.encode('utf-8')).hexdigest()[:24]}"


def build_entity_planner_handoff(resolution: object) -> ProductEntityPlannerHandoff:
    """Convert governed entity resolution into a safe planner execution scope."""
    if not isinstance(resolution, ProductEntityResolution):
        return ProductEntityPlannerHandoff(
            handoff_id=_stable_id("INVALID_INPUT", repr(resolution)),
            resolution_id="invalid-resolution",
            status="INVALID_INPUT",
            canonical_entity_id=None,
            insurer_id=None,
            product_id=None,
            uin=None,
            candidate_entity_ids=(),
            reason_codes=("INVALID_ENTITY_RESOLUTION",),
        )

    candidate_ids = tuple(
        item.canonical_entity_id for item in resolution.candidates
    )

    if resolution.status != "RESOLVED":
        reason = {
            "AMBIGUOUS": "ENTITY_REFERENCE_AMBIGUOUS",
            "NOT_RESOLVED": "UNRESOLVED_ENTITY_REFERENCE",
            "INVALID_INPUT": "INVALID_ENTITY_REFERENCE",
        }.get(resolution.status, "ENTITY_REFERENCE_NOT_READY")
        return ProductEntityPlannerHandoff(
            handoff_id=_stable_id(
                "BLOCKED", resolution.resolution_id, reason, *candidate_ids
            ),
            resolution_id=resolution.resolution_id,
            status="BLOCKED",
            canonical_entity_id=None,
            insurer_id=None,
            product_id=None,
            uin=None,
            candidate_entity_ids=candidate_ids,
            reason_codes=(reason,),
        )

    selected = resolution.selected_entity
    if selected is None:
        return ProductEntityPlannerHandoff(
            handoff_id=_stable_id(
                "BLOCKED", resolution.resolution_id, "MISSING_SELECTED_ENTITY"
            ),
            resolution_id=resolution.resolution_id,
            status="BLOCKED",
            canonical_entity_id=None,
            insurer_id=None,
            product_id=None,
            uin=None,
            candidate_entity_ids=(),
            reason_codes=("MISSING_SELECTED_ENTITY",),
        )

    return ProductEntityPlannerHandoff(
        handoff_id=_stable_id(
            "READY",
            resolution.resolution_id,
            selected.canonical_entity_id,
            selected.insurer_id,
            selected.product_id,
            selected.uin,
        ),
        resolution_id=resolution.resolution_id,
        status="READY",
        canonical_entity_id=selected.canonical_entity_id,
        insurer_id=selected.insurer_id,
        product_id=selected.product_id,
        uin=selected.uin,
        candidate_entity_ids=(selected.canonical_entity_id,),
        reason_codes=("GOVERNED_PRODUCT_ENTITY_READY_FOR_PLANNING",),
    )
