import json
from datetime import datetime, timezone

import pytest

from syune.core import Confidence, ObservationId, ProvenanceId, SourceId
from syune.memory import (AccessContext, InMemoryReferenceRepository, Observation, Principal,
                          Provenance, SecurityEnvelope, Source, TruthMetadata, TruthState)
from syune.retrieval import (EmbeddingSpaceMismatch, IndexConsistency, InvertedSeedIndex,
    QueryMode, RecallCue, RecallRequest,
    RetrievalService)
from syune.retrieval_integrations import OpenAICompatibleEmbeddingProvider, QdrantVectorIndex

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _repo():
    repo = InMemoryReferenceRepository(); source = Source(SourceId.new(), "test", "phase22", NOW); repo.put(source)
    def add(text, *, security=None, truth=None):
        oid = ObservationId.new(); repo.put(Observation(oid, text, "text", Provenance(ProvenanceId.new(), source.id, NOW),
            NOW, NOW, Confidence(1), truth or TruthMetadata(), security=security)); return oid
    return repo, add


def test_openai_compatible_adapter_batches_and_validates_dimensions():
    seen = {}
    def transport(req, timeout):
        seen["body"] = json.loads(req.data); seen["auth"] = req.headers["Authorization"]
        return json.dumps({"data":[{"index":1,"embedding":[0,1,0]},{"index":0,"embedding":[1,0,0]}]}).encode()
    provider = OpenAICompatibleEmbeddingProvider(base_url="https://embedding.invalid", api_key="secret",
        model="real-model", model_version="2026-01", dimensions=3, transport=transport)
    assert provider.embed(("first", "second")) == ((1.0,0.0,0.0),(0.0,1.0,0.0))
    assert seen["body"]["input"] == ["first", "second"] and seen["auth"] == "Bearer secret"
    assert provider.identity.model == "real-model" and provider.identity.dimensions == 3


class FakeQdrant:
    def __init__(self, dimension=3, space=None): self.dimension=dimension; self.space=space; self.points={}
    def __call__(self, req, timeout):
        body = json.loads(req.data) if req.data else {}; url = req.full_url
        if url.endswith("/points/scroll"):
            points = list(self.points.values())[:1]; return json.dumps({"result":{"points":points}}).encode()
        if url.endswith("/points?wait=true"):
            for point in body["points"]: self.points[point["id"]] = point
            return b'{"status":"ok"}'
        if url.endswith("/points/query"):
            point = next(iter(self.points.values()))
            return json.dumps({"result":{"points":[{"score":.9,"payload":point["payload"]}]}}).encode()
        if "/points/delete" in url:
            for point_id in body["points"]: self.points.pop(point_id, None)
            return b'{"status":"ok"}'
        return json.dumps({"result":{"config":{"params":{"vectors":{"size":self.dimension}}},
            "points_count":len(self.points)}}).encode()


def test_qdrant_adapter_batch_search_delete_health_and_space_detection():
    fake = FakeQdrant(); provider = OpenAICompatibleEmbeddingProvider(base_url="https://e.invalid", api_key="x", model="m", dimensions=3)
    index = QdrantVectorIndex(base_url="http://qdrant.invalid", collection="memories", transport=fake)
    index.configure(provider.identity); oid = ObservationId.new(); index.upsert(oid, (1.,0.,0.), {"project":"a"})
    assert index.search((1.,0.,0.), 1, {"project":"a"}) == ((oid,.9),)
    assert index.stats().ann and index.health().value == "HEALTHY"
    other = OpenAICompatibleEmbeddingProvider(base_url="https://e.invalid", api_key="x", model="other", dimensions=3)
    restarted = QdrantVectorIndex(base_url="http://qdrant.invalid", collection="memories", transport=fake)
    with pytest.raises(EmbeddingSpaceMismatch): restarted.configure(other.identity)
    index.remove(oid); assert not fake.points


@pytest.mark.parametrize("security,principal,purpose", [
    (SecurityEnvelope(organization_scope="org-a"), Principal("u","a",organization_id="org-b"), "research"),
    (SecurityEnvelope(project_scope="p-a"), Principal("u","a",project_id="p-b"), "research"),
    (SecurityEnvelope(agent_scope="agent-a"), Principal("u","agent-b"), "research"),
    (SecurityEnvelope(owner="user:u", purpose_constraints=("audit",)), Principal("u","a"), "research"),
])
def test_semantic_security_boundaries_survive_high_similarity(security, principal, purpose):
    repo, add = _repo(); secret = add("conceptual automobile launch owner", security=security)
    allowed = add("conceptual vehicle launch owner", security=SecurityEnvelope(owner="user:u"))
    index = InvertedSeedIndex(repo); index.rebuild(); service = RetrievalService(repo,index)
    result = service.recall(RecallRequest(RecallCue(text="similar car owner", access_context=AccessContext(principal,purpose,legacy_local_compatible=False))))
    ids = {item.entity_id for item in result.working_memory}
    assert secret not in ids and allowed in ids


def test_future_strong_semantic_match_cannot_override_historical_eligibility():
    repo, add = _repo()
    past = add("automobile launch plan", truth=TruthMetadata(TruthState.VERIFIED, recorded_at=NOW,
        valid_from=datetime(2020,1,1,tzinfo=timezone.utc), valid_until=datetime(2025,1,1,tzinfo=timezone.utc)))
    future = add("similar car automobile launch plan owner", truth=TruthMetadata(TruthState.VERIFIED, recorded_at=NOW,
        valid_from=datetime(2027,1,1,tzinfo=timezone.utc)))
    index = InvertedSeedIndex(repo); index.rebuild(); service = RetrievalService(repo,index)
    result = service.recall(RecallRequest(RecallCue(text="similar automobile launch plan", query_mode=QueryMode.HISTORICAL,
        valid_at=datetime(2024,1,1,tzinfo=timezone.utc))))
    ids = {item.entity_id for item in result.working_memory}
    assert past in ids and future not in ids


class FailingEmbedding:
    from syune.retrieval import EmbeddingIdentity
    identity = EmbeddingIdentity("test", "failure", "1", 3); version="1"; dimensions=3
    def embed(self, texts):
        from syune.retrieval import EmbeddingUnavailable
        raise EmbeddingUnavailable("offline")


def test_embedding_failure_is_explicit_degraded_but_lexical_operational():
    repo, add = _repo(); expected = add("Mercury migration owner Avery")
    index = InvertedSeedIndex(repo, embedding_provider=FailingEmbedding()); index.rebuild()
    assert index.consistency is IndexConsistency.DEGRADED and index.embedding_failures == 1
    result = RetrievalService(repo,index).recall(RecallRequest(RecallCue(text="Mercury migration owner")))
    assert expected in {item.entity_id for item in result.working_memory}
    assert index.health().consistency is IndexConsistency.DEGRADED


def test_rebuild_from_canonical_memory_preserves_results():
    repo, add = _repo(); expected = add("Juniper deployment vehicle")
    first = InvertedSeedIndex(repo); first.rebuild(); before = first.semantic("Juniper automobile", 3)
    restarted = InvertedSeedIndex(repo); restarted.rebuild(); after = restarted.semantic("Juniper automobile", 3)
    assert before == after and after[0].entity_id == expected
