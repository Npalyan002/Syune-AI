"""Provider-neutral contracts for reliable model execution."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping


class CallRole(str, Enum):
    DECISION = "DECISION"
    SYNTHESIS = "SYNTHESIS"
    KNOWLEDGE_CONSTRUCTION = "KNOWLEDGE_CONSTRUCTION"
    VERIFICATION = "VERIFICATION"
    CLASSIFICATION = "CLASSIFICATION"
    EXTRACTION = "EXTRACTION"
    PLANNING = "PLANNING"
    SCORING = "SCORING"
    SUMMARIZATION = "SUMMARIZATION"
    REPAIR = "REPAIR"
    GENERAL = "GENERAL"


class Capability(str, Enum):
    TEXT_GENERATION = "text_generation"
    STRUCTURED_OUTPUT = "structured_output"
    NATIVE_JSON_SCHEMA = "native_json_schema"
    TOOL_CALLING = "tool_calling"
    STREAMING = "streaming"
    REASONING_CONTROLS = "reasoning_controls"
    VISION = "vision"
    AUDIO = "audio"
    USAGE_TELEMETRY = "usage_telemetry"
    PROVIDER_REQUEST_ID = "provider_request_id"


class StructuredOutputStrategy(str, Enum):
    PLAIN_JSON_PROMPT = "PLAIN_JSON_PROMPT"
    NATIVE_STRUCTURED_OUTPUT = "NATIVE_STRUCTURED_OUTPUT"
    COMPACT_SCHEMA = "COMPACT_SCHEMA"
    REPAIR_CALL = "REPAIR_CALL"
    TWO_STAGE_GENERATION = "TWO_STAGE_GENERATION"


class FailureClass(str, Enum):
    AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"
    AUTHORIZATION_FAILURE = "AUTHORIZATION_FAILURE"
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    CONNECTION_FAILURE = "CONNECTION_FAILURE"
    PROVIDER_5XX = "PROVIDER_5XX"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
    EMPTY_OUTPUT = "EMPTY_OUTPUT"
    TRUNCATED_OUTPUT = "TRUNCATED_OUTPUT"
    REFUSAL = "REFUSAL"
    INVALID_JSON = "INVALID_JSON"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    SEMANTIC_INVALID = "SEMANTIC_INVALID"
    USAGE_UNKNOWN = "USAGE_UNKNOWN"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"
    CONCURRENCY_EXHAUSTED = "CONCURRENCY_EXHAUSTED"
    REMOTE_COMPLETION_AMBIGUOUS = "REMOTE_COMPLETION_AMBIGUOUS"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    UNKNOWN_PROVIDER_FAILURE = "UNKNOWN_PROVIDER_FAILURE"


class ExecutionState(str, Enum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    BUDGET_RESERVED = "BUDGET_RESERVED"
    REQUEST_STARTED = "REQUEST_STARTED"
    HTTP_RESPONSE_RECEIVED = "HTTP_RESPONSE_RECEIVED"
    RAW_PERSISTED = "RAW_PERSISTED"
    CLASSIFIED = "CLASSIFIED"
    PARSED = "PARSED"
    SCHEMA_VALIDATED = "SCHEMA_VALIDATED"
    SEMANTIC_VALIDATED = "SEMANTIC_VALIDATED"
    COMMITTED = "COMMITTED"
    FAILED_TERMINAL = "FAILED_TERMINAL"


class Quality(str, Enum):
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    FALLBACK = "FALLBACK"


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"


class FallbackMode(str, Enum):
    EXACT_MODEL = "EXACT_MODEL"
    CAPABILITY_EQUIVALENT = "CAPABILITY_EQUIVALENT"


class UsageStatus(str, Enum):
    MEASURED = "MEASURED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ModelCapabilities:
    values: frozenset[Capability]
    context_size: int | None = None
    max_output_tokens: int | None = None

    def supports(self, required: frozenset[Capability]) -> bool:
        return required <= self.values


@dataclass(frozen=True)
class ModelMetadata:
    provider: str
    model: str
    version: str | None
    capabilities: ModelCapabilities
    input_price_per_million: float | None = None
    output_price_per_million: float | None = None


@dataclass(frozen=True)
class TimeoutPolicy:
    connect_seconds: float = 10.0
    read_seconds: float = 120.0
    overall_seconds: float = 180.0

    def __post_init__(self) -> None:
        if min(self.connect_seconds, self.read_seconds, self.overall_seconds) <= 0:
            raise ValueError("timeouts must be positive")


@dataclass(frozen=True)
class RetryPolicy:
    name: str = "default-v1"
    max_attempts: int = 2
    retryable: frozenset[FailureClass] = frozenset({
        FailureClass.RATE_LIMIT, FailureClass.TIMEOUT, FailureClass.CONNECTION_FAILURE,
        FailureClass.PROVIDER_5XX, FailureClass.TRUNCATED_OUTPUT,
    })
    backoff_seconds: tuple[float, ...] = (0.5,)
    repair_eligible: frozenset[FailureClass] = frozenset({
        FailureClass.INVALID_JSON, FailureClass.SCHEMA_INVALID,
    })
    fallback_eligible: frozenset[FailureClass] = frozenset({
        FailureClass.RATE_LIMIT, FailureClass.TIMEOUT, FailureClass.PROVIDER_5XX,
        FailureClass.MODEL_UNAVAILABLE, FailureClass.PROVIDER_UNAVAILABLE,
        FailureClass.CAPABILITY_UNAVAILABLE,
    })

    def __post_init__(self) -> None:
        if not 1 <= self.max_attempts <= 10:
            raise ValueError("max_attempts must be finite and between 1 and 10")


@dataclass(frozen=True)
class DataPolicy:
    allow_external: bool = True
    allowed_providers: frozenset[str] | None = None
    local_only: bool = False


@dataclass(frozen=True)
class BudgetLimit:
    scope: str
    scope_id: str
    max_calls: int | None = None
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
    max_cost_usd: float | None = None


SemanticValidator = Callable[[Any], None]


@dataclass(frozen=True)
class ModelExecutionRequest:
    logical_call_id: str
    purpose: str
    messages: tuple[Mapping[str, Any], ...]
    call_role: CallRole = CallRole.GENERAL
    required_capabilities: frozenset[Capability] = frozenset({Capability.TEXT_GENERATION})
    structured_output_schema: Mapping[str, Any] | None = None
    semantic_validator: SemanticValidator | None = field(default=None, compare=False, repr=False)
    preferred_model: str | None = None
    allowed_models: frozenset[str] | None = None
    allowed_providers: frozenset[str] | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None
    timeout: TimeoutPolicy = TimeoutPolicy()
    retry_policy: RetryPolicy = RetryPolicy()
    repair_policy_reference: str | None = None
    fallback_policy_reference: str | None = None
    strategy: StructuredOutputStrategy = StructuredOutputStrategy.NATIVE_STRUCTURED_OUTPUT
    fallback_mode: FallbackMode = FallbackMode.EXACT_MODEL
    budget_limits: tuple[BudgetLimit, ...] = ()
    principal: str | None = None
    access_context: Mapping[str, Any] = field(default_factory=dict)
    data_policy: DataPolicy = DataPolicy()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    exact_model: bool = False
    accept_degraded: bool = True

    def __post_init__(self) -> None:
        if not self.logical_call_id.strip() or not self.purpose.strip() or not self.messages:
            raise ValueError("logical_call_id, purpose, and messages are required")
        if self.structured_output_schema is not None and Capability.STRUCTURED_OUTPUT not in self.required_capabilities:
            object.__setattr__(self, "required_capabilities", self.required_capabilities | {Capability.STRUCTURED_OUTPUT})


@dataclass(frozen=True)
class ProviderRequest:
    gateway_execution_id: str
    provider_attempt_id: str
    request: ModelExecutionRequest
    provider: str
    model: str
    max_output_tokens: int


@dataclass(frozen=True)
class RawProviderResponse:
    http_status: int | None
    raw_body: str
    provider_request_id: str | None = None
    resolved_model: str | None = None
    model_version: str | None = None
    finish_reason: str | None = None
    refusal: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: float = 0.0
    retry_after_seconds: float | None = None
    response_received: bool = True
    sanitized_metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AttemptEvidence:
    gateway_execution_id: str
    logical_call_id: str
    provider_attempt_id: str
    attempt_number: int
    provider: str
    requested_model: str
    resolved_model: str | None
    model_version: str | None
    provider_request_id: str | None
    http_status: int | None
    finish_reason: str | None
    raw_response_content: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: float
    timestamp: str
    failure_class: FailureClass | None
    state: ExecutionState
    usage_status: UsageStatus
    reserved_cost_usd: float
    actual_cost_usd: float | None
    quality: Quality
    policy_version: str


@dataclass(frozen=True)
class ModelExecutionResult:
    gateway_execution_id: str
    logical_call_id: str
    semantic_commit_id: str | None
    state: ExecutionState
    value: Any = None
    failure: FailureClass | None = None
    message: str | None = None
    provider: str | None = None
    requested_model: str | None = None
    resolved_model: str | None = None
    model_version: str | None = None
    provider_request_id: str | None = None
    attempts: int = 0
    used_repair: bool = False
    used_fallback: bool = False
    quality: Quality = Quality.NORMAL
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    policy_version: str = "phase29-v1"
    audit: Mapping[str, Any] = field(default_factory=dict)

    @property
    def committed(self) -> bool:
        return self.state is ExecutionState.COMMITTED
