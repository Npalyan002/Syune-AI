from datetime import datetime, timezone

import pytest

from syune.core import Confidence, LearningSignalId, ObservationId, ProvenanceId, SourceId
from syune.learning import LearningSignal, LearningSignalKind, LearningSource, LearningTarget, SQLiteLearningStore
from syune.learning.errors import LearningError
from syune.learning.service import LearningService
from syune.memory import (
    AccessContext, DefaultAccessPolicy, InMemoryReferenceRepository, Observation, Principal,
    Provenance, SecurityEnvelope, Sensitivity, Source,
)
from syune.retrieval import InvertedSeedIndex, RecallCue, RecallRequest, RetrievalService
from syune.memory.sqlite_repository import SQLiteMemoryRepository


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def context(user="alice", agent="agent-a", organization="org-a", project="project-a",
            department="dept-a", purpose="support"):
    return AccessContext(Principal(user, agent, organization, project, department), purpose, "task-1", False)


def secured_repo(envelope):
    repo = InMemoryReferenceRepository(); source = Source(SourceId.new(), "test", "secure", NOW); repo.put(source)
    oid = ObservationId.new(); provenance = Provenance(ProvenanceId.new(), source.id, NOW)
    repo.put(Observation(oid, "private launch secret", "text", provenance, NOW, NOW,
                         Confidence(1), security=envelope))
    index = InvertedSeedIndex(repo); index.rebuild()
    return repo, oid, RetrievalService(repo, index)


def ids(service, access):
    return tuple(item.entity_id for item in service.recall(
        RecallRequest(RecallCue(text="private launch secret", access_context=access))).candidates)


def test_scope_purpose_deny_precedence_and_cache_isolation():
    envelope = SecurityEnvelope(owner="user:alice", organization_scope="org-a", project_scope="project-a",
        department_scope="dept-a", agent_scope="agent-a", allowed_principals=("user:alice",),
        denied_principals=("user:mallory",), sensitivity=Sensitivity.CONFIDENTIAL,
        purpose_constraints=("support",))
    _, oid, service = secured_repo(envelope)
    assert oid in ids(service, context())
    assert oid not in ids(service, context(user="bob"))
    assert oid not in ids(service, context(agent="agent-b"))
    assert oid not in ids(service, context(project="project-b"))
    assert oid not in ids(service, context(organization="org-b"))
    assert oid not in ids(service, context(department="dept-b"))
    assert oid not in ids(service, context(purpose="training"))
    assert oid not in ids(service, None)
    assert oid not in ids(service, context(user="mallory"))
    # Repeating the same query under a different principal cannot reuse an allowed result.
    assert oid in ids(service, context()) and oid not in ids(service, context(agent="agent-b"))
    assert any(event.decision.value.startswith("DENY_") for event in service.access_events)


def test_explicit_sharing_public_restricted_and_legacy_policy():
    shared = SecurityEnvelope(allowed_principals=("user:bob",), sensitivity=Sensitivity.CONFIDENTIAL)
    _, oid, service = secured_repo(shared)
    assert oid in ids(service, context(user="bob"))
    restricted = SecurityEnvelope(organization_scope="org-a", sensitivity=Sensitivity.RESTRICTED)
    _, rid, restricted_service = secured_repo(restricted)
    assert rid not in ids(restricted_service, context())
    public = SecurityEnvelope(sensitivity=Sensitivity.PUBLIC)
    _, pid, public_service = secured_repo(public)
    assert pid in ids(public_service, None)

    repo = InMemoryReferenceRepository(); source = Source(SourceId.new(), "legacy", "legacy", NOW); repo.put(source)
    oid2 = ObservationId.new(); repo.put(Observation(oid2, "legacy local", "text",
        Provenance(ProvenanceId.new(), source.id, NOW), NOW, NOW))
    index = InvertedSeedIndex(repo); index.rebuild(); legacy = RetrievalService(repo, index)
    assert oid2 in tuple(x.entity_id for x in legacy.recall(RecallRequest(RecallCue(text="legacy local"))).candidates)
    strict = AccessContext(context().principal, "support", legacy_local_compatible=False)
    assert oid2 not in tuple(x.entity_id for x in legacy.recall(
        RecallRequest(RecallCue(text="legacy local", access_context=strict))).candidates)


def test_persistence_and_learning_boundary(tmp_path):
    envelope = SecurityEnvelope(owner="user:alice", agent_scope="agent-a", purpose_constraints=("support",))
    path = tmp_path / "memory.sqlite3"
    with SQLiteMemoryRepository(path) as repo:
        source = Source(SourceId.new(), "test", "secure", NOW); repo.put(source)
        oid = ObservationId.new(); repo.put(Observation(oid, "secure evidence", "text",
            Provenance(ProvenanceId.new(), source.id, NOW), NOW, NOW, security=envelope))
    with SQLiteMemoryRepository(path) as repo:
        assert repo.get(oid).security == envelope
        with SQLiteLearningStore(tmp_path / "learning.sqlite3") as store:
            learning = LearningService(repo, store)
            signal = LearningSignal(LearningSignalId.new(), LearningSignalKind.POSITIVE_OUTCOME, NOW,
                (LearningTarget(oid),), LearningSource.SYSTEM_TEST, "secure", ProvenanceId.new())
            with pytest.raises(LearningError): learning.record(signal, context(user="bob"))
            assert learning.record(signal, context())


def test_allow_and_deny_conflict_fails_closed():
    envelope = SecurityEnvelope(allowed_principals=("user:alice",), denied_principals=("user:alice",))
    _, oid, service = secured_repo(envelope)
    assert oid not in ids(service, context())
