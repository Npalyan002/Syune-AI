import io
import json
import urllib.error

import pytest

from benchmarks.phase28_provider import BudgetFuse, CallLedger, ModelRequest, ModelResponse, OpenAIResponsesProvider, cost_preflight, execute_once, logical_call_id, smoke_request


class FakeHTTP:
    status = 200
    headers = {"x-request-id": "req-header"}
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def read(self): return json.dumps(self.payload).encode()


def response_payload(model="gpt-5.4-mini-2026-03-17"):
    return {"id": "resp-1", "model": model, "output_text": '{"status":"OK"}', "usage": {"input_tokens": 10, "output_tokens": 3}}


def test_serialization_and_parse_and_usage():
    provider = OpenAIResponsesProvider("secret", opener=lambda *_args, **_kw: FakeHTTP(response_payload()), sleeper=lambda _: None)
    req = smoke_request(); payload = provider.payload(req)
    assert payload["model"] == req.model and payload["temperature"] == .2 and payload["store"] is False
    result = provider.execute(req)
    assert result.status == "COMPLETED" and result.output == {"status": "OK"}
    assert result.input_tokens == 10 and result.output_tokens == 3 and result.request_id == "resp-1"


def test_401_is_not_retried():
    calls = []
    def opener(*_args, **_kw):
        calls.append(1); raise urllib.error.HTTPError("url", 401, "no", {}, io.BytesIO(b'{"error":"bad key"}'))
    result = OpenAIResponsesProvider("secret", opener=opener, sleeper=lambda _: None).execute(smoke_request())
    assert result.status == "FAILED" and result.retry_count == 0 and len(calls) == 1


def test_429_retries_bounded_and_semantic_output_does_not_retry():
    calls = []
    def opener(*_args, **_kw):
        calls.append(1)
        if len(calls) < 3: raise urllib.error.HTTPError("url", 429, "rate", {}, io.BytesIO(b'{}'))
        return FakeHTTP(response_payload())
    result = OpenAIResponsesProvider("secret", opener=opener, sleeper=lambda _: None).execute(smoke_request())
    assert result.status == "COMPLETED" and result.retry_count == 2 and len(calls) == 3
    bad = response_payload(); bad["output_text"] = "wrong but valid provider response"
    calls.clear(); result = OpenAIResponsesProvider("secret", opener=lambda *_a, **_k: (calls.append(1) or FakeHTTP(bad)), sleeper=lambda _: None).execute(smoke_request())
    assert result.status == "COMPLETED" and result.output is None and len(calls) == 1


def test_resume_and_secret_hygiene(tmp_path):
    class FakeProvider:
        calls = 0
        def execute(self, request):
            self.calls += 1
            return ModelResponse(request.logical_call_id, "openai", request.model, request.model, "r", 200, "now", 1, 0, "hash", {"status":"OK"}, '{"status":"OK"}', 1, 1, .00001, "COMPLETED")
    ledger = CallLedger(tmp_path / "real.jsonl"); provider = FakeProvider(); budget = BudgetFuse(10, 1000, 1000, 1)
    execute_once(provider, ledger, budget, smoke_request()); _, resumed = execute_once(provider, ledger, budget, smoke_request())
    assert resumed and provider.calls == 1 and "secret" not in ledger.path.read_text()


def test_budget_fuse_and_stable_identity():
    budget = BudgetFuse(0, 0, 0, 0)
    with pytest.raises(RuntimeError, match="BUDGET_FUSE"): budget.reserve()
    assert logical_call_id("MODEL_ONLY", 0, "T1", 1, "DECISION") == logical_call_id("MODEL_ONLY", 0, "T1", 1, "DECISION")
    estimate = cost_preflight()
    assert estimate["expected_fits"] and not estimate["worst_case_fits"]
    assert estimate["expected_input_tokens"] < estimate["hard_cap"]["input_tokens"]


def test_budget_fuse_precedes_retry(tmp_path):
    calls = []
    def opener(*_args, **_kw):
        calls.append(1)
        raise urllib.error.HTTPError("url", 429, "rate", {}, io.BytesIO(b'{}'))
    provider = OpenAIResponsesProvider("secret", opener=opener, sleeper=lambda _: None)
    ledger = CallLedger(tmp_path / "phase28a-retry-fuse.jsonl")
    budget = BudgetFuse(1, 10000, 1000, 1)
    with pytest.raises(RuntimeError, match="BUDGET_FUSE"):
        execute_once(provider, ledger, budget, smoke_request())
    assert len(calls) == 1
