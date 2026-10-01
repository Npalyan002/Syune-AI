"""Reliable model gateway orchestration, budgets, circuits, and telemetry."""
from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Mapping
from uuid import uuid4

from .adapters import ProviderAdapter, ProviderTransportError
from .model import *
from .persistence import EvidenceStore, canonical

POLICY_VERSION = "phase29-v1"
SYSTEMIC_FAILURES = frozenset({FailureClass.RATE_LIMIT, FailureClass.TIMEOUT,
    FailureClass.CONNECTION_FAILURE, FailureClass.PROVIDER_5XX, FailureClass.MODEL_UNAVAILABLE})


class BudgetManager:
    """Atomic hierarchical reservation; unknown usage remains reserved."""
    def __init__(self):
        self._lock = threading.Lock()
        self._used: dict[tuple[str, str], dict[str, float]] = defaultdict(
            lambda: {"calls": 0, "input": 0, "output": 0, "cost": 0.0})

    def reserve(self, limits: tuple[BudgetLimit, ...], *, input_tokens: int,
                output_tokens: int, cost: float) -> None:
        with self._lock:
            for limit in limits:
                used = self._used[(limit.scope, limit.scope_id)]
                checks = ((limit.max_calls, used["calls"] + 1),
                          (limit.max_input_tokens, used["input"] + input_tokens),
                          (limit.max_output_tokens, used["output"] + output_tokens),
                          (limit.max_cost_usd, used["cost"] + cost))
                if any(cap is not None and projected > cap for cap, projected in checks):
                    raise RuntimeError(FailureClass.BUDGET_EXCEEDED.value)
            for limit in limits:
                used = self._used[(limit.scope, limit.scope_id)]
                used["calls"] += 1; used["input"] += input_tokens
                used["output"] += output_tokens; used["cost"] += cost

    def reconcile(self, limits: tuple[BudgetLimit, ...], *, reserved_input: int,
                  reserved_output: int, reserved_cost: float, actual_input: int | None,
                  actual_output: int | None, actual_cost: float | None) -> None:
        if actual_input is None or actual_output is None or actual_cost is None:
            return
        with self._lock:
            for limit in limits:
                used = self._used[(limit.scope, limit.scope_id)]
                used["input"] += actual_input - reserved_input
                used["output"] += actual_output - reserved_output
                used["cost"] += actual_cost - reserved_cost


class CircuitBreaker:
    def __init__(self, threshold: int = 3, recovery_seconds: float = 30.0):
        self.threshold, self.recovery_seconds = threshold, recovery_seconds
        self._state: dict[tuple[str, str], dict[str, Any]] = defaultdict(
            lambda: {"failures": 0, "opened_at": None, "probe": False})
        self.events: list[dict[str, Any]] = []

    def allow(self, provider: str, model: str) -> bool:
        entry = self._state[(provider, model)]
        if entry["opened_at"] is None: return True
        if time.monotonic() - entry["opened_at"] >= self.recovery_seconds and not entry["probe"]:
            entry["probe"] = True; return True
        return False

    def record(self, provider: str, model: str, failure: FailureClass | None) -> None:
        entry = self._state[(provider, model)]
        if failure is None:
            recovered = entry["opened_at"] is not None
            entry.update(failures=0, opened_at=None, probe=False)
            if recovered: self.events.append({"provider": provider, "model": model, "event": "RECOVERED"})
        elif failure in SYSTEMIC_FAILURES:
            entry["failures"] += 1; entry["probe"] = False
            if entry["failures"] >= self.threshold and entry["opened_at"] is None:
                entry["opened_at"] = time.monotonic()
                self.events.append({"provider": provider, "model": model, "event": "OPEN", "reason": failure.value})

    def status(self, provider: str, model: str) -> HealthStatus:
        return HealthStatus.CIRCUIT_OPEN if self._state[(provider, model)]["opened_at"] is not None else HealthStatus.HEALTHY


class Metrics:
    def __init__(self):
        self.counts = Counter(); self.latencies: list[float] = []
        self.by_role = defaultdict(Counter); self.by_provider = defaultdict(Counter); self.by_model = defaultdict(Counter)

    def record_attempt(self, role: CallRole, provider: str, model: str,
                       failure: FailureClass | None, latency: float, cost: float) -> None:
        self.counts["attempts"] += 1; self.counts["cost_microusd"] += round(cost * 1_000_000)
        self.latencies.append(latency)
        for group in (self.by_role[role.value], self.by_provider[provider], self.by_model[model]):
            group["attempts"] += 1; group["cost_microusd"] += round(cost * 1_000_000)
        if failure: self.counts[failure.value] += 1

    def snapshot(self) -> dict[str, Any]:
        ordered = sorted(self.latencies)
        def pct(q: float) -> float:
            return ordered[min(len(ordered)-1, int((len(ordered)-1)*q))] if ordered else 0.0
        calls, commits = self.counts["calls"], self.counts["commits"]
        return {"calls": calls, "success_rate": commits/calls if calls else 0.0,
            "first_attempt_success_rate": self.counts["first_attempt_commits"]/calls if calls else 0.0,
            "retry_rate": self.counts["retried_calls"]/calls if calls else 0.0,
            "repair_rate": self.counts["repairs"]/calls if calls else 0.0,
            "fallback_rate": self.counts["fallbacks"]/calls if calls else 0.0,
            "terminal_failure_rate": self.counts["terminal_failures"]/calls if calls else 0.0,
            "latency_ms": {"p50": pct(.5), "p95": pct(.95), "p99": pct(.99)},
            "input_tokens": self.counts["input_tokens"], "output_tokens": self.counts["output_tokens"],
            "cost_usd": self.counts["cost_microusd"]/1_000_000,
            "failure_classes": {f.value: self.counts[f.value] for f in FailureClass},
            "cost_by_role": {k: v["cost_microusd"]/1_000_000 for k,v in self.by_role.items()},
            "cost_by_provider": {k: v["cost_microusd"]/1_000_000 for k,v in self.by_provider.items()},
            "cost_by_model": {k: v["cost_microusd"]/1_000_000 for k,v in self.by_model.items()}}


def output_budget(request: ModelExecutionRequest, model_limit: int | None) -> int:
    if request.max_output_tokens is not None: value = request.max_output_tokens
    else:
        base = {CallRole.CLASSIFICATION:80, CallRole.SCORING:120, CallRole.EXTRACTION:300,
            CallRole.DECISION:240, CallRole.SYNTHESIS:800, CallRole.SUMMARIZATION:700,
            CallRole.PLANNING:1000, CallRole.KNOWLEDGE_CONSTRUCTION:900,
            CallRole.VERIFICATION:300, CallRole.REPAIR:500, CallRole.GENERAL:600}[request.call_role]
        complexity = len(request.structured_output_schema.get("properties", {}))*40 + len(canonical(request.structured_output_schema))//8 if request.structured_output_schema else 0
        value = int(max(base, complexity)*1.25)
    return max(1, min(value, model_limit) if model_limit else value)


def validate_schema(value: Any, schema: Mapping[str, Any], path: str = "$") -> None:
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, dict): raise ValueError(f"{path} must be object")
        missing = [key for key in schema.get("required", ()) if key not in value]
        if missing: raise ValueError(f"{path} missing {missing}")
        if schema.get("additionalProperties") is False:
            extra = set(value)-set(schema.get("properties", {}))
            if extra: raise ValueError(f"{path} unexpected {sorted(extra)}")
        for key, child in schema.get("properties", {}).items():
            if key in value: validate_schema(value[key], child, f"{path}.{key}")
    elif kind == "array":
        if not isinstance(value, list): raise ValueError(f"{path} must be array")
        for index,item in enumerate(value): validate_schema(item, schema.get("items", {}), f"{path}[{index}]")
    elif kind == "string" and not isinstance(value, str): raise ValueError(f"{path} must be string")
    elif kind == "integer" and (not isinstance(value,int) or isinstance(value,bool)): raise ValueError(f"{path} must be integer")
    elif kind == "number" and (not isinstance(value,(int,float)) or isinstance(value,bool)): raise ValueError(f"{path} must be number")
    elif kind == "boolean" and not isinstance(value,bool): raise ValueError(f"{path} must be boolean")
    if "enum" in schema and value not in schema["enum"]: raise ValueError(f"{path} not in enum")
    if isinstance(value,(int,float)):
        if "minimum" in schema and value < schema["minimum"]: raise ValueError(f"{path} below minimum")
        if "maximum" in schema and value > schema["maximum"]: raise ValueError(f"{path} above maximum")


def classify_transport(exc: ProviderTransportError) -> FailureClass:
    if not exc.response_received: return FailureClass.REMOTE_COMPLETION_AMBIGUOUS
    return {401:FailureClass.AUTHENTICATION_FAILURE,403:FailureClass.AUTHORIZATION_FAILURE,
        404:FailureClass.MODEL_NOT_FOUND,408:FailureClass.TIMEOUT,429:FailureClass.RATE_LIMIT}.get(
        exc.status, FailureClass.PROVIDER_5XX if exc.status and exc.status >= 500 else FailureClass.UNKNOWN_PROVIDER_FAILURE)


def classify_response(raw: RawProviderResponse) -> FailureClass | None:
    finish = (raw.finish_reason or "").casefold()
    if raw.refusal or finish in {"refusal","content_filter","content-filter"}: return FailureClass.REFUSAL
    if finish in {"length","max_output_tokens","incomplete"}: return FailureClass.TRUNCATED_OUTPUT
    if raw.http_status == 429: return FailureClass.RATE_LIMIT
    if raw.http_status and raw.http_status >= 500: return FailureClass.PROVIDER_5XX
    if raw.http_status and not 200 <= raw.http_status < 300: return FailureClass.UNKNOWN_PROVIDER_FAILURE
    text = raw.sanitized_metadata.get("response_text", "")
    if not isinstance(text,str) or not text.strip(): return FailureClass.EMPTY_OUTPUT
    return None


def request_fingerprint(request: ModelExecutionRequest) -> str:
    """Fingerprint all execution-relevant request semantics, excluding the call ID."""
    validator = request.semantic_validator
    validator_identity = None if validator is None else f"{getattr(validator,'__module__','')}:{getattr(validator,'__qualname__',type(validator).__qualname__)}"
    value = {"purpose":request.purpose,"messages":request.messages,"call_role":request.call_role,
        "required_capabilities":sorted(x.value for x in request.required_capabilities),
        "structured_output_schema":request.structured_output_schema,"semantic_validator":validator_identity,
        "preferred_model":request.preferred_model,"allowed_models":sorted(request.allowed_models or ()),
        "allowed_providers":sorted(request.allowed_providers or ()),"temperature":request.temperature,
        "max_output_tokens":request.max_output_tokens,"timeout":request.timeout,"retry_policy":request.retry_policy,
        "repair_policy_reference":request.repair_policy_reference,"fallback_policy_reference":request.fallback_policy_reference,
        "strategy":request.strategy,"fallback_mode":request.fallback_mode,"budget_limits":request.budget_limits,
        "principal":request.principal,"access_context":request.access_context,"data_policy":request.data_policy,
        "metadata":request.metadata,"exact_model":request.exact_model,"accept_degraded":request.accept_degraded}
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class ModelGateway:
    def __init__(self, adapters: Mapping[str, ProviderAdapter], store: EvidenceStore, *,
                 routes: tuple[tuple[str, str], ...], budget: BudgetManager | None = None,
                 circuit_breaker: CircuitBreaker | None = None,
                 sleeper: Callable[[float], None] = time.sleep,
                 policy_version: str = POLICY_VERSION, max_concurrency: int = 16,
                 stage_hook: Callable[[str], None] | None = None):
        self.adapters, self.store, self.routes = dict(adapters), store, routes
        self.budget = budget or BudgetManager(); self.circuits = circuit_breaker or CircuitBreaker()
        self.sleeper, self.policy_version = sleeper, policy_version
        self.metrics = Metrics(); self._semaphore = threading.BoundedSemaphore(max_concurrency)
        self.stage_hook = stage_hook
        self._call_locks_guard = threading.Lock(); self._call_locks: dict[str, threading.Lock] = {}

    def _call_lock(self, logical_call_id: str) -> threading.Lock:
        with self._call_locks_guard:
            return self._call_locks.setdefault(logical_call_id, threading.Lock())

    def _stage(self, name: str) -> None:
        if self.stage_hook: self.stage_hook(name)

    def _candidates(self, request: ModelExecutionRequest) -> list[tuple[ProviderAdapter, ModelMetadata]]:
        found = []
        for provider_name, model in self.routes:
            adapter = self.adapters.get(provider_name)
            if not adapter: continue
            if request.allowed_providers and provider_name not in request.allowed_providers: continue
            if request.allowed_models and model not in request.allowed_models: continue
            if request.preferred_model and request.exact_model and model != request.preferred_model: continue
            if request.data_policy.local_only and not adapter.is_local: continue
            if not request.data_policy.allow_external and not adapter.is_local: continue
            if request.data_policy.allowed_providers and provider_name not in request.data_policy.allowed_providers: continue
            try: metadata = adapter.model_metadata(model)
            except KeyError: continue
            if metadata.capabilities.supports(request.required_capabilities): found.append((adapter, metadata))
        found.sort(key=lambda pair: pair[1].model != request.preferred_model)
        if request.fallback_mode is FallbackMode.EXACT_MODEL and found: return found[:1]
        return found

    def execute(self, request: ModelExecutionRequest) -> ModelExecutionResult:
        self.metrics.counts["calls"] += 1
        fingerprint = request_fingerprint(request)
        try: prior = self.store.committed(request.logical_call_id, fingerprint)
        except ValueError:
            return self._terminal(str(uuid4()), request, FailureClass.IDEMPOTENCY_CONFLICT, 0, "logical_call_id already committed with a different request fingerprint")
        if prior:
            prior["state"] = ExecutionState(prior["state"]); prior["quality"] = Quality(prior["quality"])
            if prior.get("failure"): prior["failure"] = FailureClass(prior["failure"])
            return ModelExecutionResult(**prior)
        lock = self._call_lock(request.logical_call_id)
        with lock:
            try: prior = self.store.committed(request.logical_call_id, fingerprint)
            except ValueError:
                return self._terminal(str(uuid4()), request, FailureClass.IDEMPOTENCY_CONFLICT, 0, "logical_call_id already committed with a different request fingerprint")
            if prior:
                prior["state"] = ExecutionState(prior["state"]); prior["quality"] = Quality(prior["quality"])
                if prior.get("failure"): prior["failure"] = FailureClass(prior["failure"])
                return ModelExecutionResult(**prior)
            return self._execute_locked(request, fingerprint)

    def _execute_locked(self, request: ModelExecutionRequest, fingerprint: str) -> ModelExecutionResult:
        recovered = self.store.recover_incomplete(request.logical_call_id)
        execution_id = str(uuid4()); self.store.transition(request.logical_call_id, ExecutionState.CREATED.value)
        candidates = self._candidates(request)
        if not candidates:
            return self._terminal(execution_id, request, FailureClass.CAPABILITY_UNAVAILABLE, 0, "no authorized capable route")
        self.store.transition(request.logical_call_id, ExecutionState.VALIDATED.value)
        attempted = 0; used_fallback = False; failures: list[str] = []
        total_input = total_output = 0; total_cost = total_latency = 0.0
        last_failure = FailureClass.UNKNOWN_PROVIDER_FAILURE
        for candidate_index, (adapter, metadata) in enumerate(candidates):
            if candidate_index: used_fallback = True; self.metrics.counts["fallbacks"] += 1
            if not self.circuits.allow(adapter.name, metadata.model):
                failures.append(FailureClass.CIRCUIT_OPEN.value); last_failure = FailureClass.CIRCUIT_OPEN; continue
            max_output = output_budget(request, metadata.capabilities.max_output_tokens)
            estimated_input = max(1, len(canonical(list(request.messages)))//4)
            in_price, out_price = metadata.input_price_per_million, metadata.output_price_per_million
            reserved_cost = (estimated_input*(in_price or 0)+max_output*(out_price or 0))/1_000_000
            for number in range(1, request.retry_policy.max_attempts+1):
                attempted += 1; attempt_id = f"{execution_id}:A{attempted}"
                self._stage("before_budget_reservation")
                try:
                    self.budget.reserve(request.budget_limits, input_tokens=estimated_input, output_tokens=max_output, cost=reserved_cost)
                    self.store.reserve_budget(attempt_id,request.budget_limits,input_tokens=estimated_input,output_tokens=max_output,cost=reserved_cost)
                except RuntimeError:
                    return self._terminal(execution_id, request, FailureClass.BUDGET_EXCEEDED, attempted-1, "budget reservation denied", used_fallback=used_fallback)
                self.store.transition(request.logical_call_id, ExecutionState.BUDGET_RESERVED.value, {"attempt":attempt_id})
                self._stage("after_budget_reservation")
                self.store.transition(request.logical_call_id, ExecutionState.REQUEST_STARTED.value, {"attempt":attempt_id})
                self._stage("before_provider_request")
                timestamp = datetime.now(timezone.utc).isoformat()
                try:
                    if adapter.health(metadata.model) is HealthStatus.UNAVAILABLE:
                        raise ProviderTransportError("provider unavailable", status=503, response_received=True)
                    acquired = self._semaphore.acquire(timeout=min(request.timeout.connect_seconds, request.timeout.overall_seconds))
                    if not acquired:
                        raise ProviderTransportError("gateway concurrency exhausted", status=429, response_received=True)
                    try:
                        raw = adapter.execute(ProviderRequest(execution_id, attempt_id, request, adapter.name, metadata.model, max_output))
                    finally:
                        self._semaphore.release()
                    self.store.transition(request.logical_call_id, ExecutionState.HTTP_RESPONSE_RECEIVED.value)
                    self._stage("after_provider_response")
                    failure = classify_response(raw)
                except ProviderTransportError as exc:
                    failure = classify_transport(exc)
                    if str(exc) == "gateway concurrency exhausted": failure = FailureClass.CONCURRENCY_EXHAUSTED
                    elif str(exc) == "provider unavailable": failure = FailureClass.PROVIDER_UNAVAILABLE
                    raw = RawProviderResponse(exc.status, exc.raw_body, retry_after_seconds=exc.retry_after_seconds,
                                              response_received=exc.response_received)
                except Exception as exc:
                    failure = FailureClass.UNKNOWN_PROVIDER_FAILURE
                    raw = RawProviderResponse(None, "", response_received=False,
                                              sanitized_metadata={"error_type":type(exc).__name__})
                usage_known = raw.input_tokens is not None and raw.output_tokens is not None
                actual_cost = None if not usage_known or in_price is None or out_price is None else (
                    raw.input_tokens*in_price+raw.output_tokens*out_price)/1_000_000
                self.store.persist_attempt(AttemptEvidence(execution_id, request.logical_call_id,
                    attempt_id, attempted, adapter.name, metadata.model, raw.resolved_model,
                    raw.model_version, raw.provider_request_id, raw.http_status, raw.finish_reason,
                    raw.raw_body, raw.input_tokens, raw.output_tokens, raw.latency_ms, timestamp,
                    failure, ExecutionState.CLASSIFIED, UsageStatus.MEASURED if usage_known else UsageStatus.UNKNOWN,
                    reserved_cost, actual_cost, Quality.FALLBACK if used_fallback else Quality.NORMAL,
                    self.policy_version))
                self.store.transition(request.logical_call_id, ExecutionState.RAW_PERSISTED.value, {"attempt":attempt_id})
                self.budget.reconcile(request.budget_limits, reserved_input=estimated_input,
                    reserved_output=max_output, reserved_cost=reserved_cost, actual_input=raw.input_tokens,
                    actual_output=raw.output_tokens, actual_cost=actual_cost)
                self.store.reconcile_budget(attempt_id,input_tokens=raw.input_tokens,output_tokens=raw.output_tokens,cost=actual_cost)
                self._stage("after_raw_persistence")
                cost = actual_cost if actual_cost is not None else reserved_cost
                total_input += raw.input_tokens or estimated_input; total_output += raw.output_tokens or max_output
                total_cost += cost; total_latency += raw.latency_ms
                if failure is None and request.exact_model and raw.resolved_model != metadata.model:
                    failure = FailureClass.MODEL_UNAVAILABLE
                parsed: Any = raw.sanitized_metadata.get("response_text", "")
                if failure is None and request.structured_output_schema is not None:
                    try: parsed = json.loads(parsed)
                    except (TypeError,json.JSONDecodeError): failure = FailureClass.INVALID_JSON
                self._stage("after_parsing")
                if failure is None and request.structured_output_schema is not None:
                    try: validate_schema(parsed, request.structured_output_schema)
                    except ValueError: failure = FailureClass.SCHEMA_INVALID
                self._stage("after_schema_validation")
                if failure is None and request.semantic_validator is not None:
                    try: request.semantic_validator(parsed)
                    except (ValueError,TypeError,AssertionError): failure = FailureClass.SEMANTIC_INVALID
                self._stage("after_semantic_validation")
                self.circuits.record(adapter.name, metadata.model, failure)
                self.metrics.record_attempt(request.call_role, adapter.name, metadata.model, failure, raw.latency_ms, cost)
                self.metrics.counts["input_tokens"] += raw.input_tokens or 0; self.metrics.counts["output_tokens"] += raw.output_tokens or 0
                if failure is None:
                    result = ModelExecutionResult(execution_id, request.logical_call_id,
                        hashlib.sha256(f"{request.logical_call_id}:{canonical(parsed)}".encode()).hexdigest(),
                        ExecutionState.COMMITTED, parsed, provider=adapter.name,
                        requested_model=request.preferred_model or metadata.model,
                        resolved_model=raw.resolved_model, model_version=raw.model_version,
                        provider_request_id=raw.provider_request_id, attempts=attempted,
                        used_fallback=used_fallback, quality=Quality.FALLBACK if used_fallback else Quality.NORMAL,
                        input_tokens=total_input, output_tokens=total_output, cost_usd=total_cost,
                        latency_ms=total_latency, policy_version=self.policy_version,
                        audit={"selection":"ordered capable authorized route","retry_policy":request.retry_policy.name,
                               "failures":failures,"repair_used":False,"fallback_used":used_fallback})
                    if not request.accept_degraded and result.quality is not Quality.NORMAL:
                        return self._terminal(execution_id, request, FailureClass.MODEL_UNAVAILABLE, attempted, "caller rejected degraded result")
                    self._stage("before_semantic_commit")
                    self.store.commit(result, fingerprint); self.store.transition(request.logical_call_id, ExecutionState.COMMITTED.value)
                    self._stage("after_semantic_commit")
                    self.store.transition(request.logical_call_id,"CHECKPOINT_WRITTEN",{"semantic_commit_id":result.semantic_commit_id})
                    self._stage("after_checkpoint_write")
                    self.metrics.counts["commits"] += 1
                    if attempted == 1: self.metrics.counts["first_attempt_commits"] += 1
                    if attempted > 1: self.metrics.counts["retried_calls"] += 1
                    return result
                last_failure = failure; failures.append(failure.value)
                if failure not in request.retry_policy.retryable or number >= request.retry_policy.max_attempts: break
                delay = raw.retry_after_seconds
                if delay is None:
                    index = min(number-1,len(request.retry_policy.backoff_seconds)-1)
                    delay = request.retry_policy.backoff_seconds[index] if request.retry_policy.backoff_seconds else 0
                self.sleeper(max(0,min(delay,request.timeout.overall_seconds)))
            if request.fallback_mode is FallbackMode.EXACT_MODEL or last_failure not in request.retry_policy.fallback_eligible: break
        if attempted > 1: self.metrics.counts["retried_calls"] += 1
        return self._terminal(execution_id, request, last_failure, attempted, ";".join(failures),
            used_fallback=used_fallback, input_tokens=total_input, output_tokens=total_output, cost=total_cost, latency=total_latency)

    def repair(self, original: ModelExecutionRequest, malformed_output: str,
               validation_errors: tuple[str, ...]) -> ModelExecutionResult:
        """Run an explicitly requested, separately metered repair call.

        Only the original schema, sanitized malformed output, and deterministic validation
        errors are disclosed. Repair is never silently activated by ``execute``.
        """
        if original.structured_output_schema is None:
            raise ValueError("repair requires a structured output schema")
        safe_output = malformed_output[:20_000]
        repair_request = ModelExecutionRequest(
            logical_call_id=f"{original.logical_call_id}:repair",
            purpose=f"Repair structured output for {original.purpose}",
            call_role=CallRole.REPAIR,
            messages=({"role":"system","content":"Repair data into the required JSON schema. Do not add facts."},
                      {"role":"user","content":canonical({"schema":original.structured_output_schema,
                          "malformed_output":safe_output,"validation_errors":validation_errors})}),
            required_capabilities=original.required_capabilities,
            structured_output_schema=original.structured_output_schema,
            semantic_validator=original.semantic_validator,
            preferred_model=original.preferred_model, allowed_models=original.allowed_models,
            allowed_providers=original.allowed_providers, temperature=0,
            max_output_tokens=original.max_output_tokens, timeout=original.timeout,
            retry_policy=original.retry_policy, strategy=StructuredOutputStrategy.REPAIR_CALL,
            fallback_mode=original.fallback_mode, budget_limits=original.budget_limits,
            principal=original.principal, access_context=original.access_context,
            data_policy=original.data_policy, metadata={**original.metadata,"repair_of":original.logical_call_id},
            exact_model=original.exact_model, accept_degraded=original.accept_degraded,
            repair_policy_reference=original.repair_policy_reference,
            fallback_policy_reference=original.fallback_policy_reference)
        self.metrics.counts["repairs"] += 1
        result = self.execute(repair_request)
        if result.committed:
            object.__setattr__(result, "used_repair", True)
        return result

    def _terminal(self, execution_id: str, request: ModelExecutionRequest, failure: FailureClass,
                  attempts: int, message: str, *, used_fallback: bool=False, input_tokens: int=0,
                  output_tokens: int=0, cost: float=0.0, latency: float=0.0) -> ModelExecutionResult:
        self.store.transition(request.logical_call_id, ExecutionState.FAILED_TERMINAL.value, {"failure":failure.value})
        self.metrics.counts["terminal_failures"] += 1
        return ModelExecutionResult(execution_id, request.logical_call_id, None, ExecutionState.FAILED_TERMINAL,
            failure=failure, message=message, attempts=attempts, used_fallback=used_fallback,
            quality=Quality.FALLBACK if used_fallback else Quality.NORMAL, input_tokens=input_tokens,
            output_tokens=output_tokens, cost_usd=cost, latency_ms=latency,
            policy_version=self.policy_version, audit={"retry_policy":request.retry_policy.name,"fallback_used":used_fallback})

    def health(self) -> dict[str, Any]:
        routes=[]
        for provider,model in self.routes:
            adapter=self.adapters.get(provider); adapter_health=adapter.health(model) if adapter else HealthStatus.UNAVAILABLE
            circuit=self.circuits.status(provider,model); status=circuit if circuit is HealthStatus.CIRCUIT_OPEN else adapter_health
            routes.append({"provider":provider,"model":model,"status":status.value})
        values={row["status"] for row in routes}
        overall=HealthStatus.HEALTHY if values=={HealthStatus.HEALTHY.value} else (HealthStatus.UNAVAILABLE if values <= {HealthStatus.UNAVAILABLE.value,HealthStatus.CIRCUIT_OPEN.value} else HealthStatus.DEGRADED)
        return {"overall":overall.value,"routes":routes,"policy_version":self.policy_version}
