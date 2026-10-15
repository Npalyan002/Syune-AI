from dataclasses import replace
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from syune.core import AssociationId, Confidence, ObservationId, ProvenanceId, SourceId
from syune.memory import (
    AccessContext, Association, LifecycleState, Observation, Principal, Provenance,
    SecurityEnvelope, Source,
)
from syune.memory.repository import InMemoryReferenceRepository
from syune.retrieval import InvertedSeedIndex, RecallCue, RecallRequest, RetrievalService
from syune.adapters.aml.v1 import _ReadWriteLock


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
BOB = AccessContext(Principal("bob", "agent-b"), "audit", legacy_local_compatible=False)


def build(*, hidden: bool = True, two_hop: bool = False, denied: bool = False):
    repo = InMemoryReferenceRepository()
    source = Source(SourceId.new(), "audit", "aml09j", NOW)
    provenance = Provenance(ProvenanceId.new(), source.id, NOW)
    public = Observation(
        ObservationId.new(), "ordinary public note", "text", provenance, NOW, NOW,
        Confidence(1), security=SecurityEnvelope(owner="user:bob", agent_scope="agent-b"),
    )
    repo.put(source); repo.put(public)
    secret = middle = None
    if hidden:
        denied_principals = ("user:bob",) if denied else ()
        secret = Observation(
            ObservationId.new(), "cinnabar-private-trigger", "text", provenance, NOW, NOW,
            Confidence(1), security=SecurityEnvelope(
                owner="user:alice", agent_scope="agent-a",
                allowed_principals=("user:bob",) if denied else (),
                denied_principals=denied_principals,
            ),
        )
        repo.put(secret)
        endpoint = secret
        if two_hop:
            middle = Observation(
                ObservationId.new(), "alice hidden bridge", "text", provenance, NOW, NOW,
                Confidence(1), security=SecurityEnvelope(owner="user:alice", agent_scope="agent-a"),
            )
            repo.put(middle)
            repo.add_association(Association(
                AssociationId.new(), secret.id, middle.id, "associated_with", provenance,
                Confidence(1), NOW, 1.0,
            ))
            endpoint = middle
        repo.add_association(Association(
            AssociationId.new(), endpoint.id, public.id, "associated_with", provenance,
            Confidence(1), NOW, 1.0,
        ))
    index = InvertedSeedIndex(repo); index.rebuild()
    return repo, index, RetrievalService(repo, index), source, secret, public, middle


def stable(result):
    """Observable retrieval state excluding nondeterministic wall-clock timings."""
    return result.candidates, result.working_memory, result.diagnostics, result.evidence_status, result.route


def test_direct_id_and_context_id_are_authorized_before_graph_expansion():
    _, _, service, _, secret, public, _ = build()
    direct = service.recall(RecallRequest(RecallCue(entity_ids=(secret.id,), access_context=BOB)))
    context = service.recall(RecallRequest(RecallCue(context_ids=(secret.id,), access_context=BOB)))
    assert direct.candidates == context.candidates == ()
    assert public.id not in {item.entity_id for item in direct.candidates + context.candidates}


def test_two_hop_hidden_path_and_deny_precedence_cannot_reveal_public_neighbor():
    for kwargs in ({"two_hop": True}, {"denied": True}):
        _, _, service, _, _, public, _ = build(**kwargs)
        result = service.recall(RecallRequest(RecallCue(
            text="cinnabar-private-trigger", access_context=BOB,
        )))
        assert result.candidates == ()
        assert public.id not in {item.entity_id for item in result.candidates}


def test_hidden_graph_addition_is_observationally_non_interfering():
    _, _, without, _, _, _, _ = build(hidden=False)
    _, _, with_hidden, _, _, _, _ = build(hidden=True)
    query = RecallRequest(RecallCue(text="cinnabar-private-trigger", access_context=BOB))
    assert stable(without.recall(query)) == stable(with_hidden.recall(query))
    # Warm partitions must preserve the exact same observable view.
    assert stable(without.recall(query)) == stable(with_hidden.recall(query))
    assert "cinnabar" not in repr(with_hidden.recall(query).diagnostics)


def test_hidden_semantic_candidates_cannot_crow_visible_fallback():
    repo, index, service, source, _, public, _ = build(hidden=False)
    provenance = Provenance(ProvenanceId.new(), source.id, NOW)
    for number in range(48):
        repo.put(Observation(
            ObservationId.new(), f"similar concept idea {number}", "text", provenance, NOW, NOW,
            Confidence(1), security=SecurityEnvelope(owner="user:alice", agent_scope="agent-a"),
        ))
    visible = Observation(
        ObservationId.new(), "similar concept idea visible", "text", provenance, NOW, NOW,
        Confidence(1), security=SecurityEnvelope(owner="user:bob", agent_scope="agent-b"),
    )
    repo.put(visible); index.sync()
    result = service.recall(RecallRequest(RecallCue(text="similar concept idea", access_context=BOB)))
    ids = {item.entity_id for item in result.candidates}
    assert visible.id in ids
    assert all(getattr(repo.get(item), "security").owner == "user:bob" for item in ids)


def test_authorized_same_principal_association_still_expands():
    repo, index, service, source, _, public, _ = build(hidden=False)
    provenance = Provenance(ProvenanceId.new(), source.id, NOW)
    seed = Observation(
        ObservationId.new(), "cinnabar-owned-trigger", "text", provenance, NOW, NOW,
        Confidence(1), security=SecurityEnvelope(owner="user:bob", agent_scope="agent-b"),
    )
    repo.put(seed)
    repo.add_association(Association(
        AssociationId.new(), seed.id, public.id, "associated_with", provenance,
        Confidence(1), NOW, 1.0,
    ))
    index.sync()
    result = service.recall(RecallRequest(RecallCue(text="cinnabar-owned-trigger", access_context=BOB)))
    ids = {item.entity_id for item in result.candidates}
    assert seed.id in ids and public.id in ids


def test_source_seed_and_shared_name_return_only_request_visible_records():
    repo, index, service, source, secret, public, _ = build()
    provenance = Provenance(ProvenanceId.new(), source.id, NOW)
    bob_shared = Observation(
        ObservationId.new(), "shared codename heliotrope", "text", provenance, NOW, NOW,
        Confidence(1), security=SecurityEnvelope(owner="user:bob", agent_scope="agent-b"),
    )
    alice_shared = Observation(
        ObservationId.new(), "shared codename heliotrope", "text", provenance, NOW, NOW,
        Confidence(1), security=SecurityEnvelope(owner="user:alice", agent_scope="agent-a"),
    )
    repo.put(bob_shared); repo.put(alice_shared); index.sync()
    by_name = service.recall(RecallRequest(RecallCue(
        text="shared codename heliotrope", access_context=BOB,
    )))
    by_source = service.recall(RecallRequest(RecallCue(
        source_ids=(source.id,), access_context=BOB,
    )))
    assert bob_shared.id in {item.entity_id for item in by_name.candidates}
    assert alice_shared.id not in {item.entity_id for item in by_name.candidates}
    source_ids = {item.entity_id for item in by_source.candidates}
    assert public.id in source_ids and bob_shared.id in source_ids
    assert secret.id not in source_ids and alice_shared.id not in source_ids


def test_revocation_and_archived_hidden_endpoint_fail_closed_without_rebuild():
    repo, index, service, source, _, public, _ = build(hidden=False)
    provenance = Provenance(ProvenanceId.new(), source.id, NOW)
    seed = Observation(
        ObservationId.new(), "revocable cinnabar trigger", "text", provenance, NOW, NOW,
        Confidence(1), security=SecurityEnvelope(owner="user:bob", agent_scope="agent-b"),
    )
    repo.put(seed)
    repo.add_association(Association(
        AssociationId.new(), seed.id, public.id, "associated_with", provenance,
        Confidence(1), NOW, 1.0,
    ))
    index.sync()
    assert public.id in {item.entity_id for item in service.recall(RecallRequest(RecallCue(
        text="revocable cinnabar trigger", access_context=BOB,
    ))).candidates}
    repo.replace(replace(
        seed, security=SecurityEnvelope(owner="user:alice", agent_scope="agent-a"),
    ))
    index.sync()
    revoked = service.recall(RecallRequest(RecallCue(
        text="revocable cinnabar trigger", access_context=BOB,
    )))
    assert revoked.candidates == ()
    repo.transition_lifecycle(seed.id, LifecycleState.ARCHIVED, "security test")
    index.sync()
    archived = service.recall(RecallRequest(RecallCue(
        entity_ids=(seed.id,), include_archived=True, access_context=BOB,
    )))
    assert archived.candidates == ()


def test_policy_partition_generation_invalidates_add_policy_lifecycle_association_and_rebuild():
    repo, index, service, source, _, public, _ = build(hidden=False)
    query = RecallRequest(RecallCue(text="ordinary public note", access_context=BOB))
    service.recall(query); service.recall(query)
    before = index.partition_metrics()
    assert before["hits"] >= 1 and before["entries"] == 1

    provenance = Provenance(ProvenanceId.new(), source.id, NOW)
    added = Observation(
        ObservationId.new(), "ordinary public note added", "text", provenance, NOW, NOW,
        Confidence(1), security=SecurityEnvelope(owner="user:bob", agent_scope="agent-b"),
    )
    repo.put(added); index.sync()
    assert index.partition_metrics()["entries"] == 0
    service.recall(query)

    repo.replace(replace(added, security=SecurityEnvelope(owner="user:alice", agent_scope="agent-a")))
    index.sync(); assert index.partition_metrics()["entries"] == 0
    assert added.id not in {item.entity_id for item in service.recall(query).candidates}

    repo.transition_lifecycle(public.id, LifecycleState.ARCHIVED, "cache invalidation")
    index.sync(); assert index.partition_metrics()["entries"] == 0
    service.recall(query)

    # Associations do not alter corpus membership, but publication still invalidates
    # as required by the runtime's write-generation contract.
    repo.add_association(Association(
        AssociationId.new(), source.id, added.id, "associated_with", provenance,
        Confidence(1), NOW, 1.0,
    ))
    index.sync(); assert index.partition_metrics()["entries"] == 0
    service.recall(query); index.rebuild()
    assert index.partition_metrics()["entries"] == 0


def test_completed_revocation_is_never_stale_under_concurrent_search():
    repo, index, service, source, _, public, _ = build(hidden=False)
    provenance = Provenance(ProvenanceId.new(), source.id, NOW)
    seed = Observation(
        ObservationId.new(), "revocation-race-unique-trigger", "text", provenance, NOW, NOW,
        Confidence(1), security=SecurityEnvelope(owner="user:bob", agent_scope="agent-b"),
    )
    repo.put(seed)
    repo.add_association(Association(
        AssociationId.new(), seed.id, public.id, "associated_with", provenance,
        Confidence(1), NOW, 1.0,
    ))
    index.sync()
    request = RecallRequest(RecallCue(text="revocation-race-unique-trigger", access_context=BOB))
    assert public.id in {item.entity_id for item in service.recall(request).candidates}
    revoked = Event()
    runtime_lock = _ReadWriteLock()
    after = []

    def reader():
        for _ in range(20):
            runtime_lock.acquire_read()
            try:
                result = service.recall(request)
                if revoked.is_set():
                    after.append(tuple(item.entity_id for item in result.candidates))
            finally:
                runtime_lock.release_read()

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(reader) for _ in range(8)]
        runtime_lock.acquire_write()
        try:
            repo.replace(replace(
                seed, security=SecurityEnvelope(owner="user:alice", agent_scope="agent-a"),
            ))
            index.sync()  # publish before releasing the supported runtime writer lock
            revoked.set()
        finally:
            runtime_lock.release_write()
        for future in futures:
            future.result()
    assert after
    assert all(seed.id not in ids and public.id not in ids for ids in after)

