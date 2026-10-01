"""Safe structural encoding: PerceivedBlock -> Observation -> MemoryTrace."""
from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from syune.core import (
    Confidence, MemoryTraceId, ObservationId, ProvenanceId,
    SourceId, SourceVersionId, utc_now,
)
from syune.memory import (
    MemoryTrace, Observation, Provenance, Source,
)
from syune.memory.repository import MemoryRepository
from .model import PerceivedBlock, SourceRevisionId

ENCODER_VERSION = "1"


def observation_id(revision_id: SourceRevisionId, block_key: str) -> ObservationId:
    return ObservationId(uuid5(NAMESPACE_URL, f"syune:observation:{revision_id}:{block_key}"))


def trace_id(revision_id: SourceRevisionId, block_key: str) -> MemoryTraceId:
    return MemoryTraceId(uuid5(NAMESPACE_URL, f"syune:trace:{revision_id}:{block_key}"))


class StudyEncoder:
    """Encodes perception quality, never factual truth."""

    def __init__(self, memory: MemoryRepository):
        self.memory = memory

    def ensure_source(self, source_id: SourceId, source_version_id: SourceVersionId,
                      display_name: str, digest: str, locator_uri: str,kind:str="local_file",media_type:str|None=None) -> None:
        if not self.memory.exists(source_id):
            self.memory.put(Source(
                source_id, kind, display_name, utc_now(),
                source_version_id=source_version_id, fingerprint=digest,
                locator_uri=locator_uri,media_type=media_type,
            ))

    def encode(self, block: PerceivedBlock, source_id: SourceId,
               source_version_id: SourceVersionId, pipeline_version: str) -> tuple[ObservationId, MemoryTraceId]:
        now = utc_now()
        provenance = Provenance(
            ProvenanceId(uuid5(NAMESPACE_URL, f"syune:provenance:{block.source_revision_id}:{block.key}")),
            source_id, now, source_version_id=source_version_id,
            locator=block.locator, process_id=(f"study:perception:{block.perception_run_id}:{block.perceived_segment_id}:{block.perception_method}" if block.perception_run_id else "study:text-extraction"),
            pipeline_version=pipeline_version,
        )
        oid = observation_id(block.source_revision_id, block.key)
        tid = trace_id(block.source_revision_id, block.key)
        entities = []
        if not self.memory.exists(oid):
            entities.append(Observation(
                oid, block.text, block.content_kind, provenance, now, now,
                extraction_confidence=None,
            ))
        if not self.memory.exists(tid):
            # This value records successful structural encoding, not truth of the text.
            entities.append(MemoryTrace(tid, oid, now, provenance, Confidence(1.0), now))
        if entities:
            self.memory.put_many(tuple(entities))
        return oid, tid
