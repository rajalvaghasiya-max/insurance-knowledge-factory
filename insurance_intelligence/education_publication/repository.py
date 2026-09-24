"""Validated repository and generic lookup for governed education publications."""
from __future__ import annotations

from dataclasses import fields
import json
from pathlib import Path
from typing import Iterable

from insurance_intelligence.contracts.education_publication import (
    CUSTOMER_EDUCATION,
    EducationPublicationRecord,
    build_education_example,
    validate_education_publication_record,
)
from insurance_intelligence.contracts.full_cycle import OrchestrationRequest
from insurance_intelligence.contracts.intent import IntentAnalyzerOutput
from insurance_intelligence.contracts.explanation import (
    PracticalIllustrationProfile,
    build_practical_illustration_profile,
)
from insurance_intelligence.education_publication.admission import (
    evaluate_education_admission,
)
from insurance_intelligence.terminology.concept_resolver import CanonicalConceptResolver


class EducationPublicationRepositoryError(ValueError):
    """Raised when persisted education-publication state is invalid."""


def _publication_from_mapping(raw: object) -> EducationPublicationRecord:
    if not isinstance(raw, dict):
        raise EducationPublicationRepositoryError(
            "education publication JSON must contain an object"
        )

    expected = {item.name for item in fields(EducationPublicationRecord)}
    actual = set(raw)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        raise EducationPublicationRepositoryError(
            f"education publication fields mismatch; missing={missing}; extra={extra}"
        )

    raw_examples = raw["examples"]
    if not isinstance(raw_examples, list):
        raise EducationPublicationRepositoryError("examples must be a list")

    examples = []
    for index, item in enumerate(raw_examples):
        if not isinstance(item, dict):
            raise EducationPublicationRepositoryError(
                f"examples[{index}] must be an object"
            )
        if set(item) != {"scenario", "result", "boundary"}:
            raise EducationPublicationRepositoryError(
                f"examples[{index}] must contain scenario, result, boundary only"
            )
        examples.append(
            build_education_example(
                scenario=item["scenario"],
                result=item["result"],
                boundary=item["boundary"],
            )
        )

    def _tuple_of_strings(field: str) -> tuple[str, ...]:
        value = raw[field]
        if not isinstance(value, list):
            raise EducationPublicationRepositoryError(f"{field} must be a list")
        if any(not isinstance(item, str) for item in value):
            raise EducationPublicationRepositoryError(
                f"{field} must contain strings only"
            )
        return tuple(value)

    try:
        record = EducationPublicationRecord(
            contract_version=raw["contract_version"],
            publication_id=raw["publication_id"],
            publication_status=raw["publication_status"],
            allowed_uses=_tuple_of_strings("allowed_uses"),
            concept_id=raw["concept_id"],
            canonical_name=raw["canonical_name"],
            definition=raw["definition"],
            plain_language_explanation=raw["plain_language_explanation"],
            practical_implication=raw["practical_implication"],
            examples=tuple(examples),
            limitations=_tuple_of_strings("limitations"),
            product_specific_boundary=raw["product_specific_boundary"],
            customer_document_boundary=raw["customer_document_boundary"],
            evidence_references=_tuple_of_strings("evidence_references"),
            source_asset_id=raw["source_asset_id"],
            source_asset_digest=raw["source_asset_digest"],
            source_governed_record_id=raw["source_governed_record_id"],
            source_knowledge_version=raw["source_knowledge_version"],
            review_decision_id=raw["review_decision_id"],
            publication_authority=raw["publication_authority"],
            publication_receipt_id=raw["publication_receipt_id"],
        )
        return validate_education_publication_record(record)
    except (TypeError, ValueError) as exc:
        raise EducationPublicationRepositoryError(
            f"invalid education publication record: {exc}"
        ) from exc


class EducationPublicationRepository:
    """Immutable repository of validated education publications."""

    def __init__(
        self,
        publications: Iterable[EducationPublicationRecord] = (),
    ) -> None:
        records = tuple(publications)
        if any(not isinstance(item, EducationPublicationRecord) for item in records):
            raise EducationPublicationRepositoryError(
                "publications must contain EducationPublicationRecord values"
            )

        by_id: dict[str, EducationPublicationRecord] = {}
        by_concept: dict[str, EducationPublicationRecord] = {}
        for record in records:
            validated = validate_education_publication_record(record)
            if validated.publication_id in by_id:
                raise EducationPublicationRepositoryError(
                    f"duplicate publication_id: {validated.publication_id}"
                )
            if validated.concept_id in by_concept:
                raise EducationPublicationRepositoryError(
                    f"duplicate education publication for concept_id: {validated.concept_id}"
                )
            by_id[validated.publication_id] = validated
            by_concept[validated.concept_id] = validated

        self._by_id = by_id
        self._by_concept = by_concept

    @classmethod
    def from_json_files(
        cls,
        paths: Iterable[Path],
    ) -> "EducationPublicationRepository":
        publications = []
        for path in paths:
            resolved = Path(path)
            if not resolved.is_file():
                raise EducationPublicationRepositoryError(
                    f"education publication file not found: {resolved}"
                )
            try:
                raw = json.loads(resolved.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise EducationPublicationRepositoryError(
                    f"unable to read education publication: {resolved}"
                ) from exc
            publications.append(_publication_from_mapping(raw))
        return cls(publications)

    def get_by_concept(
        self,
        concept_id: str,
    ) -> EducationPublicationRecord | None:
        if not isinstance(concept_id, str) or not concept_id.strip():
            raise EducationPublicationRepositoryError(
                "concept_id must be a non-empty string"
            )
        return self._by_concept.get(concept_id.strip())

    def all_publications(self) -> tuple[EducationPublicationRecord, ...]:
        return tuple(self._by_id[key] for key in sorted(self._by_id))


class GovernedEducationPublicationLookup:
    """Select admitted education for exact governed concepts mentioned in a request."""

    def __init__(
        self,
        *,
        repository: EducationPublicationRepository,
        concept_resolver: CanonicalConceptResolver,
    ) -> None:
        if not isinstance(repository, EducationPublicationRepository):
            raise TypeError("repository must be EducationPublicationRepository")
        if not isinstance(concept_resolver, CanonicalConceptResolver):
            raise TypeError("concept_resolver must be CanonicalConceptResolver")
        self._repository = repository
        self._concept_resolver = concept_resolver

    def __call__(
        self,
        request: object,
        intent_output: IntentAnalyzerOutput,
    ) -> tuple[EducationPublicationRecord, ...]:
        if not isinstance(request, OrchestrationRequest):
            raise EducationPublicationRepositoryError(
                "request must be OrchestrationRequest"
            )
        if not isinstance(intent_output, IntentAnalyzerOutput):
            raise EducationPublicationRepositoryError(
                "intent_output must be IntentAnalyzerOutput"
            )

        question = request.question or ""
        domain = intent_output.domain if intent_output.domain != "unknown" else None
        mentions = self._concept_resolver.resolve_mentions(
            question,
            domain=domain,
        )

        publications: list[EducationPublicationRecord] = []
        seen_ids: set[str] = set()
        for mention in mentions:
            concept = mention.selected_concept
            if concept is None or concept.downstream_topic is None:
                continue
            publication = self._repository.get_by_concept(
                concept.downstream_topic
            )
            if publication is None:
                continue
            admission = evaluate_education_admission(
                publication=publication,
                requested_use=CUSTOMER_EDUCATION,
                concept_id=concept.downstream_topic,
            )
            if not admission.admitted:
                continue
            if publication.publication_id in seen_ids:
                continue
            publications.append(publication)
            seen_ids.add(publication.publication_id)

        return tuple(publications)



def _illustration_profile_from_mapping(raw: object) -> PracticalIllustrationProfile:
    if not isinstance(raw, dict):
        raise EducationPublicationRepositoryError(
            "practical illustration profile JSON must contain an object"
        )
    expected = {
        "schema_version",
        "profile_type",
        "review_status",
        "review_decision_id",
        "profile",
    }
    if set(raw) != expected:
        raise EducationPublicationRepositoryError(
            "practical illustration profile fields mismatch"
        )
    if raw["schema_version"] != "1.0":
        raise EducationPublicationRepositoryError(
            "practical illustration profile schema_version must be '1.0'"
        )
    if raw["profile_type"] != "practical_illustration_profile_v1":
        raise EducationPublicationRepositoryError(
            "unsupported practical illustration profile_type"
        )
    if raw["review_status"] != "APPROVED":
        raise EducationPublicationRepositoryError(
            "practical illustration profile must be human reviewed and APPROVED"
        )
    review_decision_id = raw["review_decision_id"]
    if not isinstance(review_decision_id, str) or not review_decision_id.strip():
        raise EducationPublicationRepositoryError(
            "practical illustration profile requires review_decision_id"
        )
    profile = raw["profile"]
    if not isinstance(profile, dict):
        raise EducationPublicationRepositoryError(
            "practical illustration profile.profile must be an object"
        )
    required = {
        "profile_id",
        "concept_id",
        "duration_unit",
        "before_probe_value",
        "after_probe_value",
        "related_condition",
        "unrelated_condition",
        "during_wait_template",
        "unrelated_condition_template",
        "after_wait_template",
        "boundary_text",
    }
    if set(profile) != required:
        raise EducationPublicationRepositoryError(
            "practical illustration profile payload fields mismatch"
        )
    try:
        return build_practical_illustration_profile(**profile)
    except (TypeError, ValueError) as exc:
        raise EducationPublicationRepositoryError(
            f"invalid practical illustration profile: {exc}"
        ) from exc


class PracticalIllustrationProfileRepository:
    """Immutable repository of explicitly reviewed practical-illustration profiles."""

    def __init__(
        self,
        profiles: Iterable[PracticalIllustrationProfile] = (),
    ) -> None:
        records = tuple(profiles)
        if any(not isinstance(item, PracticalIllustrationProfile) for item in records):
            raise EducationPublicationRepositoryError(
                "profiles must contain PracticalIllustrationProfile values"
            )
        by_concept: dict[str, PracticalIllustrationProfile] = {}
        for profile in records:
            if profile.concept_id in by_concept:
                raise EducationPublicationRepositoryError(
                    f"duplicate practical illustration profile for concept_id: {profile.concept_id}"
                )
            by_concept[profile.concept_id] = profile
        self._by_concept = by_concept

    @classmethod
    def from_json_files(
        cls,
        paths: Iterable[Path],
    ) -> "PracticalIllustrationProfileRepository":
        profiles = []
        for path in paths:
            resolved = Path(path)
            if not resolved.is_file():
                raise EducationPublicationRepositoryError(
                    f"practical illustration profile file not found: {resolved}"
                )
            try:
                raw = json.loads(resolved.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise EducationPublicationRepositoryError(
                    f"unable to read practical illustration profile: {resolved}"
                ) from exc
            profiles.append(_illustration_profile_from_mapping(raw))
        return cls(profiles)

    def get_by_concept(
        self,
        concept_id: str,
    ) -> PracticalIllustrationProfile | None:
        if not isinstance(concept_id, str) or not concept_id.strip():
            raise EducationPublicationRepositoryError(
                "concept_id must be a non-empty string"
            )
        return self._by_concept.get(concept_id.strip())


class GovernedPracticalIllustrationLookup:
    """Select reviewed illustration profiles for exact governed concepts in a request."""

    def __init__(
        self,
        *,
        repository: PracticalIllustrationProfileRepository,
        concept_resolver: CanonicalConceptResolver,
    ) -> None:
        if not isinstance(repository, PracticalIllustrationProfileRepository):
            raise TypeError(
                "repository must be PracticalIllustrationProfileRepository"
            )
        if not isinstance(concept_resolver, CanonicalConceptResolver):
            raise TypeError("concept_resolver must be CanonicalConceptResolver")
        self._repository = repository
        self._concept_resolver = concept_resolver

    def __call__(
        self,
        request: object,
        intent_output: IntentAnalyzerOutput,
    ) -> tuple[PracticalIllustrationProfile, ...]:
        if not isinstance(request, OrchestrationRequest):
            raise EducationPublicationRepositoryError(
                "request must be OrchestrationRequest"
            )
        if not isinstance(intent_output, IntentAnalyzerOutput):
            raise EducationPublicationRepositoryError(
                "intent_output must be IntentAnalyzerOutput"
            )
        question = request.question or ""
        domain = intent_output.domain if intent_output.domain != "unknown" else None
        mentions = self._concept_resolver.resolve_mentions(question, domain=domain)
        profiles: list[PracticalIllustrationProfile] = []
        seen: set[str] = set()
        for mention in mentions:
            concept = mention.selected_concept
            if concept is None or concept.downstream_topic is None:
                continue
            profile = self._repository.get_by_concept(concept.downstream_topic)
            if profile is None or profile.profile_id in seen:
                continue
            profiles.append(profile)
            seen.add(profile.profile_id)
        return tuple(profiles)


__all__ = [
    "EducationPublicationRepository",
    "EducationPublicationRepositoryError",
    "GovernedEducationPublicationLookup",
    "GovernedPracticalIllustrationLookup",
    "PracticalIllustrationProfileRepository",
]
