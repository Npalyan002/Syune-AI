from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import UUID

import pytest

from syune.core import ProvenanceId, SourceId
from syune.learning import (AttributionQuality, EvidenceKind, EvidenceQuality, Experience,
    ExperienceId, KnowledgeScope, OrganizationalKnowledgeState, OrganizationalLearningService,
    OutcomeStatus, ScopeExpansionGrant, ScopeRef, SharedExperience,
    SQLiteOrganizationalLearningStore)
from syune.memory import (AccessContext, InMemoryReferenceRepository, Principal, Provenance,
    SecurityEnvelope, Sensitivity, Source)
from syune.retrieval import InvertedSeedIndex, RecallCue, RecallRequest, RetrievalService

AT = datetime(2026, 1, 1, tzinfo=timezone.utc)


def setup(tmp_path):
    memory = InMemoryReferenceRepository()
    for n in range(1, 130): memory.put(Source(SourceId(UUID(int=n)), "synthetic", f"source-{n}", AT))
    index = InvertedSeedIndex(memory); index.rebuild()
    store = SQLiteOrganizationalLearningStore(tmp_path / "organizational.sqlite3")
    return memory, index, store, OrganizationalLearningService(memory, store, index=index)


def shared(n, *, agent=None, project="alpha", organization="acme", outcome=OutcomeStatus.SUCCESS,
           lineage=(), generalized=("validate package", "deploy atomically"), sensitive=("private raw step",),
           purpose=("delivery",), source_id=None, quality=.9, eligible=True):
    agent = agent or f"agent-{n}"
    sid = SourceId(UUID(int=source_id or n))
    provenance = Provenance(ProvenanceId(UUID(int=1000+n)), sid, AT)
    security = SecurityEnvelope(organization_scope=organization, project_scope=project,
        agent_scope=agent, purpose_constraints=purpose, sensitivity=Sensitivity.CONFIDENTIAL)
    exp = Experience(ExperienceId(UUID(int=2000+n)), "deployment", (("platform", "windows"),),
        ("private raw step",), outcome, EvidenceKind.DETERMINISTIC_TEST, AttributionQuality.DIRECT,
        EvidenceQuality(quality, quality, quality, quality, quality), AT, provenance, f"cross-{n}",
        f"eval-{n}", agent, principal_scope=f"agent:{agent}", purpose_constraints=purpose,
        environment="production-like", desired_result_verified=outcome is OutcomeStatus.SUCCESS,
        independence_key=f"ind-{n}", security=security, limitations=("Windows only",))
    return SharedExperience(exp, ScopeRef(KnowledgeScope.AGENT_PRIVATE, organization, agent_id=agent,
        project_id=project), generalized, eligible, lineage, sensitive, task_instance_id=f"task-{n}")


def grant(target, source=KnowledgeScope.AGENT_PRIVATE, purpose=("delivery",)):
    return ScopeExpansionGrant(source, target, "policy-25", "learning-service", "verified reuse",
        ("deployment",), purpose, AT)


def test_cold_agent_gets_scoped_knowledge_without_raw_access(tmp_path):
    memory, index, store, service = setup(tmp_path)
    items = [shared(1, sensitive=("customer alice",)), shared(2, sensitive=("customer bob",))]
    for item in items: service.submit(item)
    target = ScopeRef(KnowledgeScope.ORGANIZATION, "acme")
    result = service.promote(items[0], target, grant(target))
    assert result.state is OrganizationalKnowledgeState.PROMOTED
    cold = AccessContext(Principal(agent_id="cold", organization_id="acme"), "delivery")
    hits = RetrievalService(memory, index).recall(RecallRequest(RecallCue(text="deploy atomically", access_context=cold)))
    assert result.procedure_id in {x.entity_id for x in hits.candidates}
    with pytest.raises(PermissionError): service.inspect_raw(str(items[0].experience.id), cold)
    owner = AccessContext(Principal(agent_id="agent-1", organization_id="acme", project_id="alpha"), "delivery")
    assert service.inspect_raw(str(items[0].experience.id), owner)["strategy"] == ["private raw step"]


def test_scope_organization_and_purpose_boundaries(tmp_path):
    _, _, _, service = setup(tmp_path); item = shared(3); service.submit(item)
    with pytest.raises(PermissionError):
        other = ScopeRef(KnowledgeScope.ORGANIZATION, "other")
        service.promote(item, other, grant(other))
    target = ScopeRef(KnowledgeScope.PROJECT, "acme", project_id="beta")
    with pytest.raises(PermissionError): service.promote(item, target, grant(target, purpose=("marketing",)))


def test_private_detail_blocks_or_is_excluded(tmp_path):
    _, _, store, service = setup(tmp_path)
    unsafe = shared(4, generalized=("email customer alice@example.test",), sensitive=("alice@example.test",))
    service.submit(unsafe); target = ScopeRef(KnowledgeScope.ORGANIZATION, "acme")
    assert service.promote(unsafe, target, grant(target)) is None
    assert any(row[0] == "promotion_blocked" for row in store.events())


def test_correlated_hundred_do_not_outvote_independent_failure(tmp_path):
    _, _, _, service = setup(tmp_path)
    positives = [shared(n, lineage=("copied:seed",), source_id=1) for n in range(10, 110)]
    failure = shared(110, outcome=OutcomeStatus.FAILURE, quality=1.0, lineage=("independent:failure",), source_id=110)
    for item in (*positives, failure): service.submit(item)
    target = ScopeRef(KnowledgeScope.ORGANIZATION, "acme")
    result = service.promote(positives[0], target, grant(target))
    assert result.state is OrganizationalKnowledgeState.DISPUTED
    assert result.independence_clusters == 1


def test_contexts_coexist_and_policy_wins(tmp_path):
    _, _, _, service = setup(tmp_path)
    windows = shared(5); linux = shared(6)
    linux = SharedExperience(replace_experience(linux.experience, conditions=(("platform", "linux"),)),
        linux.source_scope, ("use linux release",), True, ("linux",), ("secret",), "task-linux")
    assert service.precedence(.95, .8, local_is_more_specific=True, local_valid=True, organizational_valid=True) == "LOCAL"
    assert service.precedence(.95, .8, local_is_more_specific=True, local_valid=True,
                              organizational_valid=True, authoritative_policy_conflict=True) == "AUTHORITATIVE_POLICY"
    assert windows.experience.conditions != linux.experience.conditions


def replace_experience(x, **changes):
    from dataclasses import replace
    return replace(x, **changes)


def test_concurrent_promotion_is_single_materialization(tmp_path):
    memory, _, store, service = setup(tmp_path)
    items = [shared(7), shared(8)]
    for item in items: service.submit(item)
    target = ScopeRef(KnowledgeScope.ORGANIZATION, "acme"); policy = grant(target)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: service.promote(items[0], target, policy), range(8)))
    assert all(x.procedure_id == results[-1].procedure_id for x in results)
    assert memory.exists(results[-1].procedure_id)
    assert store.knowledge(results[-1].key)["revision"] == 1


def test_demotion_preserves_history_and_audit(tmp_path):
    memory, _, store, service = setup(tmp_path)
    positives = [shared(120), shared(121)]
    for item in positives: service.submit(item)
    target = ScopeRef(KnowledgeScope.ORGANIZATION, "acme"); policy = grant(target)
    promoted = service.promote(positives[0], target, policy)
    for n in (122, 123): service.submit(shared(n, outcome=OutcomeStatus.FAILURE, quality=1.0))
    changed = service.promote(positives[0], target, policy)
    assert changed.state in {OrganizationalKnowledgeState.DEMOTED, OrganizationalKnowledgeState.REVOKED}
    assert memory.lifecycle(promoted.procedure_id).state.value == "ARCHIVED"
    audit = store.scope_audit(promoted.key)
    assert audit and audit[-1][2:5] == ("policy-25", "learning-service", "verified reuse")
