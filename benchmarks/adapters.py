from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from time import perf_counter
from uuid import NAMESPACE_URL, uuid5

from syune.core import AssociationId, Confidence, ObservationId, ProvenanceId, SourceId
from syune.memory import (
    AccessContext, Association, InMemoryReferenceRepository, Observation, Principal, Provenance,
    SecurityEnvelope, Source, SourceLocator, TruthMetadata, TruthState,
)
from syune.retrieval import InvertedSeedIndex, RecallCue, RecallRequest, RetrievalConfig, RetrievalService
from syune.core import utc_now

from .model import AdapterResponse, Baseline, Case, Edge, Record

_TOKEN = re.compile(r"\w+", re.UNICODE)


def _tokens(text: str) -> set[str]:
    return {match.group().casefold() for match in _TOKEN.finditer(text)}


class NotConfiguredAdapter:
    adapter_version = "1.0.0"
    status = "NOT_CONFIGURED"
    unsupported_capabilities = ("provider_execution",)

    def __init__(self, baseline: Baseline, reason: str):
        self.baseline, self.reason = baseline, reason

    def prepare(self) -> None: pass
    def reset(self) -> None: pass
    def ingest(self, records: tuple[Record, ...], edges: tuple[Edge, ...]) -> None: pass
    def query(self, text: str, top_k: int) -> AdapterResponse:
        return AdapterResponse(error={"category": "unsupported_capability", "message": self.reason})
    def execute_task(self, case: Case) -> AdapterResponse: return self.query(case.query, case.top_k)
    def export_state_metrics(self) -> dict[str, int]: return {"records": 0, "bytes": 0}
    def cleanup(self) -> None: pass


class BasicRagAdapter:
    baseline = Baseline.BASIC_RAG
    adapter_version = "1.0.0"
    status = "READY"
    unsupported_capabilities = ("authorization", "temporal_truth", "learning", "compression", "graph_traversal")

    def __init__(self) -> None: self._records: dict[str, Record] = {}
    def prepare(self) -> None: self.reset()
    def reset(self) -> None: self._records = {}
    def ingest(self, records: tuple[Record, ...], edges: tuple[Edge, ...]) -> None: self._records.update((r.record_id, r) for r in records)
    def query(self, text: str, top_k: int) -> AdapterResponse:
        started, query = perf_counter(), _tokens(text)
        ranked = []
        for record in self._records.values():
            overlap = len(query & _tokens(record.text))
            if overlap:
                ranked.append((overlap / max(1, len(query)), record.record_id))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return AdapterResponse([item[1] for item in ranked[:top_k]], (perf_counter() - started) * 1000,
                               input_tokens=sum(len(_tokens(r.text)) for r in self._records.values()) + len(query), output_tokens=0,
                               provenance_ids=[self._records[item[1]].source_id for item in ranked[:top_k]])
    def execute_task(self, case: Case) -> AdapterResponse: return self.query(case.query, case.top_k)
    def export_state_metrics(self) -> dict[str, int]: return {"records": len(self._records), "bytes": sum(len(r.text.encode()) for r in self._records.values())}
    def cleanup(self) -> None: self.reset()


class CurrentSyuneAdapter:
    baseline = Baseline.CURRENT_SYUNE
    adapter_version = "1.0.0"
    status = "READY"
    unsupported_capabilities = ("authorization", "verified_learning_transfer", "cognitive_compression")

    def __init__(self) -> None: self.reset()
    @staticmethod
    def _uuid(kind: str, value: str): return uuid5(NAMESPACE_URL, f"phase18:{kind}:{value}")
    def prepare(self) -> None: self.reset()
    def reset(self) -> None:
        self.memory = InMemoryReferenceRepository()
        self._ids: dict[str, ObservationId] = {}
        self._records: dict[str, Record] = {}
        self.index = InvertedSeedIndex(self.memory)
        self.index.rebuild()
        self.service = RetrievalService(self.memory, self.index, RetrievalConfig(max_results=32, working_memory_capacity=16))
    def ingest(self, records: tuple[Record, ...], edges: tuple[Edge, ...]) -> None:
        now = utc_now()
        prior: dict[str, tuple[ObservationId, str, bool]] = {}
        for position, record in enumerate(records):
            source_id = SourceId(self._uuid("source", record.source_id))
            provenance = Provenance(ProvenanceId(self._uuid("provenance", record.record_id)), source_id, now, locator=SourceLocator(span=record.locator))
            self.memory.put(Source(source_id, "benchmark", record.source_id, now, locator_uri=record.locator))
            observation_id = ObservationId(self._uuid("observation", record.record_id))
            text = record.text.strip().rstrip(".")
            normalized = re.sub(r"^(verified|unverified)\s+", "", text, flags=re.I)
            negative = bool(re.search(r"\b(?:does not|not)\b", normalized, re.I))
            if re.search(r"\bis\b", normalized, re.I):
                left, value = re.split(r"\bis\b", normalized, maxsplit=1, flags=re.I)
                fact_key = re.sub(r"\bcurrent\b", "", left, flags=re.I).strip().casefold()
                fact_value = value.strip().casefold()
            elif " support" in normalized.casefold():
                key_text = re.sub(r"\bdoes not\b", "", normalized, flags=re.I)
                fact_key = " ".join(re.sub(r"\bsupports\b", "support", key_text, flags=re.I).split()).casefold()
                fact_value = "false" if negative else "true"
            else:
                fact_key, fact_value = normalized.casefold(), normalized.casefold()
            valid_from = datetime.fromisoformat(record.valid_from).replace(tzinfo=timezone.utc) if record.valid_from else None
            valid_until = datetime.fromisoformat(record.valid_to).replace(tzinfo=timezone.utc) + timedelta(days=1) if record.valid_to else None
            supersedes = ()
            previous = prior.get(fact_key)
            if previous and record.verified and not negative and not previous[2] and valid_from is None and valid_until is None:
                supersedes = (previous[0],)
            truth = TruthMetadata(
                TruthState.VERIFIED if record.verified else TruthState.ASSERTED,
                recorded_at=now - timedelta(microseconds=len(records) - position), valid_from=valid_from, valid_until=valid_until,
                revision_of=previous[0] if supersedes else None, supersedes=supersedes,
                fact_key=fact_key, fact_value=fact_value,
            )
            security = SecurityEnvelope(owner=f"user:{record.principal}", agent_scope=record.agent)
            self.memory.put(Observation(observation_id, record.text, "text", provenance, now, now,
                                        Confidence(1.0), truth, security=security))
            prior[fact_key] = (observation_id, fact_value, negative)
            self._ids[record.record_id], self._records[record.record_id] = observation_id, record
        for number, edge in enumerate(edges):
            source_record = self._records[edge.source_id]
            source_id = SourceId(self._uuid("source", source_record.source_id))
            provenance = Provenance(ProvenanceId(self._uuid("edge-provenance", f"{edge.source_id}:{edge.target_id}:{number}")), source_id, now, locator=SourceLocator(span="synthetic edge"))
            self.memory.add_association(Association(AssociationId(self._uuid("edge", f"{edge.source_id}:{edge.target_id}:{number}")), self._ids[edge.source_id], self._ids[edge.target_id], edge.relation, provenance, Confidence(1.0), now, edge.strength))
        self.index.sync()
    def query(self, text: str, top_k: int, access_context: AccessContext | None = None) -> AdapterResponse:
        started = perf_counter()
        context = access_context or AccessContext(Principal(user_id="alpha", agent_id="agent-a"), "benchmark")
        result = self.service.recall(RecallRequest(RecallCue(text=text, access_context=context), max_results=top_k))
        reverse = {value: key for key, value in self._ids.items()}
        ids = [reverse[candidate.entity_id] for candidate in result.candidates if candidate.entity_id in reverse]
        provenance = [str(candidate.source_id) for candidate in result.candidates if candidate.source_id is not None]
        return AdapterResponse(ids, (perf_counter() - started) * 1000, input_tokens=len(_tokens(text)), output_tokens=0, provenance_ids=provenance)
    def execute_task(self, case: Case) -> AdapterResponse:
        return self.query(case.query, case.top_k,
                          AccessContext(Principal(user_id="alpha", agent_id="agent-a"), case.family,
                                        task_id=case.case_id, legacy_local_compatible=False))
    def export_state_metrics(self) -> dict[str, int]: return {"records": len(self._records), "bytes": sum(len(r.text.encode()) for r in self._records.values()), "entities": len(self.memory.iter_entities())}
    def cleanup(self) -> None: self.reset()


def adapter_for(baseline: Baseline):
    if baseline is Baseline.BASIC_RAG: return BasicRagAdapter()
    if baseline is Baseline.CURRENT_SYUNE: return CurrentSyuneAdapter()
    reasons = {
        Baseline.MODEL_ONLY: "NOT_EXECUTED — CREDENTIALS/PROVIDER UNAVAILABLE",
        Baseline.LONG_CONTEXT: "NOT_EXECUTED — CREDENTIALS/PROVIDER UNAVAILABLE",
        Baseline.MEM0: "external Mem0 adapter is not configured",
        Baseline.ZEP: "external Zep adapter is not configured",
        Baseline.LETTA: "external Letta adapter is not configured",
    }
    return NotConfiguredAdapter(baseline, reasons[baseline])
