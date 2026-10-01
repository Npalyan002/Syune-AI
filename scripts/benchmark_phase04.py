"""Synthetic Phase 04 baseline; read-only recall, no external corpus."""
from __future__ import annotations

import argparse
import json
import platform
from datetime import datetime, timezone
from statistics import median
from time import perf_counter
from uuid import UUID

from syune.core import AssociationId, ConceptId, Confidence, ProvenanceId, SourceId
from syune.memory import Association, Concept, InMemoryReferenceRepository, Provenance, Source
from syune.retrieval import InvertedSeedIndex, RecallCue, RecallRequest, RetrievalService


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]


def run(size: int, repeats: int) -> dict:
    at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    repo = InMemoryReferenceRepository()
    sid = SourceId(UUID(int=1))
    provenance = Provenance(ProvenanceId(UUID(int=2)), sid, at)
    repo.put(Source(sid, "synthetic", "benchmark", at))
    nodes = []
    for n in range(size):
        entity = Concept(ConceptId(UUID(int=100 + n)), f"topic{n} shared planning", provenance, Confidence(0.5), at)
        repo.put(entity)
        nodes.append(entity)
    for n in range(size - 1):
        repo.add_association(Association(AssociationId(UUID(int=100000 + n)), nodes[n].id, nodes[n + 1].id,
                                         "associated_with", provenance, Confidence(0.5), at, 0.5))
    index = InvertedSeedIndex(repo)
    build_start = perf_counter()
    index.rebuild()
    build_ms = (perf_counter() - build_start) * 1000
    service = RetrievalService(repo, index)
    cues = {
        "exact_id": RecallCue(entity_ids=(nodes[size // 2].id,)),
        "lexical": RecallCue(text=f"topic{size // 2}"),
        "association": RecallCue(entity_ids=(nodes[size // 2].id, nodes[size // 2 + 2].id)),
        "full": RecallCue(text=f"topic{size // 2}", context_ids=(nodes[size // 2 + 2].id,)),
    }
    metrics = {}
    for name, cue in cues.items():
        samples = []
        for _ in range(repeats):
            start = perf_counter()
            service.recall(RecallRequest(cue))
            samples.append((perf_counter() - start) * 1000)
        metrics[name] = {"p50_ms": round(median(samples), 3), "p95_ms": round(percentile(samples, 0.95), 3)}
    return {"entities": size + 1, "associations": size - 1, "index_build_ms": round(build_ms, 3), "recall": metrics}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", nargs="+", type=int, default=[100, 1000, 10000])
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    if args.repeats < 1 or any(size < 5 for size in args.sizes):
        parser.error("repeats >= 1 and sizes >= 5 required")
    print(json.dumps({"python": platform.python_version(), "platform": platform.platform(),
                      "repeats": args.repeats, "results": [run(size, args.repeats) for size in args.sizes]}, indent=2))
