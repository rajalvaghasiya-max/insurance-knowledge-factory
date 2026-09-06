"""Generic real-capability prefix for canonical intelligence-response orchestration.

This module composes existing governed request, identity, planning, and evidence
capabilities without changing their semantic algorithms.  It intentionally stops at
publication-backed evidence resolution; reasoning and answer generation remain separate
Issue #242 slices so a prefix failure cannot be hidden by downstream presentation code.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable, Sequence

from insurance_intelligence.authority_intent_reconciliation import reconcile_authority_and_intent
from insurance_intelligence.context.builder import ContextBuilder
from insurance_intelligence.context.requirements import requirements_for_intent
from insurance_intelligence.contracts.authority_intent_reconciliation import (
    AuthorityIntentReconciliationOutput,
    build_input as build_reconciliation_input,
)
from insurance_intelligence.contracts.context import (
    ContextBuilderOutput,
    build_input as build_context_input,
    build_resolved_context_item,
)
from insurance_intelligence.contracts.evidence import (
    EvidenceResolverOutput,
    build_input as build_evidence_input,
)
from insurance_intelligence.contracts.evidence_instance_enforcement import (
    EvidenceInstanceEnforcementOutput,
    build_input as build_evidence_enforcement_input,
)
from insurance_intelligence.contracts.full_cycle import OrchestrationRequest, ProductScope
from insurance_intelligence.contracts.instance_sufficiency import (
    InstanceSufficiencyOutput,
    build_input as build_instance_input,
)
from insurance_intelligence.contracts.intent import (
    IntentAnalyzerOutput,
    build_input as build_intent_input,
)
from insurance_intelligence.contracts.reasoning_plan import (
    ReasoningPlan,
    build_input as build_plan_input,
)
from insurance_intelligence.contracts.request_authority import (
    RequestAuthorityOutput,
    build_input as build_authority_input,
)
from insurance_intelligence.entity_resolution.product_resolver import GovernedProductEntityRegistry
from insurance_intelligence.evidence.admission import USER_ANSWER
from insurance_intelligence.evidence.published_resolver import PublishedEvidenceResolver
from insurance_intelligence.evidence_instance_enforcement import EvidenceInstanceEnforcer
from insurance_intelligence.intent.analyzer import IntentAnalyzer
from insurance_intelligence.instance_sufficiency import InstanceSufficiencyGuard
from insurance_intelligence.orchestration.execution_state import RuntimeStageObjectStore
from insurance_intelligence.orchestration.intelligence_adapters import (
    IntelligenceStageAdapter,
    build_intelligence_stage_adapter,
    build_raw_intelligence_stage_output,
)
from insurance_intelligence.orchestration.product_instance_binding import (
    IdentityRecordLookup,
    ProductInstanceBinding,
    bind_product_scope_to_context,
)
from insurance_intelligence.planning.planner import ReasoningPlanner
from insurance_intelligence.request_authority import classify_request_authority


class RealResponsePrefixError(ValueError):
    """Raised when the real canonical response prefix cannot proceed safely."""


@dataclass(frozen=True)
class CertifiedKnowledgeSelection:
    snapshot_id: str
    canonical_entity_id: str
    selection_record_ref: str

    def __post_init__(self) -> None:
        for label, value in (
            ("snapshot_id", self.snapshot_id),
            ("canonical_entity_id", self.canonical_entity_id),
            ("selection_record_ref", self.selection_record_ref),
        ):
            if not isinstance(value, str) or not value.strip():
                raise RealResponsePrefixError(f"{label} must be non-empty text")


KnowledgeSnapshotLookup = Callable[[str, ProductScope], CertifiedKnowledgeSelection | None]


@dataclass(frozen=True)
class RealResponsePrefixDependencies:
    store: RuntimeStageObjectStore
    product_registry: GovernedProductEntityRegistry
    identity_record_lookup: IdentityRecordLookup
    knowledge_snapshot_lookup: KnowledgeSnapshotLookup
    published_evidence_resolver: PublishedEvidenceResolver
    repository_roots: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.store, RuntimeStageObjectStore):
            raise RealResponsePrefixError("store must be RuntimeStageObjectStore")
        if not isinstance(self.product_registry, GovernedProductEntityRegistry):
            raise RealResponsePrefixError("product_registry must be GovernedProductEntityRegistry")
        if not callable(self.identity_record_lookup):
            raise RealResponsePrefixError("identity_record_lookup must be callable")
        if not callable(self.knowledge_snapshot_lookup):
            raise RealResponsePrefixError("knowledge_snapshot_lookup must be callable")
        if not isinstance(self.published_evidence_resolver, PublishedEvidenceResolver):
            raise RealResponsePrefixError("published_evidence_resolver must be PublishedEvidenceResolver")
        if not self.repository_roots or any(not isinstance(item, str) or not item.strip() for item in self.repository_roots):
            raise RealResponsePrefixError("repository_roots must contain non-empty paths")


def _canonical_entity_id(scope: ProductScope) -> str:
    return f"{scope.insurer_id}:{scope.product_id}"


def _output_id(request: OrchestrationRequest, stage: str) -> str:
    return f"{request.execution_id}:real:{stage.lower()}"


def _support_id(request: OrchestrationRequest, name: str) -> str:
    return f"{request.execution_id}:runtime:{name}"


def _store_raw(
    *, request: OrchestrationRequest, stage: str, snapshot: str, value: object,
    store: RuntimeStageObjectStore, output_type: str, limitations: Sequence[str] = (),
    evidence_ids: Sequence[str] = (),
):
    output_id = _output_id(request, stage)
    store.put(output_id=output_id, value=value)
    payload = asdict(value) if hasattr(value, "__dataclass_fields__") else {"value_type": type(value).__name__}
    return build_raw_intelligence_stage_output(
        execution_id=request.execution_id,
        stage=stage,
        knowledge_snapshot_id=snapshot,
        output_id=output_id,
        output_type=output_type,
        payload=payload,
        limitations=limitations,
        evidence_ids=evidence_ids,
    )


def _scope_session_context(request: OrchestrationRequest, intent: IntentAnalyzerOutput):
    canonical = _canonical_entity_id(request.product_scope)
    items = []
    for requirement in requirements_for_intent(intent.primary_intent):
        product_compatible = requirement.category == "PRODUCT" or requirement.context_key == "policy_or_product_reference"
        if not product_compatible:
            continue
        items.append(
            build_resolved_context_item(
                key=requirement.context_key,
                value=canonical,
                category="PRODUCT" if requirement.category == "PRODUCT" else "POLICY",
                provenance="SYSTEM_DERIVED",
                source_reference="orchestration.product_scope.candidate",
                confidence=1.0,
                materiality=requirement.materiality,
            )
        )
    return tuple(items)


def _user_context(request: OrchestrationRequest):
    items = []
    for sequence, (key, value) in enumerate(sorted(request.customer_context.items()), start=1):
        if value is None:
            continue
        items.append(
            {
                "key": str(key),
                "value": str(value),
                "source_reference": "request.customer_context",
                "sequence": sequence,
            }
        )
    return tuple(items)


def build_real_response_prefix_adapters(
    *, dependencies: RealResponsePrefixDependencies
) -> tuple[IntelligenceStageAdapter, ...]:
    """Build canonical real adapters from request intake through guarded evidence resolution."""
    deps = dependencies

    def request_intake(*, request, stage, input_ids, knowledge_snapshot_id):
        if stage != "REQUEST_INTAKE":
            raise RealResponsePrefixError("request intake stage mismatch")
        return _store_raw(
            request=request, stage=stage, snapshot=knowledge_snapshot_id, value=request,
            store=deps.store, output_type="orchestration_request",
        )

    def knowledge_retrieval(*, request, stage, input_ids, knowledge_snapshot_id):
        if stage != "CERTIFIED_KNOWLEDGE_RETRIEVAL":
            raise RealResponsePrefixError("knowledge retrieval stage mismatch")
        selection = deps.knowledge_snapshot_lookup(knowledge_snapshot_id, request.product_scope)
        if not isinstance(selection, CertifiedKnowledgeSelection):
            raise RealResponsePrefixError("certified knowledge snapshot was not admitted by governed lookup")
        if selection.snapshot_id != knowledge_snapshot_id:
            raise RealResponsePrefixError("knowledge snapshot lookup returned a different snapshot")
        if selection.canonical_entity_id != _canonical_entity_id(request.product_scope):
            raise RealResponsePrefixError("knowledge snapshot is not bound to the orchestration product scope")
        return _store_raw(
            request=request, stage=stage, snapshot=knowledge_snapshot_id, value=selection,
            store=deps.store, output_type="certified_knowledge_selection",
            evidence_ids=(selection.selection_record_ref,),
        )

    def authority(*, request, stage, input_ids, knowledge_snapshot_id):
        output = classify_request_authority(
            build_authority_input(request_id=request.execution_id, text=request.question or "")
        )
        return _store_raw(
            request=request, stage=stage, snapshot=knowledge_snapshot_id, value=output,
            store=deps.store, output_type="request_authority",
        )

    def intent(*, request, stage, input_ids, knowledge_snapshot_id):
        output = IntentAnalyzer().analyze(
            build_intent_input(
                request_id=request.execution_id,
                text=request.question or "",
                domain_hint=request.product_scope.domain.lower(),
            )
        )
        return _store_raw(
            request=request, stage=stage, snapshot=knowledge_snapshot_id, value=output,
            store=deps.store, output_type="intent_analysis",
        )

    def reconciliation(*, request, stage, input_ids, knowledge_snapshot_id):
        authority_output = deps.store.get(
            _output_id(request, "AUTHORITY_CLASSIFICATION"), expected_type=RequestAuthorityOutput
        )
        intent_output = deps.store.get(
            _output_id(request, "INTENT_ANALYSIS"), expected_type=IntentAnalyzerOutput
        )
        output = reconcile_authority_and_intent(
            build_reconciliation_input(
                request_id=request.execution_id,
                authority=authority_output,
                intent=intent_output,
            )
        )
        return _store_raw(
            request=request, stage=stage, snapshot=knowledge_snapshot_id, value=output,
            store=deps.store, output_type="authority_intent_reconciliation",
        )

    def context(*, request, stage, input_ids, knowledge_snapshot_id):
        intent_output = deps.store.get(
            _output_id(request, "INTENT_ANALYSIS"), expected_type=IntentAnalyzerOutput
        )
        output = ContextBuilder().build(
            build_context_input(
                request_id=request.execution_id,
                intent_analysis=intent_output,
                user_context=_user_context(request),
                session_context=_scope_session_context(request, intent_output),
            )
        )
        return _store_raw(
            request=request, stage=stage, snapshot=knowledge_snapshot_id, value=output,
            store=deps.store, output_type="context_assessment",
            limitations=tuple(item.key for item in output.missing_optional_context),
        )

    def instance(*, request, stage, input_ids, knowledge_snapshot_id):
        reconciliation_output = deps.store.get(
            _output_id(request, "AUTHORITY_INTENT_RECONCILIATION"),
            expected_type=AuthorityIntentReconciliationOutput,
        )
        context_output = deps.store.get(
            _output_id(request, "CONTEXT_BUILDING"), expected_type=ContextBuilderOutput
        )
        binding = bind_product_scope_to_context(
            product_scope=request.product_scope,
            reconciliation=reconciliation_output,
            context=context_output,
            registry=deps.product_registry,
            identity_record_lookup=deps.identity_record_lookup,
        )
        deps.store.put(output_id=_support_id(request, "product-instance-binding"), value=binding)
        output = InstanceSufficiencyGuard().evaluate(
            build_instance_input(
                request_id=request.execution_id,
                reconciliation=reconciliation_output,
                context=context_output,
                attestations=binding.attestations,
            )
        )
        if output.outcome != "PASS" or not output.planning_authorized:
            raise RealResponsePrefixError(
                f"instance sufficiency blocked real prefix: {output.outcome}; {output.basis}"
            )
        return _store_raw(
            request=request, stage=stage, snapshot=knowledge_snapshot_id, value=output,
            store=deps.store, output_type="instance_sufficiency",
        )

    def planning(*, request, stage, input_ids, knowledge_snapshot_id):
        intent_output = deps.store.get(
            _output_id(request, "INTENT_ANALYSIS"), expected_type=IntentAnalyzerOutput
        )
        context_output = deps.store.get(
            _output_id(request, "CONTEXT_BUILDING"), expected_type=ContextBuilderOutput
        )
        instance_output = deps.store.get(
            _output_id(request, "INSTANCE_SUFFICIENCY"), expected_type=InstanceSufficiencyOutput
        )
        if instance_output.outcome != "PASS" or not instance_output.planning_authorized:
            raise RealResponsePrefixError("planning cannot bypass Instance Sufficiency")
        output = ReasoningPlanner().plan(
            build_plan_input(
                request_id=request.execution_id,
                intent_analysis=intent_output,
                context_assessment=context_output,
            )
        )
        return _store_raw(
            request=request, stage=stage, snapshot=knowledge_snapshot_id, value=output,
            store=deps.store, output_type="reasoning_plan", limitations=output.limitations,
        )

    def evidence(*, request, stage, input_ids, knowledge_snapshot_id):
        plan = deps.store.get(
            _output_id(request, "REASONING_PLANNING"), expected_type=ReasoningPlan
        )
        instance_output = deps.store.get(
            _output_id(request, "INSTANCE_SUFFICIENCY"), expected_type=InstanceSufficiencyOutput
        )
        binding = deps.store.get(
            _support_id(request, "product-instance-binding"), expected_type=ProductInstanceBinding
        )
        evidence_input = build_evidence_input(
            request_id=request.execution_id,
            reasoning_plan=plan,
            repository_roots=deps.repository_roots,
            resolution_context={
                "knowledge_snapshot_id": knowledge_snapshot_id,
                "evidence_use": USER_ANSWER,
                "resolved_candidate_references": binding.resolved_candidate_references,
            },
            strict_mode="STRICT",
        )
        enforced = EvidenceInstanceEnforcer(resolver=deps.published_evidence_resolver).resolve(
            build_evidence_enforcement_input(
                request_id=request.execution_id,
                instance_sufficiency=instance_output,
                evidence_input=evidence_input,
            )
        )
        if (
            enforced.outcome != "EVIDENCE_RESOLUTION_AUTHORIZED"
            or not enforced.evidence_resolver_called
            or not isinstance(enforced.evidence_output, EvidenceResolverOutput)
        ):
            raise RealResponsePrefixError(f"guarded evidence resolution blocked: {enforced.basis}")
        if enforced.evidence_output.resolution_status not in {"RESOLVED", "RESOLVED_WITH_LIMITATIONS"}:
            raise RealResponsePrefixError(
                f"publication-backed evidence failed closed: {enforced.evidence_output.sufficiency}"
            )
        deps.store.put(output_id=_support_id(request, "evidence-enforcement"), value=enforced)
        output = enforced.evidence_output
        return _store_raw(
            request=request, stage=stage, snapshot=knowledge_snapshot_id, value=output,
            store=deps.store, output_type="publication_backed_evidence_resolution",
            evidence_ids=tuple(item.evidence_id for item in output.evidence_packages),
            limitations=output.limitations,
        )

    capabilities = (
        ("REQUEST_INTAKE", request_intake),
        ("CERTIFIED_KNOWLEDGE_RETRIEVAL", knowledge_retrieval),
        ("AUTHORITY_CLASSIFICATION", authority),
        ("INTENT_ANALYSIS", intent),
        ("AUTHORITY_INTENT_RECONCILIATION", reconciliation),
        ("CONTEXT_BUILDING", context),
        ("INSTANCE_SUFFICIENCY", instance),
        ("REASONING_PLANNING", planning),
        ("EVIDENCE_RESOLUTION_ENFORCED", evidence),
    )
    return tuple(build_intelligence_stage_adapter(stage=stage, capability=capability) for stage, capability in capabilities)


__all__ = [
    "CertifiedKnowledgeSelection",
    "KnowledgeSnapshotLookup",
    "RealResponsePrefixDependencies",
    "RealResponsePrefixError",
    "build_real_response_prefix_adapters",
]
