import json
import sqlite3

import pytest

from benchmarks.phase28r import DECISION_SCHEMA, MODEL, TEMPERATURE, build_dataset
from benchmarks.phase28r2_execution import (CanonicalPhase28R2Runner,
    DeterministicFakeProvider, ExecutionStore, MAX_ATTEMPTS, ModelRequest,
    TerminalInfrastructureFailure, _request)


def decision_request(call_id="L1"):
    return _request(call_id, "DECISION",
        "AVAILABLE ACTIONS\n- OK: diagnostic\nAUTHORIZED ORGANIZATIONAL EXPERIENCE\nNone",
        DECISION_SCHEMA, {"treatment":"MODEL_ONLY","epoch":0,"task_id":"DEV","agent_id":"dev"}, 180)


@pytest.mark.parametrize("kind,expected", [
    ("TRUNCATED_OUTPUT","TRUNCATED_OUTPUT"),("INVALID_JSON","INVALID_JSON"),
    ("SCHEMA_INVALID","SCHEMA_INVALID"),("EMPTY_OUTPUT","EMPTY_OUTPUT"),
    ("UNEXPECTED_FORMAT","INVALID_JSON")])
def test_parse_failures_are_durable_classified_and_eventually_succeed(tmp_path, kind, expected):
    req=decision_request();provider=DeterministicFakeProvider({req.logical_call_id:[kind,"VALID"]});store=ExecutionStore(tmp_path/"x.sqlite3")
    try:
        response,replayed=store.execute(provider,req)
        assert not replayed and response.retry_count==1
        attempts=store.db.execute("select * from provider_attempts order by attempt_number").fetchall()
        assert len(attempts)==2 and attempts[0]["raw_persistence_status"]=="PERSISTED"
        assert attempts[0]["failure_class"]==expected and attempts[1]["terminal_state"]=="COMMITTED"
    finally:store.close()


def test_repeated_truncation_is_finite_terminal(tmp_path):
    req=decision_request();provider=DeterministicFakeProvider({req.logical_call_id:["TRUNCATED_OUTPUT"]*3});store=ExecutionStore(tmp_path/"x.sqlite3")
    try:
        with pytest.raises(TerminalInfrastructureFailure,match="PARSE_FAILURE_TERMINAL"):
            store.execute(provider,req)
        assert provider.calls==MAX_ATTEMPTS==3
        assert store.db.execute("select terminal_state from logical_calls").fetchone()[0]=="PARSE_FAILURE_TERMINAL"
    finally:store.close()


def test_mixed_http_truncation_valid_obeys_single_attempt_budget(tmp_path):
    req=decision_request();provider=DeterministicFakeProvider({req.logical_call_id:["HTTP_500","TRUNCATED_OUTPUT","VALID"]});store=ExecutionStore(tmp_path/"x.sqlite3")
    try:
        response,_=store.execute(provider,req)
        assert response.retry_count==2 and store.usage()["calls"]==3
        states=[x[0] for x in store.db.execute("select terminal_state from provider_attempts order by attempt_number")]
        assert states==["HTTP_TRANSIENT_FAILURE","PARSE_FAILURE_RETRYABLE","COMMITTED"]
    finally:store.close()


def test_eventual_success_commits_once_and_preserves_two_attempts(tmp_path):
    req=decision_request();provider=DeterministicFakeProvider({req.logical_call_id:["TRUNCATED_OUTPUT","VALID"]});store=ExecutionStore(tmp_path/"x.sqlite3")
    try:
        one,replay1=store.execute(provider,req);two,replay2=store.execute(provider,req)
        assert not replay1 and replay2 and one.parsed_content==two.parsed_content and provider.calls==2
        assert store.db.execute("select count(*) from logical_calls where terminal_state='COMMITTED'").fetchone()[0]==1
    finally:store.close()


def test_raw_body_and_usage_are_persisted_before_parse(tmp_path):
    req=decision_request();provider=DeterministicFakeProvider({req.logical_call_id:["INVALID_JSON","VALID"]});store=ExecutionStore(tmp_path/"x.sqlite3")
    try:
        store.execute(provider,req)
        row=store.db.execute("select * from provider_attempts where attempt_number=1").fetchone()
        assert row["raw_body"] and row["usage_status"]=="MEASURED" and row["input_tokens"]>0
        assert "authorization" not in row["sanitized_headers_json"].lower()
    finally:store.close()


def test_started_attempt_becomes_remote_ambiguity_then_retries(tmp_path):
    req=decision_request();db=tmp_path/"x.sqlite3";store=ExecutionStore(db);store._start_attempt(req);store.close()
    store=ExecutionStore(db)
    try:
        assert store.db.execute("select terminal_state from provider_attempts").fetchone()[0]=="REMOTE_COMPLETION_AMBIGUOUS"
        response,_=store.execute(DeterministicFakeProvider(),req)
        assert response.retry_count==1
        assert store.reliability()["failure_classes"]["REMOTE_COMPLETION_AMBIGUOUS"]==1
    finally:store.close()


@pytest.mark.parametrize("boundary", ["before_http_request","after_http_response","after_raw_persistence","during_parse","after_parse","after_semantic_result_persistence"])
def test_crash_windows_resume_deterministically(tmp_path,boundary):
    req=decision_request();db=tmp_path/f"{boundary}.sqlite3";fired=set()
    def inject(stage):
        if stage==boundary and stage not in fired:fired.add(stage);raise RuntimeError("INJECTED_CRASH")
    store=ExecutionStore(db)
    with pytest.raises(RuntimeError,match="INJECTED_CRASH"):store.execute(DeterministicFakeProvider(),req,inject)
    store.close();store=ExecutionStore(db)
    try:
        response,_=store.execute(DeterministicFakeProvider(),req)
        assert response.parsed_content["selected_action"]=="OK"
        assert store.db.execute("select count(*) from logical_calls where terminal_state='COMMITTED'").fetchone()[0]==1
    finally:store.close()


@pytest.mark.parametrize("boundary", ["after_learning","before_checkpoint","after_scorer"])
def test_orchestration_crash_windows_resume_without_duplicate_results(tmp_path,boundary):
    tasks,truth,_=build_dataset();out=tmp_path/boundary;fired=set()
    def inject(stage):
        if stage==boundary and stage not in fired:fired.add(stage);raise RuntimeError("INJECTED_CRASH")
    runner=CanonicalPhase28R2Runner(DeterministicFakeProvider(),out,tasks[:1],truth[:1],failure_injector=inject)
    try:
        with pytest.raises(RuntimeError,match="INJECTED_CRASH"):
            if boundary=="after_scorer":runner.run_treatments();runner.run_scorers()
            else:runner.run_treatments()
    finally:runner.close()
    resumed=CanonicalPhase28R2Runner(DeterministicFakeProvider(),out,tasks[:1],truth[:1])
    try:
        resumed.run_treatments();resumed.run_scorers()
        assert len(resumed.store.all_results())==6
        assert resumed.store.db.execute("select count(*) from results").fetchone()[0]==6
    finally:resumed.close()


def test_non_treatment_smoke_is_three_calls(tmp_path):
    runner=CanonicalPhase28R2Runner(DeterministicFakeProvider(),tmp_path/"smoke",treatment_mode=False)
    try:
        result=runner.smoke();assert result["calls"]==3 and result["raw_response_first"] and result["parsing"]
    finally:runner.close()
