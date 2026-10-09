from datetime import datetime, timezone
from uuid import UUID

import pytest

from syune import RecallRequest as PublicRecallRequest, Syune
from syune.core import AssociationId, ConceptId, Confidence, ProvenanceId, SourceId
from syune.memory import (
    Association, Concept, Provenance, SecurityEnvelope, Sensitivity, Source,
)
from syune.product.config import load_config
from syune.product.runtime import SyuneRuntime
from syune.product.state import initialize_state


def configured_state(tmp_path, max_results, *, learning=False):
    state = (tmp_path / f"state-{max_results}-{learning}").resolve()
    config_path = (tmp_path / f"config-{max_results}-{learning}.toml").resolve()
    config_path.write_text(
        f'[retrieval]\nmax_results={max_results}\n[features]\nlearning={str(learning).lower()}\n',
        encoding="utf-8",
    )
    config = load_config(cli_state_root=state, cli_config=config_path)
    initialize_state(config)
    return state, config_path, config


def populate_candidates(runtime, count=100, *, restricted=0):
    at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    source_id = SourceId(UUID(int=1))
    provenance = Provenance(ProvenanceId(UUID(int=2)), source_id, at)
    runtime.memory.put(Source(source_id, "test", "phase02a", at))
    concepts = []
    for offset in range(count):
        security = SecurityEnvelope(sensitivity=Sensitivity.PUBLIC)
        if offset < restricted:
            security = SecurityEnvelope(
                owner="user:owner", sensitivity=Sensitivity.CONFIDENTIAL
            )
        concept = Concept(
            ConceptId(UUID(int=100 + offset)), "phase02a eligible candidate",
            provenance, Confidence(0.5), at, security=security,
        )
        runtime.memory.put(concept)
        concepts.append(concept)
    # The native lexical budget seeds 32 candidates. Connect those seeds to the
    # remaining eligible candidates so ordinary associative retrieval reaches 100.
    edge_number = 10_000
    for tail_index in range(32, count):
        seed_index = (tail_index - 32) % 32
        runtime.memory.add_association(Association(
            AssociationId(UUID(int=edge_number)), concepts[seed_index].id,
            concepts[tail_index].id, "associated_with", provenance,
            Confidence(0.8), at, 1.0,
        ))
        edge_number += 1
    runtime.index.sync()


def ranked_ids(result):
    return [(item["entity_id"], item["rank"], item["score"]) for item in result.data["candidates"]]


def test_product_default_remains_16_and_invalid_values_fail(tmp_path):
    assert load_config(cli_state_root=tmp_path.resolve()).retrieval.max_results == 16
    for value in (0, 101):
        path = (tmp_path / f"invalid-{value}.toml").resolve()
        path.write_text(f"[retrieval]\nmax_results={value}\n", encoding="utf-8")
        with pytest.raises(ValueError, match="1..100"):
            load_config(cli_state_root=tmp_path.resolve(), cli_config=path)


@pytest.mark.parametrize("learning", [False, True])
def test_runtime_wires_product_retrieval_config_in_both_paths(tmp_path, learning):
    _, _, config = configured_state(tmp_path, 100, learning=learning)
    with SyuneRuntime.open(config) as runtime:
        assert runtime.retrieval.config.max_results == 100
        assert runtime.retrieval.config.working_memory_capacity == 8


@pytest.mark.parametrize("limit", [16, 32, 100])
def test_public_sdk_returns_configured_native_candidates(tmp_path, limit):
    state, config_path, config = configured_state(tmp_path, limit)
    with SyuneRuntime.open(config) as runtime:
        populate_candidates(runtime)
    with Syune.open(state_root=state, config=config_path) as client:
        result = client.recall(PublicRecallRequest(
            cue="phase02a eligible candidate", max_results=100
        ))
        assert len(result.data["candidates"]) == limit
        assert len(result.data["working_memory"]) <= 8


def test_ranking_access_isolation_and_restart_are_deterministic(tmp_path):
    state, config_path, config = configured_state(tmp_path, 100)
    with SyuneRuntime.open(config) as runtime:
        populate_candidates(runtime, restricted=7)
    request = PublicRecallRequest(
        cue="phase02a eligible candidate", max_results=100, user_id="reader"
    )
    with Syune.open(state_root=state, config=config_path) as first_client:
        first = first_client.recall(request)
        first_ranking = ranked_ids(first)
        assert len(first_ranking) == 93
        assert [rank for _, rank, _ in first_ranking] == list(range(1, 94))
    with Syune.open(state_root=state, config=config_path) as second_client:
        second_ranking = ranked_ids(second_client.recall(request))
    assert second_ranking == first_ranking
