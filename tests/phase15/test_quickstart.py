from __future__ import annotations

import json
from pathlib import Path

from syune.product.config import load_config
from syune.product.state import initialize_state
from syune.quickstart import run


def _records(output: str) -> list[dict]:
    return [json.loads(line) for line in output.splitlines()]


def test_fresh_default_initializes_without_preexisting_state(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("syune.quickstart.tempfile.gettempdir", lambda: str(tmp_path))
    expected = tmp_path / "syune-quickstart"
    assert not expected.exists()

    assert run([]) == 0

    records = _records(capsys.readouterr().out)
    assert records[0]["created"] is True
    assert Path(records[0]["state_root"]) == expected.resolve()
    assert "memory_id" in records[1]["remember"]
    assert records[2]["context"]["items"][0]["provenance"]
    assert records[-1] == {"closed": True}


def test_relative_state_root_is_normalized_and_reused(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    relative = Path("relative-test-state")

    assert run(["--state-root", str(relative)]) == 0
    first = _records(capsys.readouterr().out)
    assert first[0]["created"] is True
    assert Path(first[0]["state_root"]) == (tmp_path / relative).resolve()

    assert run(["--state-root", str(relative)]) == 0
    second = _records(capsys.readouterr().out)
    assert second[0]["created"] is False
    assert second[-1] == {"closed": True}


def test_absolute_preinitialized_state_is_reused(tmp_path, capsys):
    state = (tmp_path / "absolute-state").resolve()
    initialize_state(load_config(cli_state_root=state))

    assert run(["--state-root", str(state)]) == 0

    records = _records(capsys.readouterr().out)
    assert records[0]["created"] is False
    assert Path(records[0]["state_root"]) == state


def test_expected_state_error_is_actionable(tmp_path, capsys):
    state = (tmp_path / "unsafe-existing-directory").resolve()
    state.mkdir()
    (state / "unexpected.txt").write_text("do not overwrite", encoding="utf-8")

    assert run(["--state-root", str(state)]) == 2

    captured = capsys.readouterr()
    assert not captured.out
    assert captured.err.startswith("error: state root contains unknown entries")
