"""Generic certification of governed conditional co-payment bindings.

This module is insurer-independent. It follows a reviewed generic legal-condition
binding back to its registered primary legal evidence, runs the production
conditional co-payment reasoner, and builds certification cases from the resulting
semantic findings. It does not publish assertions or select policy-specific options.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from insurance_intelligence.contracts.evidence import (
    EvidencePackage,
    EvidenceResolverOutput,
    Lineage,
    RequirementResult,
)
from insurance_intelligence.contracts.rule_certification import (
    RuleCertificationResult,
    build_component_certification_expectation,
    build_rule_certification_expectation,
)
from insurance_intelligence.contracts.topic_profile import build_topic_profile
from insurance_intelligence.reasoning.rules import (
    build_rule_input,
    conditional_copayment_obligation,
)
from insurance_intelligence.rule_certification.fixtures import RuleCertificationCaseFixture
from insurance_intelligence.rule_certification.runner import run_rule_certification
from insurance_intelligence.topic_completeness.catalogue import (
    build_conditional_obligation_definition,
)


class ConditionalCopaymentCertificationError(ValueError):
    """Raised when a governed co-payment binding cannot be certified safely."""


@dataclass(frozen=True)
class ConditionalCopaymentCertificationBundle:
    binding_manifest_path: str
    cases: tuple[RuleCertificationCaseFixture, ...]


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConditionalCopaymentCertificationError(f"{label} must be a non-empty string")
    return value.strip()


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ConditionalCopaymentCertificationError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ConditionalCopaymentCertificationError(f"{label} must be a JSON array")
    return value


def _safe_relative(value: object, label: str) -> str:
    raw = _text(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise ConditionalCopaymentCertificationError(f"{label} must be repository-relative")
    return path.as_posix()


def _load(root: Path, relative_path: str, label: str) -> tuple[Mapping[str, Any], str]:
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ConditionalCopaymentCertificationError(f"{label} must remain under repository_root") from exc
    if not path.is_file():
        raise FileNotFoundError(f"{label} was not found: {relative_path}")
    raw = path.read_bytes()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConditionalCopaymentCertificationError(f"{label} must be valid UTF-8 JSON") from exc
    return _mapping(parsed, label), sha256(raw).hexdigest()


def _candidate_index(registration: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    review = _mapping(registration.get("evidence_review"), "registration.evidence_review")
    result: dict[str, Mapping[str, Any]] = {}
    for raw in _items(review.get("candidates"), "registration.evidence_review.candidates"):
        candidate = _mapping(raw, "candidate")
        result[_text(candidate.get("candidate_id"), "candidate.candidate_id")] = candidate
    return result


def _profile(profile_id: str):
    definition = build_conditional_obligation_definition()
    return build_topic_profile(
        profile_id=profile_id,
        profile_version="1.0",
        definition=definition,
        required_component_ids=(
            "obligation_value",
            "trigger_condition",
            "applicability_scope",
        ),
        optional_component_ids=("exception_condition", "calculation_basis"),
        explanation_blocking_component_ids=(
            "obligation_value",
            "trigger_condition",
            "applicability_scope",
        ),
    )


def _requirement(requirement_id: str, evidence_id: str) -> RequirementResult:
    return RequirementResult(
        requirement_id=requirement_id,
        status="SATISFIED",
        matched_evidence_ids=(evidence_id,),
        rejected_candidate_ids=(),
        missing_reason=None,
        authority_satisfied=True,
        version_satisfied=True,
        lineage_satisfied=True,
        conflict_status="NONE",
        confidence=1.0,
    )


def _component_evidence(
    *,
    case_id: str,
    component_id: str,
    requirement_type: str,
    claim: str,
    assertion_id: str,
    reviewed_statement: str,
    document: Mapping[str, Any],
    candidate: Mapping[str, Any],
    binding_path: str,
    binding_sha: str,
) -> EvidencePackage:
    requirement_id = f"requirement:{case_id}:{component_id}"
    evidence_id = f"evidence:{case_id}:{component_id}"
    document_id = _text(document.get("document_id"), "document.document_id")
    document_version_id = _text(
        document.get("document_version_id"), "document.document_version_id"
    )
    source_path = _text(document.get("storage_locator"), "document.storage_locator")
    source_sha = _text(document.get("content_sha256"), "document.content_sha256")
    return EvidencePackage(
        evidence_id=evidence_id,
        requirement_id=requirement_id,
        subject_reference=f"product:{case_id}",
        governed_entity_reference=f"assertion:{assertion_id}",
        field_or_topic=requirement_type,
        claim=claim,
        evidence_role="DEFINING",
        source_type=_text(document.get("document_type"), "document.document_type").upper(),
        document_reference=document_id,
        document_version=document_version_id,
        effective_from=None,
        effective_to=None,
        page=candidate.get("source_page"),
        section="Conditional co-payment",
        source_excerpt=reviewed_statement,
        normalized_fact_reference=f"{assertion_id}:{component_id}",
        authority_rank=1,
        authority_requirement="AUTHORITATIVE",
        version_status="CURRENT_APPLICABLE",
        applicability_status="APPLICABLE",
        lineage=Lineage(
            source_artifact_path=source_path,
            source_artifact_sha256=source_sha,
            governed_record_path=binding_path,
            governed_record_sha256=binding_sha,
            binding_reference=f"assertion:{assertion_id}",
            projection_reference=f"conditional_obligation:{component_id}",
            lineage_status="VERIFIED",
        ),
        retrieval_basis=(
            "reviewed_generic_legal_condition_binding",
            "production_conditional_copayment_obligation",
            _text(candidate.get("candidate_id"), "candidate.candidate_id"),
        ),
        confidence=1.0,
    )


def build_conditional_copayment_certification_cases(
    *,
    binding_manifest_path: str | Path,
    repository_root: str | Path,
    assertion_ids: Sequence[str] | None = None,
) -> ConditionalCopaymentCertificationBundle:
    root = Path(repository_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"repository_root was not found: {root}")
    binding_path = _safe_relative(str(binding_manifest_path), "binding_manifest_path")
    binding, binding_sha = _load(root, binding_path, "binding_manifest")
    if binding.get("binding_type") != "generic_legal_condition_binding_v1":
        raise ConditionalCopaymentCertificationError("binding manifest type is not supported")
    if binding.get("binding_status") != "reviewed_generic_legal_conditions_bound_not_published":
        raise ConditionalCopaymentCertificationError("binding manifest is not review-ready")

    selected_ids = None if assertion_ids is None else tuple(_text(v, "assertion_ids[]") for v in assertion_ids)
    if selected_ids is not None and len(selected_ids) != len(set(selected_ids)):
        raise ConditionalCopaymentCertificationError("assertion_ids must be unique")

    bundle_path = _safe_relative(binding.get("generic_source_bundle_path"), "generic_source_bundle_path")
    bundle, bundle_sha = _load(root, bundle_path, "generic_source_bundle")
    if binding.get("generic_source_bundle_sha256") != bundle_sha:
        raise ConditionalCopaymentCertificationError("generic source bundle hash mismatch")

    sources: dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]] = {}
    for raw_source in _items(bundle.get("sources"), "generic_source_bundle.sources"):
        source = _mapping(raw_source, "generic_source")
        document_id = _text(source.get("document_id"), "source.document_id")
        registration_path = _safe_relative(
            source.get("registration_output_path"), "source.registration_output_path"
        )
        registration, _ = _load(root, registration_path, f"registration[{document_id}]")
        sources[document_id] = (source, registration)

    cases: list[RuleCertificationCaseFixture] = []
    seen_assertion_ids: set[str] = set()
    for raw_assertion in _items(binding.get("assertions"), "binding_manifest.assertions"):
        assertion = _mapping(raw_assertion, "binding_assertion")
        assertion_id = _text(assertion.get("assertion_id"), "assertion.assertion_id")
        if selected_ids is not None and assertion_id not in selected_ids:
            continue
        seen_assertion_ids.add(assertion_id)
        if assertion.get("assertion_type") != "conditional_copayment_rule":
            raise ConditionalCopaymentCertificationError(
                f"{assertion_id} is not a conditional_copayment_rule"
            )
        if assertion.get("publication_status") != "bound_not_published":
            raise ConditionalCopaymentCertificationError(
                f"{assertion_id} must remain bound_not_published during certification"
            )
        reviewed_statement = _text(
            assertion.get("reviewed_statement"), "assertion.reviewed_statement"
        )
        evidence_entries = _items(assertion.get("evidence"), "assertion.evidence")
        if len(evidence_entries) != 1:
            raise ConditionalCopaymentCertificationError(
                f"{assertion_id} requires exactly one bound evidence selection"
            )
        evidence_entry = _mapping(evidence_entries[0], "assertion.evidence[0]")
        if evidence_entry.get("authority_role") != "primary_legal":
            raise ConditionalCopaymentCertificationError(
                f"{assertion_id} evidence must be primary_legal"
            )
        document_id = _text(evidence_entry.get("document_id"), "evidence.document_id")
        if document_id not in sources:
            raise ConditionalCopaymentCertificationError(
                f"{assertion_id} references an unregistered source"
            )
        source, registration = sources[document_id]
        document = _mapping(registration.get("document"), "registration.document")
        if document.get("document_version_id") != evidence_entry.get("document_version_id"):
            raise ConditionalCopaymentCertificationError(
                f"{assertion_id} document version mismatch"
            )
        candidate_id = _text(evidence_entry.get("candidate_id"), "evidence.candidate_id")
        candidate = _candidate_index(registration).get(candidate_id)
        if candidate is None:
            raise ConditionalCopaymentCertificationError(
                f"{assertion_id} candidate is missing from registration"
            )
        if candidate.get("text_sha256") != evidence_entry.get("candidate_text_sha256"):
            raise ConditionalCopaymentCertificationError(
                f"{assertion_id} candidate text hash mismatch"
            )

        raw = _component_evidence(
            case_id=assertion_id,
            component_id="governed_statement",
            requirement_type="conditional_copayment",
            claim=reviewed_statement,
            assertion_id=assertion_id,
            reviewed_statement=reviewed_statement,
            document=document,
            candidate=candidate,
            binding_path=binding_path,
            binding_sha=binding_sha,
        )
        finding = conditional_copayment_obligation(
            build_rule_input(
                requirement_id=raw.requirement_id,
                evidence=(raw,),
                approved_context={},
                scope=f"{bundle.get('product_context', {}).get('insurer_id')}:{bundle.get('product_context', {}).get('product_id')}",
            )
        )[0]
        if finding.applicability_scope is None:
            raise ConditionalCopaymentCertificationError(
                f"{assertion_id} production reasoning did not resolve applicability_scope"
            )

        component_claims: list[tuple[str, str, str]] = [
            ("obligation_value", "OBLIGATION_VALUE", finding.object_or_effect),
            ("trigger_condition", "TRIGGER_CONDITION", finding.trigger or ""),
            ("applicability_scope", "APPLICABILITY_SCOPE", finding.applicability_scope),
        ]
        if finding.exception:
            component_claims.append(
                ("exception_condition", "EXCEPTION_CONDITION", finding.exception)
            )

        component_evidence = tuple(
            _component_evidence(
                case_id=assertion_id,
                component_id=component_id,
                requirement_type=requirement_type,
                claim=claim,
                assertion_id=assertion_id,
                reviewed_statement=reviewed_statement,
                document=document,
                candidate=candidate,
                binding_path=binding_path,
                binding_sha=binding_sha,
            )
            for component_id, requirement_type, claim in component_claims
        )
        requirements = tuple(
            _requirement(package.requirement_id, package.evidence_id)
            for package in component_evidence
        )
        case_id = f"conditional_copayment:{assertion_id}"
        expectation = build_rule_certification_expectation(
            certification_id=case_id,
            governed_subject_reference=f"assertion:{assertion_id}",
            topic_id="conditional_obligation",
            topic_version="1.0",
            expected_completeness_statuses=("COMPLETE",),
            expected_explanation_permitted=True,
            component_expectations=tuple(
                build_component_certification_expectation(
                    component_id=component_id,
                    acceptable_statuses=("SATISFIED",),
                )
                for component_id, _, _ in component_claims
            ),
        )
        output = EvidenceResolverOutput(
            contract_version="1.0",
            request_id=f"request:{case_id}",
            resolution_id=f"resolution:{case_id}",
            evidence_packages=component_evidence,
            requirement_results=requirements,
            entity_resolutions=(),
            document_resolutions=(),
            conflicts=(),
            missing_evidence=(),
            sufficiency="COMPLETE",
            limitations=(
                "The governed binding remains bound_not_published and is used only for internal certification.",
                "Certification does not select policy-specific co-payment options or decide claim payment.",
            ),
            resolution_trace=(),
            resolution_status="RESOLVED",
            confidence=1.0,
        )
        cases.append(
            RuleCertificationCaseFixture(
                case_id=case_id,
                description=f"Conditional co-payment certification for {assertion_id}.",
                domain="health",
                expectation=expectation,
                evidence_output=output,
                expected_outcome="PASS",
            )
        )

    if selected_ids is not None:
        missing = set(selected_ids) - seen_assertion_ids
        if missing:
            raise ConditionalCopaymentCertificationError(
                f"requested assertion_ids were not found: {sorted(missing)}"
            )
    if not cases:
        raise ConditionalCopaymentCertificationError("no conditional co-payment assertions were selected")
    return ConditionalCopaymentCertificationBundle(
        binding_manifest_path=binding_path,
        cases=tuple(sorted(cases, key=lambda item: item.case_id)),
    )


def run_conditional_copayment_certification_cases(
    bundle: ConditionalCopaymentCertificationBundle,
) -> tuple[RuleCertificationResult, ...]:
    if not isinstance(bundle, ConditionalCopaymentCertificationBundle):
        raise ConditionalCopaymentCertificationError(
            "bundle must be a ConditionalCopaymentCertificationBundle"
        )
    results = []
    for case in bundle.cases:
        result = run_rule_certification(
            expectation=case.expectation,
            evidence_output=case.evidence_output,
            domain=case.domain,
            profile=_profile(case.case_id),
        )
        results.append(result)
    return tuple(results)
