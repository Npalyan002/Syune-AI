import json
from pathlib import Path

from benchmarks.phase28r import build_dataset
from benchmarks.phase28r1_execution import (CanonicalPhase28RRunner,
    DeterministicFakeProvider, ExecutionStore, HARD_CAPS, ModelResponse)


def test_provider_choice_cannot_change_canonical_request(tmp_path):
    tasks, truth, _ = build_dataset()
    a = CanonicalPhase28RRunner(DeterministicFakeProvider(), tmp_path / "a", tasks[:1], truth[:1])
    b = CanonicalPhase28RRunner(DeterministicFakeProvider(), tmp_path / "b", tasks[:1], truth[:1])
    try:
        assert a.request_hash(tasks[0], "MODEL_ONLY") == b.request_hash(tasks[0], "MODEL_ONLY")
    finally:
        a.close(); b.close()


def test_evidence_first_exactly_once_and_budget(tmp_path):
    tasks, truth, _ = build_dataset(); provider = DeterministicFakeProvider()
    runner = CanonicalPhase28RRunner(provider, tmp_path / "run", tasks[:1], truth[:1])
    try:
        req = runner._decision_request(tasks[0], "MODEL_ONLY")
        one, replay1 = runner.store.execute(provider, req)
        two, replay2 = runner.store.execute(provider, req)
        assert not replay1 and replay2 and provider.calls == 1 and one == two
        assert runner.store.usage()["calls"] == 1
        assert runner.store.response(req.logical_call_id) is not None
    finally: runner.close()


def test_non_treatment_smoke_uses_canonical_evidence_and_scorer_paths(tmp_path):
    runner = CanonicalPhase28RRunner(DeterministicFakeProvider(), tmp_path / "smoke", treatment_mode=False)
    try:
        result = runner.smoke()
        assert result["calls"] == 3 and result["parsing"] and result["evidence_persistence"]
        roles = {x[0] for x in runner.store.db.execute("select call_role from evidence")}
        assert roles == {"DECISION", "SEMANTIC_SCORER", "RUBRIC_SCORER"}
    finally: runner.close()


def test_small_resume_has_no_duplicate_calls_or_results(tmp_path):
    tasks, truth, _ = build_dataset(); tasks, truth = tasks[:2], truth[:2]
    provider = DeterministicFakeProvider(); out = tmp_path / "resume"
    first = CanonicalPhase28RRunner(provider, out, tasks, truth)
    first.run_treatments(); usage = first.store.usage(); count = len(first.store.all_results()); first.close()
    second = CanonicalPhase28RRunner(provider, out, tasks, truth)
    second.run_treatments()
    assert second.store.usage() == usage and len(second.store.all_results()) == count == 12
    second.close()


def test_fault_boundaries_preserve_one_committed_logical_call(tmp_path):
    tasks, truth, _ = build_dataset(); task = tasks[0]
    for boundary in ("before_provider_call", "after_provider_response", "after_evidence_persistence"):
        fired = set()
        def inject(stage, target=boundary):
            if stage == target and stage not in fired:
                fired.add(stage); raise RuntimeError("INJECTED_CRASH")
        out = tmp_path / boundary; provider = DeterministicFakeProvider()
        runner = CanonicalPhase28RRunner(provider, out, tasks[:1], truth[:1], failure_injector=inject)
        req = runner._decision_request(task, "MODEL_ONLY")
        try:
            try: runner.store.execute(provider, req, runner._stage)
            except RuntimeError as exc: assert str(exc) == "INJECTED_CRASH"
        finally: runner.close()
        resumed = CanonicalPhase28RRunner(provider, out, tasks[:1], truth[:1])
        resumed.store.execute(provider, req)
        assert resumed.store.db.execute("select count(*) from evidence where logical_call_id=?", (req.logical_call_id,)).fetchone()[0] == 1
        resumed.close()
