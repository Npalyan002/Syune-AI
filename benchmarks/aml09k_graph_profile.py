"""Bounded graph authorization/repository microprofile for AML-09K."""
from __future__ import annotations

import json
import argparse
from datetime import datetime, timezone
from statistics import median
from time import perf_counter

from syune.core import AssociationId, Confidence, ObservationId, ProvenanceId, SourceId
from syune.memory import (
    AccessContext, Association, InMemoryReferenceRepository, Observation, Principal,
    Provenance, SecurityEnvelope, Source, authorize,
)
from syune.retrieval import InvertedSeedIndex

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def timed(fn):
    values = []
    for _ in range(31):
        started = perf_counter(); fn(); values.append((perf_counter() - started) * 1000)
    return {"median_ms": round(median(values), 4), "min_ms": round(min(values), 4),
            "max_ms": round(max(values), 4)}


repo = InMemoryReferenceRepository()
source = Source(SourceId.new(), "synthetic", "aml09k-graph-profile", NOW)
provenance = Provenance(ProvenanceId.new(), source.id, NOW); repo.put(source)
security = SecurityEnvelope(owner="user:bob", agent_scope="agent-b")
nodes = []
for number in range(513):
    item = Observation(ObservationId.new(), f"graph node {number}", "text", provenance,
                       NOW, NOW, Confidence(1), security=security)
    repo.put(item); nodes.append(item)
for number in range(512):
    repo.add_association(Association(AssociationId.new(), nodes[number].id, nodes[number + 1].id,
                                     "associated_with", provenance, Confidence(1), NOW, 1.0))
index = InvertedSeedIndex(repo); index.rebuild()
access = AccessContext(Principal("bob", "agent-b"), legacy_local_compatible=False)
edges = tuple(edge for node in nodes for edge in repo.associations_for(node.id))[:512]


def authorize_endpoints():
    for edge in edges:
        assert authorize(index.entries[edge.source_id].security, access).allowed
        assert authorize(index.entries[edge.target_id].security, access).allowed


def repository_edges():
    for node in nodes:
        repo.associations_for(node.id)


parser = argparse.ArgumentParser(); parser.add_argument("--output", required=True)
args = parser.parse_args()
report = {"edges": len(edges), "endpoint_authorization": timed(authorize_endpoints),
          "repository_association_access": timed(repository_edges)}
with open(args.output, "w", encoding="utf-8") as handle:
    json.dump(report, handle, indent=2); handle.write("\n")
print(json.dumps(report, indent=2))
