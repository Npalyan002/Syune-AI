"""Synthetic Phase 07 append, consolidation, overlay lookup, and retrieval overhead benchmark."""
import json
import math
import statistics
import tempfile
from pathlib import Path
from time import perf_counter

from syune.core import Confidence, LearningSignalId, ObservationId, ProvenanceId, SourceId, utc_now
from syune.learning import (
    LearningService, LearningSignal, LearningSignalKind, LearningSource,
    LearningTarget, PlasticityConfig, PlasticityPolicy, SQLiteLearningStore,
    StorePlasticityView,
)
from syune.memory import InMemoryReferenceRepository, Observation, Provenance, Source
from syune.retrieval import InvertedSeedIndex, RecallCue, RecallRequest, RetrievalService


def percentile(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, max(0, math.ceil(len(values) * p) - 1))]


def single(size):
    memory = InMemoryReferenceRepository(); at = utc_now(); source = Source(SourceId.new(), "synthetic", "benchmark", at)
    provenance = Provenance(ProvenanceId.new(), source.id, at)
    entity = Observation(ObservationId.new(), "phase seven benchmark marker", "text", provenance, at, at, Confidence(0.5))
    memory.put(source); memory.put(entity); index = InvertedSeedIndex(memory); index.rebuild()
    with tempfile.TemporaryDirectory() as directory, SQLiteLearningStore(Path(directory) / "learning.sqlite3") as store:
        policy = PlasticityPolicy(PlasticityConfig(max_signals_per_batch=size, max_proposals_per_batch=size))
        learning = LearningService(memory, store, policy)
        started = perf_counter()
        for number in range(size):
            learning.record(LearningSignal(LearningSignalId.new(), LearningSignalKind.POSITIVE_OUTCOME, at,
                (LearningTarget(entity.id),), LearningSource.SYSTEM_TEST, f"benchmark-{number}", ProvenanceId.new()))
        append_seconds = perf_counter() - started
        result = learning.consolidate_once()
        lookups = []
        for _ in range(100):
            tick = perf_counter(); store.state(LearningTarget(entity.id).key); lookups.append((perf_counter() - tick) * 1000)
        cue = RecallRequest(RecallCue(text="phase seven benchmark marker"))
        base = RetrievalService(memory, index); learned = RetrievalService(memory, index, plasticity=StorePlasticityView(store))
        base_times, learned_times = [], []
        for _ in range(30):
            tick = perf_counter(); base.recall(cue); base_times.append((perf_counter() - tick) * 1000)
            tick = perf_counter(); learned.recall(cue); learned_times.append((perf_counter() - tick) * 1000)
        return {"signals": size, "append_per_second": size / append_seconds,
                "append_p50_ms": statistics.median(learning.append_latencies_ms),
                "append_p95_ms": percentile(learning.append_latencies_ms, .95),
                "consolidation_total_ms": result.batch.total_ms + result.apply_ms,
                "proposal_ms": result.proposal_ms, "apply_ms": result.apply_ms,
                "overlay_lookup_p50_ms": statistics.median(lookups), "overlay_lookup_p95_ms": percentile(lookups, .95),
                "retrieval_base_p50_ms": statistics.median(base_times),
                "retrieval_learned_p50_ms": statistics.median(learned_times),
                "retrieval_overhead_p50_ms": statistics.median(learned_times) - statistics.median(base_times)}


def run(size, repeats=3):
    results = [single(size) for _ in range(repeats)]
    summary = {"signals": size, "repeats": repeats}
    for key in results[0]:
        if key == "signals": continue
        values = [result[key] for result in results]
        summary[key] = statistics.median(values)
        if key == "consolidation_total_ms":
            summary["consolidation_p95_ms"] = percentile(values, .95)
    return summary


if __name__ == "__main__":
    print(json.dumps([run(size) for size in (100, 1000, 10000)], indent=2))
