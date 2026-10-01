from datetime import datetime, timezone
from uuid import UUID

import pytest

from syune.core import ProvenanceId, SourceId
from syune.learning import (AttributionQuality, EvidenceKind, EvidenceQuality, Experience,
    ExperienceId, OutcomeStatus, SQLiteVerifiedLearningStore, VerifiedExperienceLearningService,
    VerifiedLearningState, hypothesis_key)
from syune.memory import (AccessContext, DefaultAccessPolicy, InMemoryReferenceRepository,
    Principal, Provenance, SecurityEnvelope, Sensitivity, Source)
from syune.retrieval import InvertedSeedIndex, RecallCue, RecallRequest, RetrievalService


AT=datetime(2026,1,1,tzinfo=timezone.utc)


def setup(tmp_path):
    memory=InMemoryReferenceRepository(); sid=SourceId(UUID(int=1)); memory.put(Source(sid,"test","experience",AT))
    provenance=Provenance(ProvenanceId(UUID(int=2)),sid,AT)
    index=InvertedSeedIndex(memory); index.rebuild()
    store=SQLiteVerifiedLearningStore(tmp_path/"verified.sqlite3")
    return memory,provenance,index,store,VerifiedExperienceLearningService(memory,store,index=index)


def experience(number,provenance,outcome=OutcomeStatus.SUCCESS,independent=None,security=None,
               evaluator="test-suite",generator="worker"):
    return Experience(ExperienceId(UUID(int=number)),"deployment",(("platform","windows"),),
        ("validate package","deploy atomically"),outcome,EvidenceKind.DETERMINISTIC_TEST,
        AttributionQuality.DIRECT,EvidenceQuality(.9,1,.9,1,1),AT,provenance,f"event-{number}",
        evaluator,generator,principal_scope="project:alpha",purpose_constraints=("delivery",),
        environment="production-like",desired_result_verified=outcome is OutcomeStatus.SUCCESS,
        independence_key=independent or f"run-{number}",security=security,
        limitations=("only validated on Windows",))


def test_single_example_does_not_promote_and_independent_support_does(tmp_path):
    memory,p,index,store,learning=setup(tmp_path)
    first=experience(10,p); learning.record(first); result=learning.maintain()[0]
    assert result.state is VerifiedLearningState.CANDIDATE and result.procedure_id is None
    for n in (11,12): learning.record(experience(n,p))
    result=learning.maintain()[0]
    assert result.state is VerifiedLearningState.PROMOTED and memory.exists(result.procedure_id)
    recalled=RetrievalService(memory,index).recall(RecallRequest(RecallCue(text="deploy atomically")))
    assert result.procedure_id in {item.entity_id for item in recalled.candidates}
    explanation=learning.explain(hypothesis_key(first))
    assert explanation["independent_support"]==3 and len(explanation["supporting_experiences"])==3


def test_duplicate_and_model_self_evaluation_do_not_inflate_independence(tmp_path):
    _,p,_,store,learning=setup(tmp_path)
    values=[experience(n,p,independent="same-run",evaluator="model-a",generator="model-a") for n in (20,21,22)]
    for item in values: learning.record(item)
    result=learning.maintain()[0]
    assert result.independent_support==1 and result.state is VerifiedLearningState.SUPPORTED
    assert learning.record(values[0]) and len(store.experiences(result.key))==3


def test_negative_evidence_demotes_then_revokes_without_erasing_lineage(tmp_path):
    memory,p,index,store,learning=setup(tmp_path)
    positives=[experience(n,p) for n in (30,31,32)]
    for item in positives: learning.record(item)
    promoted=learning.maintain()[0]
    for n in (33,34): learning.record(experience(n,p,OutcomeStatus.FAILURE))
    demoted=learning.maintain()[0]
    assert demoted.state is VerifiedLearningState.DEMOTED
    assert not index.exact("validate package deploy atomically",5)
    learning.record(experience(35,p,OutcomeStatus.FAILURE)); revoked=learning.maintain()[0]
    assert revoked.state is VerifiedLearningState.REVOKED
    assert len(revoked.supporting_experience_ids)==3 and len(revoked.contradicting_experience_ids)==3
    assert memory.get(promoted.procedure_id).truth.state.value=="INVALIDATED"


def test_scope_purpose_and_authorization_survive_promotion(tmp_path):
    memory,p,index,store,learning=setup(tmp_path)
    security=SecurityEnvelope(project_scope="alpha",agent_scope="agent-a",sensitivity=Sensitivity.CONFIDENTIAL,
        purpose_constraints=("delivery",),default_policy=DefaultAccessPolicy.SECURE_DENY)
    seed=None
    for n in (40,41,42):
        item=experience(n,p,security=security); seed=seed or item; learning.record(item)
    promoted=learning.maintain()[0]
    allowed=AccessContext(Principal(agent_id="agent-a",project_id="alpha"),"delivery")
    denied=AccessContext(Principal(agent_id="agent-b",project_id="alpha"),"delivery")
    service=RetrievalService(memory,index)
    assert service.recall(RecallRequest(RecallCue(text="deploy atomically",access_context=allowed))).candidates
    assert not service.recall(RecallRequest(RecallCue(text="deploy atomically",access_context=denied))).candidates
    other=experience(43,p,security=SecurityEnvelope(project_scope="beta",agent_scope="agent-a"))
    assert hypothesis_key(other)!=hypothesis_key(seed)


def test_success_requires_verified_desired_result(tmp_path):
    _,p,_,store,_=setup(tmp_path)
    with pytest.raises(ValueError):
        Experience(ExperienceId(UUID(int=50)),"task",(),("try",),OutcomeStatus.SUCCESS,
            EvidenceKind.SYSTEM_OBSERVATION,AttributionQuality.UNKNOWN,EvidenceQuality(.5,.5,.5,.5,.5),
            AT,p,"unsafe",desired_result_verified=False)
    store.close()


def test_restart_and_duplicate_replay_are_idempotent(tmp_path):
    memory,p,index,store,learning=setup(tmp_path); path=store.path
    values=[experience(n,p) for n in (60,61,62)]
    for item in values: learning.record(item)
    promoted=learning.maintain()[0]; procedure_id=promoted.procedure_id; store.close()
    with SQLiteVerifiedLearningStore(path) as reopened:
        resumed=VerifiedExperienceLearningService(memory,reopened,index=index)
        assert resumed.record(values[0])
        restored=reopened.hypothesis(hypothesis_key(values[0]))
        assert restored.state is VerifiedLearningState.PROMOTED
        assert restored.procedure_id==procedure_id and memory.exists(procedure_id)
        assert resumed.maintain()==()
