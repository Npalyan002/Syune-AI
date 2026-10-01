from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Protocol


class Baseline(str, Enum):
    MODEL_ONLY = "B0_MODEL_ONLY"
    LONG_CONTEXT = "B1_LONG_CONTEXT"
    BASIC_RAG = "B2_BASIC_RAG"
    CURRENT_SYUNE = "B3_CURRENT_SYUNE"
    MEM0 = "B4_MEM0"
    ZEP = "B5_ZEP"
    LETTA = "B6_LETTA"


class StateMode(str, Enum):
    FRESH = "FRESH"
    PERSISTENT = "PERSISTENT"
    SHARED = "SHARED"


@dataclass(frozen=True)
class Record:
    record_id: str
    text: str
    source_id: str
    locator: str
    principal: str = "alpha"
    agent: str = "agent-a"
    valid_from: str | None = None
    valid_to: str | None = None
    verified: bool = True


@dataclass(frozen=True)
class Edge:
    source_id: str
    target_id: str
    relation: str
    strength: float = 1.0


@dataclass(frozen=True)
class Case:
    case_id: str
    family: str
    query: str
    records: tuple[Record, ...]
    relevant_ids: tuple[str, ...]
    forbidden_ids: tuple[str, ...] = ()
    edges: tuple[Edge, ...] = ()
    state_mode: StateMode = StateMode.FRESH
    top_k: int = 5
    measures: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class Dataset:
    dataset_id: str
    dataset_version: str
    seed: int
    generator_version: str
    created_at: str
    content_hash: str
    tier: str
    case_count: int
    cases: tuple[Case, ...]


@dataclass
class AdapterResponse:
    retrieved_ids: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    input_tokens: int | None = None
    output_tokens: int | None = None
    error: dict[str, str] | None = None
    warnings: list[str] = field(default_factory=list)
    provenance_ids: list[str] = field(default_factory=list)


class BenchmarkAdapter(Protocol):
    baseline: Baseline
    adapter_version: str
    status: str
    unsupported_capabilities: tuple[str, ...]

    def prepare(self) -> None: ...
    def reset(self) -> None: ...
    def ingest(self, records: tuple[Record, ...], edges: tuple[Edge, ...]) -> None: ...
    def query(self, text: str, top_k: int) -> AdapterResponse: ...
    def execute_task(self, case: Case) -> AdapterResponse: ...
    def export_state_metrics(self) -> dict[str, int | float | None]: ...
    def cleanup(self) -> None: ...


def plain(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {key: plain(item) for key, item in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    return value
