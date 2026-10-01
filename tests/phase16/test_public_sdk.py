from dataclasses import replace
import json

import pytest

import syune
from syune import (
    CognitiveRequest, CouncilRequest, PlanRequest, RecallRequest, RuntimeMode, StudyRequest,
    Syune, SyuneError, TypedId, canonical_json, negotiate_version,
)
from syune.product.config import load_config
from syune.product.state import initialize_state


def open_fixture(tmp_path, monkeypatch, mode=RuntimeMode.TEST):
    library = (tmp_path / "library").resolve(); library.mkdir()
    state = (tmp_path / "state").resolve()
    monkeypatch.setenv("SYUNE_STUDY_ROOTS", str(library))
    initialize_state(load_config(cli_state_root=state))
    return library, Syune.open(state_root=state, mode=mode)


def test_public_sdk_end_to_end_and_correlation(tmp_path, monkeypatch):
    library, brain = open_fixture(tmp_path, monkeypatch)
    source = library / "fixture.md"
    source.write_text("# Reliable systems\nEvidence requires provenance and explicit review.", encoding="utf-8")
    with brain:
        assert brain.health(correlation_id="phase16").correlation_id == "phase16"
        assert brain.status().data["state_schema"] == 1
        assert brain.handshake(["1"]).selected_version == "1"
        assert brain.capabilities().capabilities[-1].operation == "execute_approved"
        studied = brain.study(StudyRequest(str(source), "study-correlation"))
        assert studied.correlation_id == "study-correlation"
        assert studied.data["materialization"] == "MATERIALIZED"
        status = brain.source_status(source_id=TypedId.parse(studied.data["source_id"]))
        assert status.data["known"]
        memory = brain.memory_get(studied.data["source_id"])
        assert memory.data["entity_type"] == "Source"
        recall = brain.recall(RecallRequest(cue="provenance review", correlation_id="flow-1"))
        assert recall.correlation_id == "flow-1" and recall.data["candidates"]
        cognition = brain.cognize(CognitiveRequest(cue="provenance review", correlation_id="flow-1"))
        assert cognition.correlation_id == "flow-1"
        council = brain.council(CouncilRequest("assess provenance review", ("GENERAL", "RESEARCH"),
                                               correlation_id="flow-1"))
        assert council.data["agreement_meaning"].endswith("truth probability")
        plan = brain.plan(PlanRequest("review the provenance evidence", ("review is documented",), "flow-1"))
        assert plan.data["execution_authority"] is False
        assert plan.data["approval_does_not_execute"] is True


def test_public_errors_modes_versions_and_exports(tmp_path, monkeypatch):
    library, brain = open_fixture(tmp_path, monkeypatch, RuntimeMode.READ_ONLY)
    source = library / "note.txt"; source.write_text("safe", encoding="utf-8")
    with brain:
        with pytest.raises(SyuneError) as blocked:
            brain.study(str(source))
        assert blocked.value.code == "BLOCKED" and blocked.value.blocked
        with pytest.raises(SyuneError) as missing:
            brain.memory_get("ClaimId:00000000-0000-0000-0000-000000000000")
        assert missing.value.code == "RECORD_NOT_FOUND"
        assert {c.operation: c.available for c in brain.capabilities().capabilities}["study"] is False
    with pytest.raises(SyuneError) as unsupported:
        negotiate_version(["2"])
    assert unsupported.value.code == "UNSUPPORTED_VERSION"
    assert "SQLiteMemoryRepository" not in syune.__all__
    assert "execute_approved" not in dir(Syune)


def test_canonical_serialization_and_additive_request_fields():
    request = RecallRequest(cue="x", correlation_id="c")
    assert canonical_json(request) == canonical_json(request)
    decoded = json.loads(canonical_json(request))
    decoded["future_optional"] = "ignored-by-v1-host"
    known = {name: value for name, value in decoded.items() if name in RecallRequest.__dataclass_fields__}
    assert RecallRequest(**known).cue == "x"


def test_v1_fixture_and_schemas_are_readable(tmp_path, monkeypatch):
    _, brain = open_fixture(tmp_path, monkeypatch)
    with brain:
        handshake=brain.handshake(["1"])
    fixture=json.loads((__import__("pathlib").Path(__file__).parents[1]/"fixtures/public_v1_handshake.json").read_text())
    actual={"autonomy_level":handshake.autonomy_level,"package_version":handshake.package_version,
            "public_api_version":handshake.selected_version,"runtime_mode":handshake.runtime_mode.value,
            "state_schema":handshake.state_schema,"supported_public_api_versions":list(handshake.supported_public_api_versions)}
    assert actual==fixture
    schema_root=__import__("pathlib").Path(__file__).parents[2]/"contracts/schemas/public/v1"
    assert all(json.loads(path.read_text())["$schema"].endswith("2020-12/schema") for path in schema_root.glob("*.json"))
