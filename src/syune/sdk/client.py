"""Local, synchronous public SDK facade."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, TypeVar

from syune.api.capabilities import capability_summary
from syune.api.errors import ErrorCategory, SyuneError
from syune.api.model import (
    AddMessage, AuditResult, BatchAddRequest, BatchAddResult, CapabilitySummary, ContextRequest, ContextResult, HistoryResult, ModelResult, RememberRequest, RememberResult, ReviseRequest, RevisionResult, CognitiveRequest as PublicCognitiveRequest, CognitiveResult as PublicCognitiveResult,
    CouncilRequest as PublicCouncilRequest, CouncilResult as PublicCouncilResult, DiagnosticsLevel,
    HealthResult, MemoryResult, PlanRequest, PlanResult, RecallRequest as PublicRecallRequest,
    RecallResult as PublicRecallResult, RuntimeMode, SourceStatusResult, StatusResult,
    StudyRequest, StudyResult as PublicStudyResult, SyuneHandshake, TypedId,
)
from syune.api.serialization import to_primitive
from syune.api.version import PUBLIC_API_VERSION, SUPPORTED_PUBLIC_API_VERSIONS, negotiate_version
from syune.core import *
from syune.product.config import load_config
from syune.product.runtime import SyuneRuntime
from syune.product.schema import STATE_SCHEMA_VERSION

T = TypeVar("T")
_ID_TYPES = {cls.__name__: cls for cls in (
    SourceId, ObservationId, ConceptId, ClaimId, EvidenceId, EpisodeId, ProcedureId,
    MemoryTraceId, ActivationProfileId,
)}


def _package_version() -> str:
    from syune.release import RELEASE_VERSION
    return RELEASE_VERSION


def _cid(value: str | None) -> str:
    from uuid import uuid4
    if value is None: return str(uuid4())
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise SyuneError("INVALID_REQUEST", "invalid correlation_id", ErrorCategory.INVALID_REQUEST)
    return value


def _observed_at(value: str | None, default):
    from datetime import datetime, timezone
    if value is None:
        return default
    if not isinstance(value, str) or not value.strip():
        raise ValueError("observed_at must be a timezone-aware ISO 8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("observed_at must be a timezone-aware ISO 8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("observed_at must include a timezone offset")
    return parsed.astimezone(timezone.utc)


def _internal_id(value: TypedId, expected=None):
    try:
        cls = _ID_TYPES[value.entity_type]
        result = cls.parse(value.value)
    except (KeyError, ValueError, TypeError) as exc:
        raise SyuneError("INVALID_REQUEST", "unsupported or malformed typed ID", ErrorCategory.INVALID_REQUEST) from exc
    if expected is not None and type(result) is not expected:
        raise SyuneError("INVALID_REQUEST", f"{expected.__name__} required", ErrorCategory.INVALID_REQUEST)
    return result


class Syune:
    """Lifecycle-managed local v1 client. Internal stores are never returned."""

    __slots__ = ("__runtime", "_mode", "_model_gateway")

    def __init__(self, runtime: SyuneRuntime, mode: RuntimeMode = RuntimeMode.NORMAL, model_gateway=None):
        self.__runtime = runtime
        self._mode = mode
        self._model_gateway = model_gateway

    @classmethod
    def open(cls, *, state_root: str | Path | None = None, config: str | Path | None = None,
             mode: RuntimeMode | str = RuntimeMode.NORMAL, model_gateway=None) -> "Syune":
        try:
            selected = mode if isinstance(mode, RuntimeMode) else RuntimeMode(mode)
            return cls(SyuneRuntime.open(load_config(cli_state_root=state_root, cli_config=config)), selected, model_gateway)
        except FileNotFoundError as exc:
            raise SyuneError("NOT_INITIALIZED", str(exc), ErrorCategory.NOT_INITIALIZED) from None
        except SyuneError: raise
        except (ValueError, TypeError) as exc:
            raise SyuneError("INVALID_REQUEST", str(exc), ErrorCategory.INVALID_REQUEST) from None

    def close(self) -> None: self.__runtime.close()
    def __enter__(self) -> "Syune": return self
    def __exit__(self, *_: object) -> None: self.close()

    def _call(self, correlation_id: str | None, operation: Callable[[str], T]) -> T:
        cid = _cid(correlation_id)
        try: return operation(cid)
        except SyuneError: raise
        except KeyError:
            raise SyuneError("NOT_FOUND", "requested object was not found", ErrorCategory.NOT_FOUND,
                             correlation_id=cid) from None
        except (ValueError, TypeError) as exc:
            raise SyuneError("INVALID_REQUEST", str(exc)[:240], ErrorCategory.INVALID_REQUEST,
                             correlation_id=cid) from None
        except Exception as exc:
            code = getattr(getattr(exc, "code", None), "value", None)
            if code:
                category = ErrorCategory.NOT_FOUND if "MISSING" in code else ErrorCategory.INVALID_REQUEST
                raise SyuneError(code, str(exc)[:240], category, correlation_id=cid) from None
            raise SyuneError("INTERNAL", "operation failed", ErrorCategory.INTERNAL, correlation_id=cid) from None

    def capabilities(self) -> CapabilitySummary: return capability_summary(self._mode)

    def handshake(self, host_supported: tuple[str, ...] | list[str] = (PUBLIC_API_VERSION,)) -> SyuneHandshake:
        selected = negotiate_version(host_supported)
        return SyuneHandshake(_package_version(), SUPPORTED_PUBLIC_API_VERSIONS, selected, STATE_SCHEMA_VERSION,
                              "LEAN_V1", self.capabilities(), self._mode,
                              self.__runtime.health()["overall"])

    def health(self, *, correlation_id: str | None = None) -> HealthResult:
        return self._call(correlation_id, lambda cid: HealthResult(cid, {
            **self.__runtime.health(), "package_version": _package_version(), "public_api_version": PUBLIC_API_VERSION,
        }))

    def status(self, *, correlation_id: str | None = None) -> StatusResult:
        return self._call(correlation_id, lambda cid: StatusResult(cid, {
            "package_version": _package_version(), "public_api_version": PUBLIC_API_VERSION,
            "initialized": True, "state_schema": self.__runtime.metadata.state_schema_version,
            "runtime_mode": self._mode.value,
            "product": "SYUNE", "runtime": "LEAN_V1", "telemetry": "OFF",
            "health": self.__runtime.health()["overall"],
        }))

    def _safe_study_path(self, raw: str, *, must_exist: bool) -> Path:
        path = Path(raw)
        if not path.is_absolute() or ".." in path.parts:
            raise SyuneError("INVALID_REQUEST", "absolute child path without traversal required", ErrorCategory.INVALID_REQUEST)
        try: resolved = path.resolve(strict=must_exist)
        except OSError as exc: raise SyuneError("NOT_FOUND", "source unavailable", ErrorCategory.NOT_FOUND) from exc
        if not any(resolved.is_relative_to(root.resolve(strict=True)) for root in self.__runtime.config.study.roots):
            raise SyuneError("BLOCKED", "source is outside configured Study roots", ErrorCategory.BLOCKED, blocked=True)
        return resolved

    def study(self, request: StudyRequest | str) -> PublicStudyResult:
        request = StudyRequest(request) if isinstance(request, str) else request
        if self._mode not in (RuntimeMode.NORMAL, RuntimeMode.TEST):
            raise SyuneError("BLOCKED", "Study is unavailable in this runtime mode", ErrorCategory.BLOCKED, blocked=True,
                             correlation_id=_cid(request.correlation_id))
        def operation(cid):
            result = self.__runtime.study.study(self._safe_study_path(request.path, must_exist=True))
            self.__runtime.index.sync()
            return PublicStudyResult(cid, self._study_status(result.status) | {
                "classification": result.classification.value, "block_changes": to_primitive(result.block_changes)})
        return self._call(request.correlation_id, operation)

    def _study_status(self, status) -> dict:
        if status is None: return {"known": False, "materialization": "NOT_ENCODED"}
        return {"known": True, "source_id": f"SourceId:{status.source_id}",
                "revision_id": f"SourceRevisionId:{status.revision_id}", "state": status.state.value,
                "is_studied": status.is_studied,
                "materialization": self.__runtime.study.materialization_status(status.revision_id).value,
                "sha256": status.sha256, "blocks_total": status.blocks_total,
                "blocks_encoded": status.blocks_encoded, "error_code": status.error_code,
                "provenance": {"locators": list(status.locators), "parser_version": status.parser_version,
                               "pipeline_version": status.pipeline_version}}

    def source_status(self, *, source_id: TypedId | None = None, fingerprint: str | None = None,
                      path: str | None = None, correlation_id: str | None = None) -> SourceStatusResult:
        def operation(cid):
            if sum(item is not None for item in (source_id, fingerprint, path)) != 1:
                raise ValueError("exactly one lookup key required")
            if source_id is not None: status = self.__runtime.study_registry.by_source_id(_internal_id(source_id, SourceId))
            elif fingerprint is not None: status = self.__runtime.study_registry.by_fingerprint(fingerprint)
            else: status = self.__runtime.study_registry.by_locator(str(self._safe_study_path(path, must_exist=False)))
            return SourceStatusResult(cid, self._study_status(status))
        return self._call(correlation_id, operation)

    def remember(self, request: RememberRequest | str) -> RememberResult:
        request = RememberRequest(request) if isinstance(request, str) else request
        if self._mode not in (RuntimeMode.NORMAL, RuntimeMode.TEST):
            raise SyuneError("BLOCKED", "remember is unavailable in this runtime mode", ErrorCategory.BLOCKED, blocked=True)
        def operation(cid):
            from syune.core import Confidence, ObservationId, ProvenanceId, SourceId, utc_now
            from syune.memory import Observation, Provenance, SecurityEnvelope, Source
            now, source_id = utc_now(), SourceId.new()
            observed_at = _observed_at(request.observed_at, now)
            security = SecurityEnvelope(owner=request.owner, allowed_principals=request.allowed_principals) \
                if request.owner or request.allowed_principals else None
            source = Source(source_id, "direct", request.source_name, now, security=security)
            observation = Observation(ObservationId.new(), request.text, "text",
                Provenance(ProvenanceId.new(), source_id, now, process_id="syune.remember",
                           pipeline_version="lean-v1"), observed_at, now, Confidence(1.0), security=security)
            self.__runtime.memory.put_many((source, observation)); self.__runtime.index.sync()
            self.__runtime.audit.record(operation_id=cid, correlation_id=cid, operation_type="remember",
                outcome="SUCCESS", resource_ids=(f"SourceId:{source.id}", f"ObservationId:{observation.id}"))
            return RememberResult(cid, {"source_id": f"SourceId:{source.id}",
                "memory_id": f"ObservationId:{observation.id}", "stored_as": "observation",
                "truth_claim": False,
                "observed_at": observation.observed_at.isoformat().replace("+00:00", "Z"),
                "created_at": observation.created_at.isoformat().replace("+00:00", "Z")})
        return self._call(request.correlation_id, operation)

    def add_batch(self, request: BatchAddRequest, *, global_request_id: bool = False) -> BatchAddResult:
        """Atomically add an ordered, idempotent user/session message batch."""
        if self._mode not in (RuntimeMode.NORMAL, RuntimeMode.TEST):
            raise SyuneError("BLOCKED", "batch add is unavailable in this runtime mode",
                             ErrorCategory.BLOCKED, blocked=True)
        def operation(cid):
            import hashlib
            import json
            from uuid import NAMESPACE_URL, uuid5
            from syune.core import Confidence, ObservationId, ProvenanceId, SourceId, utc_now
            from syune.memory import (
                IdempotencyConflictError, Observation, Provenance, SecurityEnvelope, Source,
            )
            if not isinstance(request, BatchAddRequest):
                raise ValueError("BatchAddRequest required")
            for name in ("request_id", "user_id", "session_id"):
                value = getattr(request, name)
                if not isinstance(value, str) or not value.strip() or len(value) > 256:
                    raise ValueError(f"{name} must be a nonempty string of at most 256 characters")
            if not isinstance(request.messages, tuple) or not request.messages:
                raise ValueError("messages must be a nonempty tuple")
            if any(not isinstance(item, AddMessage) for item in request.messages):
                raise ValueError("messages must contain AddMessage values")
            ordinals = tuple(item.ordinal for item in request.messages)
            if any(type(value) is not int or value < 0 for value in ordinals):
                raise ValueError("message ordinals must be nonnegative integers")
            if ordinals != tuple(range(len(request.messages))):
                raise ValueError("message ordinals must be ordered and contiguous from zero")

            now = utc_now()
            normalized = []
            for item in request.messages:
                if not isinstance(item.text, str) or not item.text.strip():
                    raise ValueError("message text must be nonempty")
                if not isinstance(item.source_name, str) or not item.source_name.strip():
                    raise ValueError("message source_name must be nonempty")
                event_time = _observed_at(item.observed_at, now)
                normalized.append((item, event_time))
            canonical = {
                "user_id": request.user_id,
                "session_id": request.session_id,
                "messages": [{"ordinal": item.ordinal, "text": item.text,
                              "observed_at": (event_time.isoformat()
                                              if item.observed_at is not None else None),
                              "source_name": item.source_name}
                             for item, event_time in normalized],
            }
            payload_hash = hashlib.sha256(json.dumps(
                canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")).hexdigest()
            namespace = f"syune:add:{request.user_id}:{request.session_id}:{request.request_id}"
            security = SecurityEnvelope(owner=f"user:{request.user_id}")
            entities = []
            results = []
            for item, event_time in normalized:
                source_id = SourceId(uuid5(NAMESPACE_URL, f"{namespace}:{item.ordinal}:source"))
                observation_id = ObservationId(uuid5(NAMESPACE_URL, f"{namespace}:{item.ordinal}:observation"))
                provenance_id = ProvenanceId(uuid5(NAMESPACE_URL, f"{namespace}:{item.ordinal}:provenance"))
                source = Source(source_id, "agent-memory", item.source_name, now, security=security)
                observation = Observation(observation_id, item.text, "text",
                    Provenance(provenance_id, source_id, now, process_id="syune.add_batch",
                               pipeline_version="lean-v1"),
                    event_time, now, Confidence(1.0), security=security)
                entities.extend((source, observation))
                results.append({"ordinal": item.ordinal, "source_id": f"SourceId:{source_id}",
                                "memory_id": f"ObservationId:{observation_id}",
                                "observed_at": event_time.isoformat().replace("+00:00", "Z"),
                                "created_at": now.isoformat().replace("+00:00", "Z")})
            data = {"request_id": request.request_id, "user_id": request.user_id,
                    "session_id": request.session_id, "payload_hash": payload_hash,
                    "messages": results}
            try:
                replayed, durable = self.__runtime.memory.put_idempotent_batch(
                    user_id=request.user_id, session_id=request.session_id,
                    request_id=request.request_id, payload_hash=payload_hash,
                    entities=tuple(entities), result=data,
                    global_request_id=global_request_id)
            except IdempotencyConflictError as exc:
                raise SyuneError("IDEMPOTENCY_CONFLICT", str(exc), ErrorCategory.CONFLICT,
                                 correlation_id=cid, operation_id=request.request_id) from None
            # The index is derivative. A committed request is not acknowledged until
            # this runtime has synchronized it; retry/restart safely repeats this step.
            self.__runtime.index.sync()
            resource_ids = tuple(item["memory_id"] for item in durable["messages"])
            self.__runtime.audit.record(
                operation_id=request.request_id, correlation_id=cid,
                operation_type="batch_add", outcome="REPLAY" if replayed else "SUCCESS",
                principal={"user_id": request.user_id}, resource_ids=resource_ids,
                detail={"session_id": request.session_id, "payload_hash": payload_hash,
                        "message_count": len(request.messages)},
            )
            return BatchAddResult(cid, durable)
        return self._call(request.correlation_id, operation)

    def revise(self, request: ReviseRequest) -> RevisionResult:
        def operation(cid):
            from datetime import datetime
            from syune.core import ObservationId, ProvenanceId, utc_now
            from syune.memory import Observation, Provenance, TruthMetadata, authorize
            old_id = _internal_id(request.memory_id)
            old = self.__runtime.memory.get(old_id)
            if old is None: self._raise_record_state(old_id, cid)
            if not isinstance(old, Observation):
                raise SyuneError("INVALID_REQUEST", "v1 revision supports observations", ErrorCategory.INVALID_REQUEST,
                                 correlation_id=cid, resource_id=str(request.memory_id), operation_id=cid)
            access = self._access(request)
            decision = authorize(old.security, access)
            if not decision.allowed: self._raise_auth(decision.code.value, cid, str(request.memory_id), request, "revision")
            if self.__runtime.index.is_superseded(old_id):
                raise SyuneError("REVISION_CONFLICT", "memory already has a current revision", ErrorCategory.CONFLICT,
                                 correlation_id=cid, resource_id=str(request.memory_id), operation_id=cid)
            now = utc_now()
            valid_from = datetime.fromisoformat(request.valid_from.replace("Z", "+00:00")) if request.valid_from else now
            truth = TruthMetadata(state=old.truth.state, recorded_at=now, valid_from=valid_from,
                revision_of=old.id, supersedes=(old.id,), fact_key=old.truth.fact_key,
                fact_value=old.truth.fact_value, context_key=old.truth.context_key)
            provenance = Provenance(ProvenanceId.new(), old.provenance.source_id, now,
                source_version_id=old.provenance.source_version_id, locator=old.provenance.locator,
                process_id="syune.revise", pipeline_version="lean-v1",
                parent_provenance_ids=(old.provenance.id,))
            new = Observation(ObservationId.new(), request.content, old.content_kind, provenance, now, now,
                old.extraction_confidence, truth, security=old.security)
            self.__runtime.memory.put(new); self.__runtime.index.sync()
            new_typed = f"ObservationId:{new.id}"
            self.__runtime.audit.record(operation_id=cid, correlation_id=cid, operation_type="revision",
                outcome="SUCCESS", authorization_decisions=(decision.code.value,),
                resource_ids=(str(request.memory_id), new_typed), purpose=request.purpose)
            return RevisionResult(cid, {"memory_id": new_typed, "revision_of": str(request.memory_id),
                "supersedes": [str(request.memory_id)], "recorded_at": now.isoformat(),
                "valid_from": valid_from.isoformat()})
        return self._call(request.correlation_id, operation)

    @staticmethod
    def _access(request):
        from syune.memory import AccessContext, Principal
        if not any((getattr(request, "user_id", None), getattr(request, "agent_id", None), getattr(request, "service_id", None))):
            return None
        return AccessContext(Principal(request.user_id, request.agent_id, request.organization_id,
            request.project_id, request.department_id, request.service_id), getattr(request, "purpose", None),
            getattr(request, "task_id", None), False)

    def _raise_record_state(self, internal, cid):
        from syune.memory import LifecycleState
        state = self.__runtime.memory.lifecycle(internal).state
        code = {LifecycleState.ARCHIVED:"RECORD_ARCHIVED", LifecycleState.FORGOTTEN:"RECORD_FORGOTTEN",
                LifecycleState.PURGED:"RECORD_PURGED"}.get(state, "RECORD_NOT_FOUND")
        self.__runtime.audit.record(operation_id=cid, correlation_id=cid, operation_type="lifecycle_denial",
            outcome="DENIED", resource_ids=(f"{type(internal).__name__}:{internal}",), lifecycle_action=state.value)
        raise SyuneError(code, f"memory record is {state.value.lower()}", ErrorCategory.NOT_FOUND,
                         correlation_id=cid, resource_id=f"{type(internal).__name__}:{internal}", operation_id=cid)

    def _raise_auth(self, decision, cid, resource_id, request, operation):
        code = "MISSING_PRINCIPAL" if decision == "DENY_MISSING_PRINCIPAL" else (
            "PURPOSE_DENIED" if decision == "DENY_PURPOSE" else (
            "SCOPE_DENIED" if "SCOPE" in decision else "UNAUTHORIZED"))
        self.__runtime.audit.record(operation_id=cid, correlation_id=cid, operation_type=operation,
            outcome="DENIED", authorization_decisions=(decision,), resource_ids=(resource_id,),
            purpose=getattr(request, "purpose", None))
        raise SyuneError(code, "access denied by memory policy", ErrorCategory.BLOCKED, blocked=True,
                         correlation_id=cid, resource_id=resource_id, operation_id=cid)

    def forget(self, entity_id: TypedId | str, *, reason: str = "user request",
               correlation_id: str | None = None) -> MemoryResult:
        if self._mode not in (RuntimeMode.NORMAL, RuntimeMode.TEST):
            raise SyuneError("BLOCKED", "forget is unavailable in this runtime mode", ErrorCategory.BLOCKED, blocked=True)
        typed = TypedId.parse(entity_id) if isinstance(entity_id, str) else entity_id
        def operation(cid):
            from syune.memory import LifecycleState
            internal = _internal_id(typed)
            if self.__runtime.memory.get(internal) is None: raise KeyError(internal)
            self.__runtime.memory.transition_lifecycle(internal, LifecycleState.FORGOTTEN, reason)
            self.__runtime.index.sync()
            self.__runtime.audit.record(operation_id=cid, correlation_id=cid, operation_type="forget",
                outcome="SUCCESS", resource_ids=(str(typed),), lifecycle_action="FORGOTTEN")
            return MemoryResult(cid, {"typed_entity_id": str(typed), "lifecycle": "FORGOTTEN"})
        return self._call(correlation_id, operation)

    def archive(self, entity_id: TypedId | str, *, reason: str = "user request",
                correlation_id: str | None = None) -> MemoryResult:
        return self._lifecycle(entity_id, "ARCHIVED", reason, correlation_id)

    def purge(self, entity_id: TypedId | str, *, reason: str = "user request",
              correlation_id: str | None = None) -> MemoryResult:
        return self._lifecycle(entity_id, "PURGED", reason, correlation_id)

    def _lifecycle(self, entity_id, state_name, reason, correlation_id):
        typed = TypedId.parse(entity_id) if isinstance(entity_id, str) else entity_id
        def operation(cid):
            from syune.memory import LifecycleState
            internal = _internal_id(typed)
            if self.__runtime.memory.get(internal) is None: self._raise_record_state(internal, cid)
            if state_name == "PURGED": self.__runtime.memory.purge(internal, reason)
            else: self.__runtime.memory.transition_lifecycle(internal, LifecycleState(state_name), reason)
            self.__runtime.index.sync()
            self.__runtime.audit.record(operation_id=cid, correlation_id=cid, operation_type=state_name.lower(),
                outcome="SUCCESS", resource_ids=(str(typed),), lifecycle_action=state_name)
            return MemoryResult(cid, {"typed_entity_id": str(typed), "lifecycle": state_name})
        return self._call(correlation_id, operation)

    def history(self, entity_id: TypedId | str, *, correlation_id: str | None = None) -> HistoryResult:
        typed = TypedId.parse(entity_id) if isinstance(entity_id, str) else entity_id
        def operation(cid):
            internal = _internal_id(typed)
            if self.__runtime.memory.get(internal) is None: raise KeyError(internal)
            events = [event for event in self.__runtime.memory.truth_events() if event.entity_id == internal]
            entity = self.__runtime.memory.get(internal)
            return HistoryResult(cid, {"typed_entity_id": str(typed),
                "lifecycle": to_primitive(self.__runtime.memory.lifecycle(internal)),
                "truth": to_primitive(getattr(entity, "truth", None)),
                "provenance": to_primitive(getattr(entity, "provenance", None)),
                "truth_events": to_primitive(tuple(events))})
        return self._call(correlation_id, operation)

    def model(self, request) -> ModelResult:
        cid = getattr(request, "logical_call_id", None)
        if self._model_gateway is None:
            raise SyuneError("MODEL_UNAVAILABLE", "attach a configured ModelGateway when opening Syune",
                             ErrorCategory.BLOCKED, blocked=True, correlation_id=cid)
        def operation(resolved):
            result = self._model_gateway.execute(request)
            self.__runtime.audit.record(operation_id=resolved, correlation_id=resolved,
                operation_type="model", outcome="SUCCESS" if getattr(result,"committed",False) else "FAILED",
                logical_call_id=request.logical_call_id,
                detail={"result": type(result).__name__, "provider": getattr(result,"provider",None),
                        "model": getattr(result,"resolved_model",None), "cost_usd": getattr(result,"cost_usd",None)})
            failure = getattr(getattr(result, "failure", None), "value", None)
            if failure:
                code = ("BUDGET_DENIED" if failure == "BUDGET_EXCEEDED" else
                        "STRUCTURED_OUTPUT_FAILURE" if failure in ("INVALID_JSON","SCHEMA_INVALID","SEMANTIC_INVALID") else
                        "MODEL_UNAVAILABLE" if failure in ("MODEL_NOT_FOUND","MODEL_UNAVAILABLE","CAPABILITY_UNAVAILABLE") else
                        "PROVIDER_UNAVAILABLE")
                retryable = failure in ("RATE_LIMIT","TIMEOUT","CONNECTION_FAILURE","PROVIDER_5XX","PROVIDER_UNAVAILABLE")
                raise SyuneError(code, getattr(result,"message",None) or "model execution failed",
                    ErrorCategory.UNAVAILABLE if retryable else ErrorCategory.BLOCKED, retryable=retryable,
                    blocked=not retryable, correlation_id=resolved, operation_id=resolved)
            return ModelResult(resolved, to_primitive(result))
        return self._call(cid, operation)

    def memory_get(self, entity_id: TypedId | str, *, include_associations: bool = False,
                   correlation_id: str | None = None, user_id: str | None = None,
                   agent_id: str | None = None, organization_id: str | None = None,
                   project_id: str | None = None, department_id: str | None = None,
                   service_id: str | None = None, purpose: str | None = None,
                   task_id: str | None = None) -> MemoryResult:
        typed = TypedId.parse(entity_id) if isinstance(entity_id, str) else entity_id
        def operation(cid):
            internal = _internal_id(typed)
            entity = self.__runtime.memory.get(internal)
            if entity is None: self._raise_record_state(internal, cid)
            from syune.memory import LifecycleState
            if self.__runtime.memory.lifecycle(internal).state is not LifecycleState.ACTIVE:
                self._raise_record_state(internal, cid)
            from syune.memory import AccessContext, Principal, authorize
            identity = any((user_id, agent_id, service_id))
            access = AccessContext(Principal(user_id, agent_id, organization_id, project_id,
                                             department_id, service_id), purpose, task_id, False) if identity else None
            decision = authorize(getattr(entity, "security", None), access)
            if not decision.allowed: self._raise_auth(decision.code.value, cid, str(typed), type("R", (), {"purpose":purpose})(), "memory_get")
            data = {"typed_entity_id": str(typed), "entity_type": type(entity).__name__, "fields": to_primitive(entity)}
            if include_associations:
                edges = []
                for edge in self.__runtime.memory.associations_for(internal):
                    other_id = edge.target_id if edge.source_id == internal else edge.source_id
                    other = self.__runtime.memory.get(other_id)
                    if other is not None and authorize(getattr(other, "security", None), access).allowed:
                        edges.append(edge)
                    if len(edges) == 32: break
                data["associations"] = to_primitive(tuple(edges))
            return MemoryResult(cid, data)
        return self._call(correlation_id, operation)

    def recall(self, request: PublicRecallRequest | str) -> PublicRecallResult:
        request = PublicRecallRequest(cue=request) if isinstance(request, str) else request
        def operation(cid):
            from syune.retrieval import RecallCue, RecallRequest
            from datetime import datetime
            from syune.retrieval import QueryMode, VerificationPolicy
            from syune.memory import AccessContext, Principal
            parse_time = lambda value: datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
            identity = any((request.user_id, request.agent_id, request.service_id))
            access = AccessContext(Principal(request.user_id, request.agent_id, request.organization_id,
                                             request.project_id, request.department_id, request.service_id),
                                   request.purpose, request.task_id, False) if identity else None
            cue = RecallCue(request.cue, tuple(_internal_id(x) for x in request.entity_ids),
                            tuple(_internal_id(x, SourceId) for x in request.source_ids),
                            tuple(_internal_id(x) for x in request.context_ids), correlation_id=cid,
                            query_mode=QueryMode(request.query_mode), valid_at=parse_time(request.valid_at),
                            knowledge_at=parse_time(request.knowledge_at),
                            verification_policy=VerificationPolicy(request.verification_policy), access_context=access,
                            include_archived=request.include_archived)
            result = self.__runtime.retrieval.recall(RecallRequest(cue, max_results=request.max_results))
            access_events = self.__runtime.retrieval.access_events
            self.__runtime.audit.record(operation_id=cid, correlation_id=cid, operation_type="retrieve",
                outcome="SUCCESS" if result.candidates else "EMPTY",
                authorization_decisions=tuple(event.decision.value for event in access_events[-max(1, len(result.candidates)):]),
                resource_ids=tuple(f"{type(item.entity_id).__name__}:{item.entity_id}" for item in result.candidates))
            return PublicRecallResult(cid, to_primitive(result) | {
                "score_meaning": "recall relevance and activation, not truth probability"})
        return self._call(request.correlation_id, operation)

    def context(self, request: ContextRequest | str) -> ContextResult:
        request = ContextRequest(request) if isinstance(request, str) else request
        recall = PublicRecallRequest(cue=request.cue, max_results=request.max_results,
            correlation_id=request.correlation_id, query_mode=request.query_mode, valid_at=request.valid_at,
            knowledge_at=request.knowledge_at, verification_policy=request.verification_policy,
            user_id=request.user_id, agent_id=request.agent_id, organization_id=request.organization_id,
            project_id=request.project_id, department_id=request.department_id, service_id=request.service_id,
            purpose=request.purpose, task_id=request.task_id)
        def operation(cid):
            from datetime import datetime
            from syune.memory import AccessContext, Principal
            from syune.retrieval import QueryMode, RecallCue, RecallRequest, VerificationPolicy
            parse = lambda value: datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
            identity = any((request.user_id, request.agent_id, request.service_id))
            access = AccessContext(Principal(request.user_id, request.agent_id, request.organization_id,
                request.project_id, request.department_id, request.service_id), request.purpose,
                request.task_id, False) if identity else None
            internal = RecallRequest(RecallCue(text=recall.cue, correlation_id=cid,
                query_mode=QueryMode(recall.query_mode), valid_at=parse(recall.valid_at),
                knowledge_at=parse(recall.knowledge_at), verification_policy=VerificationPolicy(recall.verification_policy),
                access_context=access), max_results=recall.max_results)
            access_start = len(self.__runtime.retrieval.access_events)
            assembled = self.__runtime.context.assemble(internal, max_chars=request.max_chars,
                provenance_mode=request.provenance_mode.value)
            denied = [event for event in self.__runtime.retrieval.access_events[access_start:]
                      if not event.decision.value.startswith("ALLOW_")]
            if not assembled.items and denied:
                self._raise_auth(denied[0].decision.value, cid,
                    f"{type(denied[0].resource_id).__name__}:{denied[0].resource_id}", request, "context")
            return ContextResult(cid, to_primitive(assembled))
        return self._call(request.correlation_id, operation)

    def audit(self, *, limit: int = 100, correlation_id: str | None = None) -> AuditResult:
        return self._call(correlation_id, lambda cid: AuditResult(cid, {
            "events": to_primitive(self.__runtime.audit.query(limit=limit)),
            "context_events": list(self.__runtime.context.audit(limit)),
            "authorization_events": to_primitive(tuple(self.__runtime.retrieval.access_events[-limit:])),
        }))

    def cognize(self, request: PublicCognitiveRequest | str) -> PublicCognitiveResult:
        request = PublicCognitiveRequest(cue=request) if isinstance(request, str) else request
        def operation(cid):
            self.__runtime.enable_research()
            from syune.cognition import CognitiveRequest, ProfileName
            from syune.memory import AccessContext, Principal
            profile = self.__runtime.profiles.by_name(ProfileName(request.profile.upper()))
            identity = any((request.user_id, request.agent_id, request.service_id))
            access = AccessContext(Principal(request.user_id, request.agent_id, request.organization_id,
                                             request.project_id, request.department_id, request.service_id),
                                   request.purpose, request.task_id, False) if identity else None
            internal = CognitiveRequest(CognitiveRequestId.new(), request.cue,
                tuple(_internal_id(x) for x in request.entity_ids), tuple(_internal_id(x, SourceId) for x in request.source_ids),
                tuple(_internal_id(x) for x in request.context_ids), correlation_id=cid,
                diagnostics=request.diagnostics is not DiagnosticsLevel.NONE, activation_profile=profile.id,
                access_context=access)
            return PublicCognitiveResult(cid, to_primitive(self.__runtime.cognition.process(internal)))
        return self._call(request.correlation_id, operation)

    def council(self, request: PublicCouncilRequest) -> PublicCouncilResult:
        def operation(cid):
            self.__runtime.enable_research()
            from syune.cognition import CognitiveRequest, ProfileName
            from syune.council import CouncilMemberSpec, CouncilRequest
            profiles = tuple(self.__runtime.profiles.by_name(ProfileName(name.upper())).id for name in request.members)
            cognitive = CognitiveRequest(CognitiveRequestId.new(), request.cue, correlation_id=cid)
            internal = CouncilRequest(CouncilRequestId.new(), cognitive,
                tuple(CouncilMemberSpec(item) for item in profiles),
                diagnostics=request.diagnostics is not DiagnosticsLevel.NONE, correlation_id=cid)
            return PublicCouncilResult(cid, to_primitive(self.__runtime.council.run(internal)) | {
                "agreement_meaning": "structural convergence, not truth probability"})
        return self._call(request.correlation_id, operation)

    def plan(self, request: PlanRequest | str) -> PlanResult:
        request = PlanRequest(request) if isinstance(request, str) else request
        def operation(cid):
            self.__runtime.enable_research()
            from syune.executive import ExecutiveRequest, Goal, GoalSource
            goal = Goal(GoalId.new(), request.goal, request.success_criteria, source=GoalSource.HOST, correlation_id=cid)
            result = self.__runtime.planner.plan(ExecutiveRequest(ExecutiveRequestId.new(), goal, correlation_id=cid))
            return PlanResult(cid, to_primitive(result) | {"execution_authority": False,
                                                           "approval_does_not_execute": True})
        return self._call(request.correlation_id, operation)


SyuneClient = Syune
