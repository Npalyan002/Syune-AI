from datetime import datetime, timedelta, timezone

import pytest

from syune import RecallRequest, RememberRequest, Syune, SyuneError, TypedId
from syune.product.config import load_config
from syune.product.state import initialize_state


def open_client(tmp_path):
    state = (tmp_path / "state").resolve()
    initialize_state(load_config(cli_state_root=state))
    return state, Syune.open(state_root=state)


def memory_fields(client, typed_id):
    return client.memory_get(TypedId.parse(typed_id)).data["fields"]


def test_source_timestamp_is_normalized_and_ingestion_fields_remain_distinct(tmp_path):
    state, client = open_client(tmp_path)
    with client:
        result = client.remember(RememberRequest(
            "offset event marker", observed_at="2026-05-01T14:30:00-04:00"
        ))
        observation = memory_fields(client, result.data["memory_id"])
        source = memory_fields(client, result.data["source_id"])
        assert observation["observed_at"] == "2026-05-01T18:30:00Z"
        assert result.data["observed_at"] == observation["observed_at"]
        assert observation["created_at"] == result.data["created_at"]
        assert observation["observed_at"] != observation["created_at"]
        assert source["registered_at"] == observation["created_at"]
        assert observation["provenance"]["created_at"] == observation["created_at"]
        assert observation["truth"]["recorded_at"] is None
        assert observation["truth"]["valid_from"] is None

    with Syune.open(state_root=state) as restarted:
        restored = memory_fields(restarted, result.data["memory_id"])
        assert restored["observed_at"] == "2026-05-01T18:30:00Z"
        assert restored["created_at"] == observation["created_at"]


def test_missing_timestamp_retains_ingestion_time_behavior(tmp_path):
    _, client = open_client(tmp_path)
    with client:
        result = client.remember(RememberRequest("legacy timestamp behavior"))
        observation = memory_fields(client, result.data["memory_id"])
        assert observation["observed_at"] == observation["created_at"]
        assert result.data["observed_at"] == result.data["created_at"]


@pytest.mark.parametrize("value", ["2026-05-01T14:30:00", "not-a-timestamp", "", 123])
def test_naive_malformed_and_non_string_timestamps_are_rejected(tmp_path, value):
    _, client = open_client(tmp_path)
    with client, pytest.raises(SyuneError) as error:
        client.remember(RememberRequest("invalid timestamp", observed_at=value))
    assert error.value.code == "INVALID_REQUEST"


def test_future_event_timestamp_is_preserved_without_becoming_validity(tmp_path):
    _, client = open_client(tmp_path)
    future = datetime.now(timezone.utc) + timedelta(days=3650)
    with client:
        result = client.remember(RememberRequest(
            "future event marker", observed_at=future.isoformat()
        ))
        observation = memory_fields(client, result.data["memory_id"])
        assert observation["observed_at"] == future.isoformat().replace("+00:00", "Z")
        assert observation["truth"]["valid_from"] is None
        recalled = client.recall(RecallRequest(cue="future event marker"))
        assert any(item["entity_type"] == "Observation" for item in recalled.data["candidates"])
