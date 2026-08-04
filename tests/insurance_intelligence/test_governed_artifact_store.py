from __future__ import annotations

from insurance_intelligence.llm.governed_artifact_store import (
    FilesystemGovernedArtifactStore,
    GovernedArtifactIdentity,
    GovernedArtifactRecord,
    GovernedArtifactStoreError,
)


def _identity(**changes):
    values = {
        "stage": "RENDERING",
        "contract_hash": "contract-hash",
        "evidence_hash": "evidence-hash",
        "rule_family_id": "CONDITIONAL_COPAYMENT",
        "rule_family_version": "1.0",
        "binding_hash": "binding-hash",
        "audience": "customer",
        "reading_level": "plain_language",
        "provider": "openai",
        "model": "gpt-test",
        "prompt_version": "renderer-v1",
        "schema_version": "schema-v1",
        "generation_config_hash": "config-hash",
        "data_classification": "PUBLIC",
    }
    values.update(changes)
    return GovernedArtifactIdentity(**values)


def _record(identity):
    return GovernedArtifactRecord(
        schema_version="1.0",
        cache_key=identity.cache_key,
        identity=identity,
        raw_response={"response_id": "provider-1", "text": "raw"},
        parsed_output={"components": []},
        trace={"latency_ms": 10},
        validation={"status": "PASSED"},
    )


def test_cache_hit_prevents_provider_execution(tmp_path):
    store = FilesystemGovernedArtifactStore(tmp_path)
    identity = _identity()
    calls = []

    first, first_hit = store.get_or_execute(
        identity,
        lambda: calls.append("provider") or _record(identity),
    )
    second, second_hit = store.get_or_execute(
        identity,
        lambda: calls.append("provider") or _record(identity),
    )

    assert first == second
    assert first_hit is False
    assert second_hit is True
    assert calls == ["provider"]


def test_identity_change_creates_cache_miss(tmp_path):
    store = FilesystemGovernedArtifactStore(tmp_path)
    original = _identity()
    changed = _identity(prompt_version="renderer-v2")
    calls = []

    store.get_or_execute(original, lambda: calls.append("v1") or _record(original))
    _, hit = store.get_or_execute(changed, lambda: calls.append("v2") or _record(changed))

    assert hit is False
    assert calls == ["v1", "v2"]
    assert original.cache_key != changed.cache_key


def test_immutable_artifact_cannot_be_overwritten(tmp_path):
    store = FilesystemGovernedArtifactStore(tmp_path)
    identity = _identity()
    store.save(_record(identity))
    changed = GovernedArtifactRecord(
        schema_version="1.0",
        cache_key=identity.cache_key,
        identity=identity,
        raw_response={"response_id": "different"},
        parsed_output={"components": []},
        trace={"latency_ms": 10},
        validation={"status": "PASSED"},
    )

    try:
        store.save(changed)
    except GovernedArtifactStoreError as exc:
        assert "immutable artifact" in str(exc)
    else:
        raise AssertionError("immutable overwrite must fail")
