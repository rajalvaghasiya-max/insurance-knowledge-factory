"""Deterministic registry for generic topic-completeness definitions (MO-023I.2)."""

from __future__ import annotations

from collections.abc import Iterable

from insurance_intelligence.contracts.reasoning_plan import DOMAIN_VALUES
from insurance_intelligence.contracts.topic_completeness import TopicDefinition


class TopicCompletenessRegistryError(ValueError):
    """Raised when topic registration or lookup is invalid."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TopicCompletenessRegistryError(f"{label} must be a non-empty string")
    return value.strip()


def _domain(value: object) -> str:
    validated = _text(value, "domain")
    if validated not in DOMAIN_VALUES:
        raise TopicCompletenessRegistryError(
            f"domain must be one of {sorted(DOMAIN_VALUES)}; got {validated!r}"
        )
    return validated


class TopicCompletenessRegistry:
    """Immutable-by-interface registry with deterministic lookup ordering.

    Multiple versions of a topic may coexist. Callers must either request an
    exact version or explicitly mark one version active for unversioned lookup.
    """

    def __init__(self, definitions: Iterable[TopicDefinition] = ()) -> None:
        self._definitions: dict[tuple[str, str], TopicDefinition] = {}
        self._active_versions: dict[str, str] = {}
        for definition in definitions:
            self.register(definition)

    def register(self, definition: TopicDefinition, *, active: bool = False) -> None:
        if not isinstance(definition, TopicDefinition):
            raise TopicCompletenessRegistryError(
                "definition must be a TopicDefinition"
            )
        key = (definition.topic_id, definition.topic_version)
        if key in self._definitions:
            raise TopicCompletenessRegistryError(
                f"duplicate topic registration: {definition.topic_id}@{definition.topic_version}"
            )
        self._definitions[key] = definition
        if active:
            self.set_active_version(
                topic_id=definition.topic_id,
                topic_version=definition.topic_version,
            )

    def set_active_version(self, *, topic_id: str, topic_version: str) -> None:
        topic = _text(topic_id, "topic_id")
        version = _text(topic_version, "topic_version")
        if (topic, version) not in self._definitions:
            raise TopicCompletenessRegistryError(
                f"cannot activate unregistered topic: {topic}@{version}"
            )
        self._active_versions[topic] = version

    def get(
        self,
        topic_id: str,
        topic_version: str | None = None,
    ) -> TopicDefinition:
        topic = _text(topic_id, "topic_id")
        if topic_version is not None:
            key = (topic, _text(topic_version, "topic_version"))
            try:
                return self._definitions[key]
            except KeyError as exc:
                raise TopicCompletenessRegistryError(
                    f"topic not registered: {key[0]}@{key[1]}"
                ) from exc

        active_version = self._active_versions.get(topic)
        if active_version is not None:
            return self._definitions[(topic, active_version)]

        matches = [
            definition
            for (registered_topic, _), definition in self._definitions.items()
            if registered_topic == topic
        ]
        if not matches:
            raise TopicCompletenessRegistryError(
                f"topic not registered: {topic}"
            )
        if len(matches) > 1:
            raise TopicCompletenessRegistryError(
                f"topic lookup is ambiguous without an active version: {topic}"
            )
        return matches[0]

    def all_definitions(self) -> tuple[TopicDefinition, ...]:
        return tuple(sorted(self._definitions.values(), key=self._sort_key))

    def by_domain(self, domain: str) -> tuple[TopicDefinition, ...]:
        validated_domain = _domain(domain)
        return tuple(
            definition
            for definition in self.all_definitions()
            if definition.domain == validated_domain
        )

    def versions(self, topic_id: str) -> tuple[str, ...]:
        topic = _text(topic_id, "topic_id")
        return tuple(
            sorted(
                version
                for registered_topic, version in self._definitions
                if registered_topic == topic
            )
        )

    def active_version(self, topic_id: str) -> str | None:
        return self._active_versions.get(_text(topic_id, "topic_id"))

    def contains(self, *, topic_id: str, topic_version: str) -> bool:
        return (
            _text(topic_id, "topic_id"),
            _text(topic_version, "topic_version"),
        ) in self._definitions

    @staticmethod
    def _sort_key(definition: TopicDefinition) -> tuple[str, str, str]:
        return (
            definition.domain,
            definition.topic_id,
            definition.topic_version,
        )
