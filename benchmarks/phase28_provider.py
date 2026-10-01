"""Provider-neutral, crash-safe real-model bridge for Phase 28A.

This module contains no treatment semantics. It serializes already-frozen model
requests, records provider telemetry without credentials, retries only transient
infrastructure failures, and deduplicates completed logical calls on resume.
"""
from __future__ import annotations

import hashlib
import json
import socket
import threading
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

PROVIDER = "openai"
MODEL = "gpt-5.4-mini-2026-03-17"
INPUT_PRICE = .75 / 1_000_000
OUTPUT_PRICE = 4.50 / 1_000_000
TRANSIENT_HTTP = frozenset({408, 409, 429, 500, 502, 503, 504})
RETRY_DELAYS_SECONDS = (1.0, 2.0)
CALL_ROLES = frozenset({"DECISION", "QUERY_TIME_SYNTHESIS", "KNOWLEDGE_CONSTRUCTION", "VERIFICATION", "MAINTENANCE", "SCORER", "SMOKE"})


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


@dataclass(frozen=True)
class ModelRequest:
    logical_call_id: str
    model: str
    input: list[dict[str, Any]]
    temperature: float
    response_schema: dict[str, Any]
    response_name: str
    metadata: dict[str, Any]
    max_output_tokens: int = 500

    def __post_init__(self) -> None:
        if self.model != MODEL:
            raise ValueError("model differs from frozen Phase 28 model")
        if self.temperature != .2:
            raise ValueError("temperature differs from frozen Phase 28 setting")
        if self.metadata.get("call_role") not in CALL_ROLES:
            raise ValueError("unknown call role")


@dataclass(frozen=True)
class ModelResponse:
    logical_call_id: str
    provider: str
    requested_model: str
    resolved_model: str | None
    request_id: str | None
    http_status: int | None
    timestamp: str
    latency_ms: float
    retry_count: int
    input_hash: str
    output: Any
    output_text: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    status: str
    error: dict[str, Any] | None = None


class ModelProvider(Protocol):
    def execute(self, request: ModelRequest) -> ModelResponse: ...


class ProviderError(RuntimeError):
    def __init__(self, status: int | None, kind: str, message: str, *, transient: bool):
        super().__init__(message); self.status = status; self.kind = kind; self.transient = transient


class OpenAIResponsesProvider:
    def __init__(self, api_key: str, *, opener: Callable[..., Any] = urllib.request.urlopen,
                 sleeper: Callable[[float], None] = time.sleep, timeout: float = 180.0):
        if not api_key: raise ValueError("credential missing")
        self._api_key, self._opener, self._sleeper, self._timeout = api_key, opener, sleeper, timeout

    @staticmethod
    def payload(request: ModelRequest) -> dict[str, Any]:
        return {"model": request.model, "input": request.input, "temperature": request.temperature,
                "reasoning": {"effort": "none"}, "max_output_tokens": request.max_output_tokens,
                "store": False, "service_tier": "default",
                "text": {"format": {"type": "json_schema", "name": request.response_name,
                                      "strict": True, "schema": request.response_schema}}}

    @staticmethod
    def _parse(payload: dict[str, Any]) -> tuple[Any, str]:
        text = payload.get("output_text") or "".join(
            part.get("text", "") for item in payload.get("output", [])
            for part in item.get("content", []) if part.get("type") == "output_text")
        try: return json.loads(text), text
        except (TypeError, json.JSONDecodeError): return None, text

    def _once(self, request: ModelRequest) -> tuple[int, dict[str, Any], str | None, float]:
        body = canonical(self.payload(request)).encode("utf-8")
        wire = urllib.request.Request("https://api.openai.com/v1/responses", data=body, method="POST",
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json",
                     "X-Client-Request-Id": request.logical_call_id})
        started = time.perf_counter()
        try:
            with self._opener(wire, timeout=self._timeout) as response:
                raw = response.read().decode("utf-8")
                return response.status, json.loads(raw), response.headers.get("x-request-id"), (time.perf_counter()-started)*1000
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try: detail = json.loads(raw)
            except json.JSONDecodeError: detail = {"message": raw[:1000]}
            raise ProviderError(exc.code, "http", canonical(detail), transient=exc.code in TRANSIENT_HTTP) from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError) as exc:
            raise ProviderError(None, "transport", str(exc), transient=True) from exc

    def execute(self, request: ModelRequest, *, before_attempt: Callable[[], None] | None = None) -> ModelResponse:
        input_hash = sha256_text(canonical(self.payload(request)))
        retries = 0
        while True:
            if before_attempt is not None:
                before_attempt()
            started = datetime.now(timezone.utc).isoformat()
            try:
                status, raw, header_id, latency = self._once(request)
                output, output_text = self._parse(raw); usage = raw.get("usage") or {}
                resolved = raw.get("model")
                if resolved != request.model:
                    raise ProviderError(status, "model_mismatch", f"requested {request.model}, resolved {resolved}", transient=False)
                it, ot = int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0))
                return ModelResponse(request.logical_call_id, PROVIDER, request.model, resolved,
                    raw.get("id") or header_id, status, started, latency, retries, input_hash, output, output_text,
                    it, ot, it*INPUT_PRICE + ot*OUTPUT_PRICE, "COMPLETED", None)
            except ProviderError as exc:
                if not exc.transient or retries >= len(RETRY_DELAYS_SECONDS):
                    return ModelResponse(request.logical_call_id, PROVIDER, request.model, None, None,
                        exc.status, started, 0.0, retries, input_hash, None, "", 0, 0, 0.0, "FAILED",
                        {"kind": exc.kind, "message": str(exc), "transient": exc.transient})
                self._sleeper(RETRY_DELAYS_SECONDS[retries]); retries += 1


class CallLedger:
    """Append-only JSONL ledger with stable logical-call duplicate protection."""
    def __init__(self, path: Path):
        self.path = path; path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._completed: dict[str, dict[str, Any]] = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    if row.get("status") == "COMPLETED": self._completed[row["logical_call_id"]] = row

    def completed(self, logical_call_id: str) -> dict[str, Any] | None:
        return self._completed.get(logical_call_id)

    def append(self, request: ModelRequest, response: ModelResponse) -> None:
        row = asdict(response) | {k: request.metadata.get(k) for k in
            ("condition", "epoch", "task_id", "agent_id", "department", "call_role", "trial")}
        # Never serialize request headers or credentials. Input is represented only by its hash.
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, sort_keys=True) + "\n"); handle.flush()
            if response.status == "COMPLETED": self._completed[response.logical_call_id] = row

    def usage(self) -> dict[str, float]:
        rows=list(self._completed.values())
        return {"calls":len(rows),"input_tokens":sum(int(x.get("input_tokens",0)) for x in rows),
                "output_tokens":sum(int(x.get("output_tokens",0)) for x in rows),
                "cost_usd":sum(float(x.get("cost_usd",0)) for x in rows)}


@dataclass
class BudgetFuse:
    hard_calls: int
    hard_input_tokens: int
    hard_output_tokens: int
    hard_cost_usd: float
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    def reserve(self, *, calls: int = 1, input_tokens: int = 0, output_tokens: int = 0) -> None:
        projected_cost = self.cost_usd + input_tokens*INPUT_PRICE + output_tokens*OUTPUT_PRICE
        if (self.calls + calls > self.hard_calls or self.input_tokens + input_tokens > self.hard_input_tokens or
                self.output_tokens + output_tokens > self.hard_output_tokens or projected_cost > self.hard_cost_usd):
            raise RuntimeError("BUDGET_FUSE")

    def before_attempt(self, *, estimated_input_tokens: int, max_output_tokens: int) -> None:
        """Fail before an initial call or retry that risks any amended hard cap."""
        self.reserve(calls=1, input_tokens=estimated_input_tokens, output_tokens=max_output_tokens)
        self.calls += 1

    def record(self, response: ModelResponse) -> None:
        self.input_tokens += response.input_tokens; self.output_tokens += response.output_tokens; self.cost_usd += response.cost_usd


def execute_once(provider: ModelProvider, ledger: CallLedger, budget: BudgetFuse, request: ModelRequest) -> tuple[dict[str, Any], bool]:
    prior = ledger.completed(request.logical_call_id)
    if prior is not None: return prior, True
    estimated_input = max(1, len(canonical(OpenAIResponsesProvider.payload(request))) // 4)
    if isinstance(provider, OpenAIResponsesProvider):
        response = provider.execute(request, before_attempt=lambda: budget.before_attempt(
            estimated_input_tokens=estimated_input, max_output_tokens=request.max_output_tokens))
    else:
        budget.before_attempt(estimated_input_tokens=estimated_input, max_output_tokens=request.max_output_tokens)
        response = provider.execute(request)
    ledger.append(request, response); budget.record(response)
    if response.status != "COMPLETED": raise RuntimeError(f"provider call failed: {response.error}")
    return asdict(response), False


def logical_call_id(condition: str, epoch: int, task_id: str, trial: int, call_role: str) -> str:
    if call_role not in CALL_ROLES: raise ValueError("unknown call role")
    return f"phase28:{condition}:e{epoch}:{task_id}:t{trial}:{call_role}"


def cost_preflight() -> dict[str, Any]:
    roles = {"DECISION": 6000, "QUERY_TIME_SYNTHESIS": 1000, "KNOWLEDGE_CONSTRUCTION": 0,
             "VERIFICATION": 0, "MAINTENANCE": 250, "SCORER": 600}
    # Conservative frozen pre-treatment estimates based on the sealed context cap and Phase 27 telemetry.
    estimates = {"DECISION": (1100, 90), "QUERY_TIME_SYNTHESIS": (900, 120),
                 "MAINTENANCE": (1200, 150), "SCORER": (650, 80)}
    input_tokens = sum(roles[r] * estimates.get(r, (0, 0))[0] for r in roles)
    output_tokens = sum(roles[r] * estimates.get(r, (0, 0))[1] for r in roles)
    calls = sum(roles.values()); cost = input_tokens*INPUT_PRICE + output_tokens*OUTPUT_PRICE
    retry_calls = calls * (1 + len(RETRY_DELAYS_SECONDS))
    worst_cost = cost * (1 + len(RETRY_DELAYS_SECONDS))
    hard = {"calls": 10000, "input_tokens": 10_000_000, "output_tokens": 1_500_000, "cost_usd": 20.0}
    return {"calls_by_role": roles, "expected_provider_calls": calls, "expected_input_tokens": input_tokens,
            "expected_output_tokens": output_tokens, "estimated_cost_usd": round(cost, 6),
            "worst_case_retry_calls": retry_calls, "worst_case_cost_usd": round(worst_cost, 6),
            "hard_cap": hard, "expected_fits": calls <= hard["calls"] and input_tokens <= hard["input_tokens"] and output_tokens <= hard["output_tokens"] and cost <= hard["cost_usd"],
            "worst_case_fits": retry_calls <= hard["calls"] and worst_cost <= hard["cost_usd"]}


def smoke_request() -> ModelRequest:
    schema = {"type": "object", "additionalProperties": False, "properties": {"status": {"type": "string", "enum": ["OK"]}}, "required": ["status"]}
    return ModelRequest("phase28a:smoke:1", MODEL,
        [{"role": "system", "content": "Return the required diagnostic JSON only."},
         {"role": "user", "content": "Synthetic non-treatment diagnostic. Return status OK."}], .2, schema, "phase28a_smoke",
        {"condition": "NON_TREATMENT_SMOKE", "epoch": -1, "task_id": "SMOKE-1", "agent_id": "diagnostic",
         "department": "diagnostic", "call_role": "SMOKE", "trial": 1}, max_output_tokens=40)
