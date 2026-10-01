"""Versioned evaluation and readiness contracts, separate from cognitive truth."""
from dataclasses import dataclass
from enum import Enum
from math import isfinite


class Category(str, Enum):
    ARCHITECTURE = "ARCHITECTURE"
    MEMORY = "MEMORY"
    STUDY = "STUDY"
    RETRIEVAL = "RETRIEVAL"
    LEARNING = "LEARNING"
    COGNITION = "COGNITION"
    PROFILES = "PROFILES"
    MULTIMODAL = "MULTIMODAL"
    COUNCIL = "COUNCIL"
    PLANNING = "PLANNING"
    EXECUTION = "EXECUTION"
    RESILIENCE = "RESILIENCE"
    PERFORMANCE = "PERFORMANCE"
    SECURITY = "SECURITY"
    REGRESSION = "REGRESSION"


class Health(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


class Readiness(str, Enum):
    READY = "READY"
    READY_WITH_LIMITATIONS = "READY_WITH_LIMITATIONS"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class EvalMetric:
    name: str
    value: float
    unit: str = "count"

    def __post_init__(self):
        if not self.name or not isfinite(self.value):
            raise ValueError("finite named metric required")


@dataclass(frozen=True)
class EvalExpectation:
    invariant: str
    metric: str
    minimum: float
    maximum: float

    def __post_init__(self):
        if not self.invariant or not self.metric or not all(map(isfinite, (self.minimum, self.maximum))) or self.minimum > self.maximum:
            raise ValueError("bounded invariant expectation required")


@dataclass(frozen=True)
class EvalCase:
    id: str
    category: Category
    description: str
    fixture: str
    expectations: tuple[EvalExpectation, ...]
    evidence: tuple[str, ...]

    def __post_init__(self):
        if not all((self.id, self.description, self.fixture, self.expectations, self.evidence)):
            raise ValueError("complete case contract required")


@dataclass(frozen=True)
class EvalSuite:
    name: str
    cases: tuple[EvalCase, ...]
    version: str = "1"

    def __post_init__(self):
        if not self.cases or len({c.id for c in self.cases}) != len(self.cases):
            raise ValueError("nonempty distinct cases required")


@dataclass(frozen=True)
class EvalObservation:
    case_id: str
    metrics: tuple[EvalMetric, ...]
    evidence: tuple[str, ...]
    duration_ms: float


@dataclass(frozen=True)
class EvalFailure:
    case_id: str
    invariant: str
    reason: str


@dataclass(frozen=True)
class EvalRun:
    suite: str
    version: str
    trace_id: str
    started_at: str
    runtime: tuple[tuple[str, str], ...]
    observations: tuple[EvalObservation, ...]
    failures: tuple[EvalFailure, ...]


@dataclass(frozen=True)
class EvalReport:
    run: EvalRun
    health: Health
    readiness: Readiness
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class RegressionBaseline:
    version: str
    platform: str
    metrics: tuple[EvalMetric, ...]
    relative_tolerance: float = 0.50
    absolute_tolerance: float = 5.0

    def __post_init__(self):
        if self.relative_tolerance < 0 or self.absolute_tolerance < 0:
            raise ValueError("nonnegative tolerances required")
