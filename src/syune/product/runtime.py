"""One lifecycle-managed service graph for local product commands."""
from __future__ import annotations

from dataclasses import dataclass

import warnings
from syune.context import ContextService
from syune.audit import SQLiteAuditStore
from syune.memory import SQLiteMemoryRepository
from syune.retrieval import InvertedSeedIndex, RetrievalService
from syune.study import SqliteStudyRegistry, StudyService
from .config import SyuneConfig
from .state import DATABASES, load_metadata, missing_databases, record_successful_open


@dataclass(slots=True)
class SyuneRuntime:
    config: SyuneConfig
    metadata: object
    memory: SQLiteMemoryRepository
    study_registry: SqliteStudyRegistry
    index: InvertedSeedIndex
    retrieval: RetrievalService
    context: ContextService
    study: StudyService
    audit: SQLiteAuditStore
    learning: object | None = None
    execution: object | None = None
    profiles: object | None = None
    cognition: object | None = None
    council: object | None = None
    planner: object | None = None
    closed: bool = False

    @classmethod
    def open(cls, config: SyuneConfig) -> "SyuneRuntime":
        root = config.state.root
        metadata = load_metadata(root)
        missing = missing_databases(root)
        if missing:
            raise ValueError("initialized state is missing component databases: " + ", ".join(missing))
        opened = []
        try:
            memory = SQLiteMemoryRepository(root / DATABASES["memory"]); opened.append(memory)
            registry = SqliteStudyRegistry(root / DATABASES["study_perception"]); opened.append(registry)
            index = InvertedSeedIndex(memory); index.rebuild()
            retrieval = RetrievalService(memory, index)
            audit = SQLiteAuditStore(root / DATABASES["audit"]); opened.append(audit)
            runtime = cls(config, metadata, memory, registry, index, retrieval,
                          ContextService(memory, retrieval, audit), StudyService(registry, memory), audit)
            if config.features.learning:
                from syune.learning import SQLiteLearningStore, StorePlasticityView
                runtime.learning = SQLiteLearningStore(root / DATABASES["learning"]); opened.append(runtime.learning)
                runtime.retrieval = RetrievalService(memory, index, plasticity=StorePlasticityView(runtime.learning))
                runtime.context = ContextService(memory, runtime.retrieval, audit)
            if config.features.research_cognition: runtime.enable_research(warn=False)
            runtime.metadata = record_successful_open(root, metadata)
            return runtime
        except Exception:
            for item in reversed(opened): item.close()
            raise

    def close(self) -> None:
        if self.closed: return
        if self.execution is not None: self.execution.close()
        if self.learning is not None: self.learning.close()
        self.audit.close()
        self.study_registry.close()
        self.memory.close()
        self.closed = True

    def __enter__(self) -> "SyuneRuntime": return self
    def __exit__(self, *_: object) -> None: self.close()

    def health(self) -> dict[str, object]:
        components = {
            "memory": "HEALTHY", "study": "HEALTHY", "authorization": "HEALTHY",
            "retrieval": "HEALTHY" if self.index.ready else "UNHEALTHY",
            "context": "HEALTHY", "audit": "HEALTHY", "model_gateway": "AVAILABLE",
            "state": "HEALTHY",
        }
        overall = "HEALTHY" if all(x in ("HEALTHY", "AVAILABLE", "DISABLED") for x in components.values()) else "UNHEALTHY"
        return {"overall": overall, "components": components}

    def enable_research(self, *, warn: bool = True) -> None:
        if self.cognition is not None: return
        if warn: warnings.warn("Cognitive/council/planner APIs are research compatibility surfaces; use context()",
                               DeprecationWarning, stacklevel=2)
        from syune.cognition import CognitiveService, ProfileRegistry
        from syune.council import CouncilService
        from syune.executive import ExecutiveService
        self.profiles = ProfileRegistry()
        self.cognition = CognitiveService(self.memory, self.retrieval, self.profiles)
        self.council = CouncilService(self.cognition)
        self.planner = ExecutiveService()
