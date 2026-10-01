"""Deterministic synthetic lifecycle growth comparison (Phase 23)."""
from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from statistics import quantiles
from uuid import UUID

from syune.core import Confidence, ObservationId, ProvenanceId, SourceId
from syune.memory import (InMemoryReferenceRepository, LifecycleService, MemoryClass,
                          Observation, Provenance, Source)
from syune.retrieval import InvertedSeedIndex, RecallCue, RecallRequest, RetrievalService


def run(interactions: int = 1000) -> dict[str, object]:
    at=datetime(2026,1,1,tzinfo=timezone.utc); sid=SourceId(UUID(int=1))
    provenance=Provenance(ProvenanceId(UUID(int=2)),sid,at)
    off=InMemoryReferenceRepository(); on=InMemoryReferenceRepository()
    off.put(Source(sid,"synthetic","phase23",at)); on.put(Source(sid,"synthetic","phase23",at))
    lifecycle=LifecycleService(on); started=perf_counter()
    for number in range(interactions):
        # Forty percent useful unique observations, sixty percent exact repeated evidence.
        content=f"useful fact {number}" if number%5 in (0,1) else f"repeated fact {number%20}"
        off.put(Observation(ObservationId(UUID(int=1000+number)),content,"text",provenance,at,at,Confidence(.8)))
        lifecycle.register(Observation(ObservationId(UUID(int=100000+number)),content,"text",provenance,at,at,Confidence(.8)),MemoryClass.SEMANTIC)
    maintenance_ms=(perf_counter()-started)*1000
    off_index=InvertedSeedIndex(off); on_index=InvertedSeedIndex(on)
    off_index.rebuild(); on_index.rebuild()
    def quality(repo,index):
        service=RetrievalService(repo,index); samples=[]; result=None
        for _ in range(200):
            tick=perf_counter(); result=service.recall(RecallRequest(RecallCue(text="useful fact 0"),max_results=8)); samples.append((perf_counter()-tick)*1000)
        return {"retrieval_hits":len(result.candidates),"context_size":len(result.working_memory),
                "retrieval_p95_ms":quantiles(samples,n=20)[18]}
    metrics=on.lifecycle_metrics()
    return {"kind":"synthetic_replay","interactions":interactions,
            "lifecycle_off":{"total":off.entity_count(),"active":off.entity_count(),"index":len(off_index.entries),**quality(off,off_index)},
            "lifecycle_on":{"total":on.entity_count(),"active":metrics.active,"archived":metrics.archived,
                            "forgotten":metrics.forgotten,"index":len(on_index.entries),**quality(on,on_index)},
            "active_growth_reduction":1-(metrics.active/max(1,off.entity_count())),
            "maintenance_ms":maintenance_ms,"maintenance_ms_per_interaction":maintenance_ms/interactions}


if __name__ == "__main__":
    import json
    print(json.dumps(run(),indent=2,sort_keys=True))
