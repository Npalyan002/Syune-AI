from datetime import datetime, timezone

from syune.core import Confidence, ObservationId, ProvenanceId, SourceId
from syune.memory import (
    AccessContext, InMemoryReferenceRepository, Observation, Principal, Provenance,
    SecurityEnvelope, Source,
)
from syune.retrieval import (
    DeterministicEmbeddingProvider, InvertedSeedIndex, LocalVectorIndex, QueryIntent,
    RecallCue, RecallRequest, RetrievalService, RetrieverKind, analyze_query,
)


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def memory():
    repo = InMemoryReferenceRepository(); source = Source(SourceId.new(), "test", "hybrid", NOW); repo.put(source)
    def add(text, security=None):
        oid = ObservationId.new(); repo.put(Observation(oid, text, "text",
            Provenance(ProvenanceId.new(), source.id, NOW), NOW, NOW, Confidence(1), security=security)); return oid
    return repo, add


def test_router_selects_bounded_paths():
    assert analyze_query("current vendor").intent is QueryIntent.TEMPORAL
    assert analyze_query("similar concept").routes == (RetrieverKind.SEMANTIC, RetrieverKind.ASSOCIATIVE)
    assert RetrieverKind.SEMANTIC not in analyze_query("exact launch code").routes
    assert analyze_query(None, True).intent is QueryIntent.EXACT


def test_exact_lexical_entity_semantic_and_incremental_indexing():
    repo, add = memory(); owner = add("Mercury migration owner is Avery")
    index = InvertedSeedIndex(repo); index.rebuild()
    assert index.exact("Mercury migration owner is Avery", 4)[0].entity_id == owner
    assert owner in {hit.entity_id for hit in index.lexical("Mercury migration owner", 4)}
    assert owner in {hit.entity_id for hit in index.entity("Mercury owner", 4)}
    # chief/owner share a deterministic semantic canonical token.
    assert owner in {hit.entity_id for hit in index.semantic("Mercury migration chief", 4)}
    later = add("Juniper release vehicle is ready"); index.sync()
    assert later in index.entries
    assert later in {hit.entity_id for hit in index.semantic("Juniper release automobile", 4)}


def test_entity_hits_report_only_actual_matches_and_relations_must_match():
    repo, add = memory()
    location = add("Atlas-17 headquarters is in Northport")
    add("Atlas-17 publishes maintenance notes")
    other = add("Boreal-22 headquarters is in Southport")
    index = InvertedSeedIndex(repo); index.rebuild(); service = RetrievalService(repo, index)

    entity_hits = {hit.entity_id: hit for hit in index.entity("Where is Atlas-17?", 10)}
    assert set(entity_hits[location].matched_tokens) == {"atlas", "17"}
    assert other not in entity_hits

    relevant = service.recall(RecallRequest(RecallCue(text="Where is Atlas-17 headquarters?")))
    assert [item.entity_id for item in relevant.candidates] == [location]
    absent = service.recall(RecallRequest(RecallCue(text="What launch password belongs to Atlas-17?")))
    assert not absent.candidates and absent.evidence_status == "INSUFFICIENT_EVIDENCE"


def test_fixed_relation_equivalence_recovers_paraphrase_without_relation_drift():
    repo, add = memory()
    manager = add("Avery supervises Atlas-17")
    location = add("Atlas-17 is situated in Northport")
    index = InvertedSeedIndex(repo); index.rebuild(); service = RetrievalService(repo, index)

    managed = service.recall(RecallRequest(RecallCue(text="Who manages Atlas-17?")))
    assert [item.entity_id for item in managed.candidates] == [manager]
    located = service.recall(RecallRequest(RecallCue(text="Where is Atlas-17 located?")))
    assert [item.entity_id for item in located.candidates] == [location]
    ownership = service.recall(RecallRequest(RecallCue(text="Who owns Atlas-17?")))
    assert not ownership.candidates


def test_abstention_duplicate_context_and_associative_explainability():
    repo, add = memory(); first = add("orchard budget exact"); duplicate = add("orchard budget exact")
    index = InvertedSeedIndex(repo); index.rebuild(); service = RetrievalService(repo, index)
    result = service.recall(RecallRequest(RecallCue(text="orchard budget exact")))
    assert {first, duplicate} <= {item.entity_id for item in result.candidates}
    assert len(result.working_memory) == 1
    assert result.evidence_status == "SUFFICIENT_EVIDENCE"
    assert all(item.found_by for item in result.candidates)
    absent = service.recall(RecallRequest(RecallCue(text="submarine password unknown")))
    assert absent.evidence_status == "INSUFFICIENT_EVIDENCE" and not absent.working_memory


def test_unauthorized_semantic_match_never_enters_context():
    repo, add = memory()
    secret = add("conceptual automobile launch plan",
                 SecurityEnvelope(owner="user:alice", agent_scope="agent-a"))
    public = add("conceptual vehicle safety overview", SecurityEnvelope(owner="user:bob", agent_scope="agent-b"))
    index = InvertedSeedIndex(repo); index.rebuild(); service = RetrievalService(repo, index)
    access = AccessContext(Principal("bob", "agent-b"), "research", legacy_local_compatible=False)
    result = service.recall(RecallRequest(RecallCue(text="similar car", access_context=access)))
    ids = {item.entity_id for item in result.working_memory}
    assert public in ids and secret not in ids


def test_semantic_ablation_is_deterministic():
    provider = DeterministicEmbeddingProvider(); index = LocalVectorIndex()
    vectors = provider.embed(("car owner", "vehicle chief", "banana policy"))
    ids = tuple(ObservationId.new() for _ in vectors)
    for memory_id, vector in zip(ids, vectors): index.upsert(memory_id, vector)
    first = index.search(provider.embed(("automobile lead",))[0], 3)
    second = index.search(provider.embed(("automobile lead",))[0], 3)
    assert first == second and {item[0] for item in first[:2]} == {ids[0], ids[1]}


def test_long_claim_discovers_multi_term_evidence_without_mandatory_capitalized_anchor():
    repo, add = memory()
    evidence = add("Dietary nitrate supplementation reduces resting blood pressure in healthy adults")
    index = InvertedSeedIndex(repo); index.rebuild(); service = RetrievalService(repo, index)
    result = service.recall(RecallRequest(RecallCue(
        text="Scientific studies report dietary nitrate can reduce resting pressure among adults"
    )))
    assert [item.entity_id for item in result.candidates] == [evidence]
    diagnostics = dict(result.diagnostics)
    assert diagnostics["discovery_admitted"] >= 1
    assert diagnostics["authorized_candidates"] == 1


def test_long_claim_single_generic_overlap_is_filtered_with_safe_diagnostics():
    repo, add = memory()
    add("Dietary nitrate supplementation reduces resting blood pressure in healthy adults")
    index = InvertedSeedIndex(repo); index.rebuild(); service = RetrievalService(repo, index)
    result = service.recall(RecallRequest(RecallCue(
        text="Scientific archives discuss unrelated planetary geology and healthy ecosystems"
    )))
    assert result.candidates == ()
    diagnostics = dict(result.diagnostics)
    assert diagnostics["discovery_filtered"] >= 1
    assert diagnostics["abstention_reason"] == "NO_ADMITTED_EVIDENCE"
