"""Executable deterministic Reasoning Engine orchestration for MO-017E."""
from __future__ import annotations

import hashlib
import json
from typing import Mapping, Sequence

from insurance_intelligence.contracts.evidence import EvidencePackage, RequirementResult as EvidenceRequirementResult
from insurance_intelligence.contracts.reasoning import (
    ReasoningContractError,
    ReasoningEngineInput,
    ReasoningEngineOutput,
    RuleExecution,
    build_output,
    build_requirement_result,
    build_rule_execution,
)
from insurance_intelligence.contracts.reasoning_plan import EvidenceRequirement
from insurance_intelligence.reasoning.registry import ReasoningRuleDefinition, ReasoningRuleRegistry
from insurance_intelligence.reasoning.rules import (
    ReasoningRuleError,
    build_rule_input,
    default_rule_registry,
    execute_rule,
)
from insurance_intelligence.reasoning.sufficiency import evaluate_reasoning_sufficiency
from insurance_intelligence.reasoning.trace import ReasoningTraceBuilder


class ReasoningEngineError(ValueError):
    """Raised for invalid cross-stage inputs or engine configuration."""


def _stable_id(prefix: str, payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(encoded).hexdigest()[:20]}"


def _topic(evidence: Sequence[EvidencePackage]) -> str:
    values = {item.field_or_topic.strip().lower().replace("-", "_") for item in evidence}
    if values & {"copay", "co_payment", "conditional_copayment"}:
        return "conditional_copayment"
    return "documented_fact"


def _requirement_type(data: ReasoningEngineInput, requirement_id: str) -> str:
    configured = data.reasoning_context.get("requirement_types", {})
    if isinstance(configured, Mapping):
        value = configured.get(requirement_id)
        if isinstance(value, str) and value.strip():
            return value.strip()
    outcome = data.reasoning_plan.expected_outcome
    if outcome == "DIRECT_FACT_RESPONSE":
        return "EXTRACT_FACTS"
    if outcome in {"CLAUSE_IMPACT_EXPLANATION", "SCENARIO_RESULT", "PARTIAL_RESPONSE"}:
        if data.reasoning_context.get("case_specific_applicability") is True:
            return "ASSESS_APPLICABILITY"
        return "DERIVE_IMPLICATIONS"
    return "EXPLAIN"


def _evidence_role_tokens(evidence: Sequence[EvidencePackage]) -> tuple[str, ...]:
    roles = {item.evidence_role for item in evidence}
    if roles & {"DEFINING", "QUALIFYING"}:
        roles.add("SUPPORTING")
    return tuple(sorted(roles))


def _authority_tokens(evidence: Sequence[EvidencePackage]) -> tuple[str, ...]:
    tokens = {"ANY_GOVERNED"}
    for item in evidence:
        tokens.add(item.authority_requirement)
        if item.source_type in {"POLICY_SCHEDULE", "ENDORSEMENT", "POLICY_WORDING"}:
            tokens.update({"BINDING", "AUTHORITATIVE", "OFFICIAL", "SUPPORTING"})
        elif item.source_type in {"CUSTOMER_INFORMATION_SHEET", "OFFICIAL_PRODUCT_FILING"}:
            tokens.update({"AUTHORITATIVE", "OFFICIAL", "SUPPORTING"})
        else:
            tokens.add("SUPPORTING")
    return tuple(sorted(tokens))


def _evidence_block_reason(result: EvidenceRequirementResult | None, resolution_status: str) -> str | None:
    if result is None:
        return "evidence requirement result is missing"
    if result.status in {"MISSING", "ENTITY_UNRESOLVED", "VERSION_UNRESOLVED", "FAILED_LINEAGE", "NOT_APPLICABLE"}:
        return f"evidence requirement status is {result.status}"
    if result.status == "CONFLICTING" or result.conflict_status not in {"NONE", "NO_CONFLICT", "RESOLVED"}:
        return "material evidence conflict remains"
    if resolution_status in {"NOT_RESOLVED", "INVALID_INPUT", "CONFLICTING"}:
        return f"evidence resolution status is {resolution_status}"
    return None


def _execution_id(request_id: str, requirement_id: str, rule: ReasoningRuleDefinition, status: str) -> str:
    return _stable_id("execution", {"request_id": request_id, "requirement_id": requirement_id, "rule": rule.registry_key, "status": status})


class ReasoningEngine:
    """Read-only deterministic orchestrator over validated plan and evidence outputs."""

    def __init__(self, registry: ReasoningRuleRegistry | None = None) -> None:
        self._registry = registry or default_rule_registry()

    def reason(self, data: ReasoningEngineInput) -> ReasoningEngineOutput:
        if not isinstance(data, ReasoningEngineInput):
            raise ReasoningEngineError("data must be a validated ReasoningEngineInput")
        plan = data.reasoning_plan
        evidence_output = data.evidence_resolution
        if plan.request_id != data.request_id or evidence_output.request_id != data.request_id:
            raise ReasoningEngineError("request_id mismatch across reasoning stages")

        reasoning_id = _stable_id("reasoning", {"request_id": data.request_id, "plan_id": plan.plan_id, "resolution_id": evidence_output.resolution_id, "strict_mode": data.strict_mode, "context": dict(sorted((str(k), repr(v)) for k, v in data.reasoning_context.items()))})
        trace = ReasoningTraceBuilder(_stable_id("trace", {"reasoning_id": reasoning_id}))
        trace.add("REASONING_STARTED", "STARTED", "validated planner and evidence outputs received", input_references=(plan.plan_id, evidence_output.resolution_id))

        if plan.plan_status == "OUT_OF_SCOPE":
            trace.add("REASONING_COMPLETED", "OUT_OF_SCOPE", "planner classified the request as out of scope")
            return build_output(request_id=data.request_id, reasoning_id=reasoning_id, reasoning_sufficiency="UNSUPPORTED", reasoning_status="OUT_OF_SCOPE", confidence=0.0, reasoning_trace=trace.build())
        if plan.execution_mode == "NO_EXECUTION" or not plan.required_evidence:
            trace.add("REASONING_COMPLETED", "NO_REASONING_REQUIRED", "planner supplied no executable reasoning requirements")
            return build_output(request_id=data.request_id, reasoning_id=reasoning_id, reasoning_sufficiency="UNSUPPORTED", reasoning_status="NO_REASONING_REQUIRED", confidence=0.0, reasoning_trace=trace.build())

        evidence_by_requirement: dict[str, tuple[EvidencePackage, ...]] = {}
        for requirement in plan.required_evidence:
            evidence_by_requirement[requirement.requirement_id] = tuple(sorted((item for item in evidence_output.evidence_packages if item.requirement_id == requirement.requirement_id), key=lambda item: item.evidence_id))
        evidence_results = {item.requirement_id: item for item in evidence_output.requirement_results}

        findings = []
        requirement_results = []
        executions: list[RuleExecution] = []
        unsupported: list[str] = []

        for requirement in sorted(plan.required_evidence, key=lambda item: item.requirement_id):
            trace.add("REQUIREMENT_RECEIVED", "RECEIVED", "reasoning requirement derived from planner evidence requirement", requirement_id=requirement.requirement_id, input_references=(requirement.requested_by_step,))
            evidence = evidence_by_requirement[requirement.requirement_id]
            evidence_result = evidence_results.get(requirement.requirement_id)
            block_reason = _evidence_block_reason(evidence_result, evidence_output.resolution_status)
            trace.add("EVIDENCE_STATUS_CHECKED", "BLOCKED" if block_reason else "USABLE", block_reason or "governed evidence is usable", requirement_id=requirement.requirement_id, evidence_ids=tuple(item.evidence_id for item in evidence))
            if block_reason:
                status = "CONFLICTING" if "conflict" in block_reason else "BLOCKED_BY_EVIDENCE"
                requirement_results.append(build_requirement_result(requirement_id=requirement.requirement_id, status=status, unsupported_reason=block_reason, evidence_satisfied=False, context_satisfied=True, conflict_status="UNRESOLVED" if status == "CONFLICTING" else "NONE", confidence=0.0))
                trace.add("FINDING_BLOCKED", status, block_reason, requirement_id=requirement.requirement_id)
                continue

            topic = _topic(evidence)
            requirement_type = _requirement_type(data, requirement.requirement_id)
            input_keys = tuple(sorted(str(key) for key in data.reasoning_context.keys()))
            eligible = self._registry.eligible_rules(domain="health", topic=topic, requirement_type=requirement_type, available_evidence_topics=(topic,), available_evidence_roles=_evidence_role_tokens(evidence), available_authorities=_authority_tokens(evidence), available_inputs=input_keys)
            for rule in eligible:
                trace.add("RULE_CANDIDATE_FOUND", "ELIGIBLE", "registry metadata matched available governed inputs", requirement_id=requirement.requirement_id, rule_id=rule.rule_id, evidence_ids=tuple(item.evidence_id for item in evidence))

            if not eligible:
                reason = f"no registered rule supports {requirement_type} for topic {topic}"
                requirement_results.append(build_requirement_result(requirement_id=requirement.requirement_id, status="NO_APPLICABLE_RULE", unsupported_reason=reason, evidence_satisfied=True, context_satisfied=True, conflict_status="NONE", confidence=0.0))
                unsupported.append(requirement.requirement_id)
                trace.add("FINDING_BLOCKED", "NO_APPLICABLE_RULE", reason, requirement_id=requirement.requirement_id)
                continue

            created = []
            rejected = []
            executed_ids = []
            missing_inputs: list[str] = []
            for rule in eligible:
                trace.add("RULE_SELECTED", "SELECTED", "deterministic registry order selected rule", requirement_id=requirement.requirement_id, rule_id=rule.rule_id)
                try:
                    rule_input = build_rule_input(requirement_id=requirement.requirement_id, evidence=evidence, approved_context=data.reasoning_context, scope="product")
                    produced = execute_rule(rule.rule_id, rule_input)
                except ReasoningRuleError as exc:
                    rejected.append(rule.rule_id)
                    reason = str(exc)
                    if "required" in reason or "context" in reason or "trigger status" in reason:
                        missing_inputs.extend(rule.required_inputs)
                    executions.append(build_rule_execution(execution_id=_execution_id(data.request_id, requirement.requirement_id, rule, "REJECTED"), requirement_id=requirement.requirement_id, rule_id=rule.rule_id, rule_version=rule.rule_version, status="REJECTED", evidence_ids=tuple(item.evidence_id for item in evidence), input_keys=input_keys, rejection_reason=reason, confidence=0.0))
                    trace.add("RULE_REJECTED", "REJECTED", reason, requirement_id=requirement.requirement_id, rule_id=rule.rule_id, evidence_ids=tuple(item.evidence_id for item in evidence))
                    continue
                executed_ids.append(rule.rule_id)
                created.extend(produced)
                confidence = min((item.confidence for item in produced), default=0.0)
                executions.append(build_rule_execution(execution_id=_execution_id(data.request_id, requirement.requirement_id, rule, "EXECUTED"), requirement_id=requirement.requirement_id, rule_id=rule.rule_id, rule_version=rule.rule_version, status="EXECUTED", evidence_ids=tuple(item.evidence_id for item in evidence), input_keys=input_keys, output_finding_ids=tuple(item.finding_id for item in produced), confidence=confidence))
                trace.add("RULE_EXECUTED", "EXECUTED", "registered deterministic rule completed", requirement_id=requirement.requirement_id, rule_id=rule.rule_id, evidence_ids=tuple(item.evidence_id for item in evidence), output_finding_ids=tuple(item.finding_id for item in produced))
                for finding in produced:
                    trace.add("FINDING_CREATED", finding.finding_status, "structured finding created from governed evidence", requirement_id=requirement.requirement_id, rule_id=rule.rule_id, evidence_ids=finding.evidence_ids, output_finding_ids=(finding.finding_id,))

            findings.extend(created)
            if created:
                finding_statuses = {item.finding_status for item in created}
                if finding_statuses <= {"SUPPORTED"}:
                    status = "SATISFIED"
                elif "PARTIALLY_SUPPORTED" in finding_statuses:
                    status = "PARTIALLY_SATISFIED"
                elif "CONDITIONAL" in finding_statuses:
                    status = "CONDITIONAL"
                else:
                    status = "SATISFIED_WITH_LIMITATIONS"
                confidence = round(sum(item.confidence for item in created) / len(created), 6)
                requirement_results.append(build_requirement_result(requirement_id=requirement.requirement_id, status=status, executed_rule_ids=executed_ids, finding_ids=tuple(item.finding_id for item in created), rejected_rule_ids=rejected, missing_inputs=tuple(sorted(set(missing_inputs))), evidence_satisfied=True, context_satisfied=not missing_inputs, conflict_status="NONE", confidence=confidence))
            else:
                reason = "all eligible rules were rejected"
                status = "BLOCKED_BY_CONTEXT" if missing_inputs else "UNSUPPORTED"
                requirement_results.append(build_requirement_result(requirement_id=requirement.requirement_id, status=status, rejected_rule_ids=rejected, missing_inputs=tuple(sorted(set(missing_inputs))), unsupported_reason=reason, evidence_satisfied=True, context_satisfied=not missing_inputs, conflict_status="NONE", confidence=0.0))
                unsupported.append(requirement.requirement_id)
                trace.add("FINDING_BLOCKED", status, reason, requirement_id=requirement.requirement_id)

        decision = evaluate_reasoning_sufficiency(requirement_results)
        trace.add("SUFFICIENCY_EVALUATED", decision.reasoning_sufficiency, "requirement outcomes aggregated with fail-closed precedence", input_references=tuple(item.requirement_id for item in requirement_results))
        trace.add("REASONING_COMPLETED", decision.reasoning_status, "deterministic reasoning orchestration completed", output_finding_ids=tuple(sorted(item.finding_id for item in findings)))
        return build_output(request_id=data.request_id, reasoning_id=reasoning_id, findings=tuple(sorted(findings, key=lambda item: item.finding_id)), requirement_results=tuple(sorted(requirement_results, key=lambda item: item.requirement_id)), rule_executions=tuple(sorted(executions, key=lambda item: item.execution_id)), unsupported_requirements=tuple(sorted(set(unsupported))), assumptions=(), limitations=decision.limitations, reasoning_sufficiency=decision.reasoning_sufficiency, reasoning_status=decision.reasoning_status, confidence=decision.confidence, reasoning_trace=trace.build())
