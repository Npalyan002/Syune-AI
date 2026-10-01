"""Phase 17 only: characterize gaps without changing production implementation.

Run with pytest and a disposable --basetemp. Passing asserts confirm findings,
not desired product behavior. No existing SYUNE state is opened.
"""
import asyncio
import json
from dataclasses import fields, replace

from syune import Syune
from syune.core import *
from syune.memory import *
from syune.product.config import SyuneConfig, StateConfig, StudyConfig
from syune.product.state import initialize_state, DATABASES
from syune.product.runtime import SyuneRuntime
from syune.learning import *
from syune.retrieval import *


def runtime_at(tmp_path):
    library = tmp_path / 'library'
    library.mkdir()
    config = SyuneConfig(StateConfig(tmp_path / 'state'), StudyConfig((library,)))
    initialize_state(config)
    return config, library


def test_p01_sdk_mcp_learning_divergence(tmp_path):
    from mcp import Client
    from syune.gateway.mcp import GatewayConfig, open_gateway
    config, library = runtime_at(tmp_path)
    source = library / 'fact.txt'
    source.write_text('auditmarker evidence', encoding='utf-8')
    with SyuneRuntime.open(config) as runtime:
        runtime.study.study(source)
        runtime.index.sync()
        target = next(x for x in runtime.memory.iter_entities() if isinstance(x, Observation))
        service = LearningService(runtime.memory, runtime.learning)
        service.record(LearningSignal(LearningSignalId.new(), LearningSignalKind.POSITIVE_OUTCOME,
            utc_now(), (LearningTarget(target.id),), LearningSource.SYSTEM_TEST,
            'audit-positive', target.provenance.id))
        service.consolidate_once()
        sdk = Syune(runtime).recall('auditmarker').data
        sdk_delta = dict(sdk['candidates'][0]['components'])['learned_utility']
    async def query():
        gateway = GatewayConfig(config.state.root, (library,),
            memory_path=config.state.root / DATABASES['memory'],
            study_path=config.state.root / DATABASES['study_perception'])
        with open_gateway(gateway) as (server, _):
            async with Client(server) as client:
                result = await client.call_tool('syune_recall', {'text': 'auditmarker'})
                return json.loads(result.content[0].text)
    mcp = asyncio.run(query())
    mcp_delta = dict(mcp['candidates'][0]['components'])['learned_utility']
    assert sdk_delta > 0 and mcp_delta == 0
    print(json.dumps({'probe': 'P01', 'sdk_utility': sdk_delta, 'mcp_utility': mcp_delta}))


def test_p02_changed_source_keeps_old_revision_retrievable(tmp_path):
    config, library = runtime_at(tmp_path)
    source = library / 'fact.txt'
    with SyuneRuntime.open(config) as runtime:
        source.write_text('oldmarker status is approved', encoding='utf-8')
        first = runtime.study.study(source)
        source.write_text('newmarker status is rejected', encoding='utf-8')
        second = runtime.study.study(source)
        runtime.index.sync()
        old = runtime.retrieval.recall(RecallRequest(RecallCue(text='oldmarker')))
        assert first.status.source_id == second.status.source_id
        assert old.candidates
        print(json.dumps({'probe': 'P02', 'old_revision_retrievable': True}))


def test_p03_retraction_is_penalty_not_exclusion(tmp_path):
    config, library = runtime_at(tmp_path)
    source = library / 'fact.txt'
    source.write_text('retractedmarker content', encoding='utf-8')
    with SyuneRuntime.open(config) as runtime:
        studied = runtime.study.study(source)
        runtime.index.sync()
        service = LearningService(runtime.memory, runtime.learning)
        service.record(LearningSignal(LearningSignalId.new(), LearningSignalKind.SOURCE_RETRACTION_NOTICE,
            utc_now(), (LearningTarget(studied.status.source_id),), LearningSource.SYSTEM_TEST,
            'audit-retraction', ProvenanceId.new()))
        service.consolidate_once()
        recalled = runtime.retrieval.recall(RecallRequest(RecallCue(text='retractedmarker')))
        assert recalled.candidates
        assert any(x.retraction_flag for x in runtime.learning.snapshot())
        print(json.dumps({'probe': 'P03', 'retraction_flag': True, 'still_retrievable': True}))


def test_p04_missing_source_provenance_accepted(tmp_path):
    from syune.evals.invariants import audit
    with SQLiteMemoryRepository(tmp_path / 'memory.sqlite3') as memory:
        now = utc_now()
        p = Provenance(ProvenanceId.new(), SourceId.new(), now)
        observation = Observation(ObservationId.new(), 'orphan', 'text', p, now, now)
        memory.put(observation)
        assert memory.get(observation.id) == observation
        result = audit(memory)
        assert 'memory:source_missing' in result.issues
        print(json.dumps({'probe': 'P04', 'write_accepted': True, 'offline_audit_issues': result.issues}))


def test_p05_runtime_health_does_not_probe_closed_memory(tmp_path):
    config, _ = runtime_at(tmp_path)
    runtime = SyuneRuntime.open(config)
    runtime.close()
    assert runtime.health()['overall'] == 'HEALTHY'
    print(json.dumps({'probe': 'P05', 'closed_runtime_health': runtime.health()['overall']}))


def test_p06_temporal_context_does_not_filter_future_observation(tmp_path):
    from datetime import timedelta
    with SQLiteMemoryRepository(tmp_path / 'memory.sqlite3') as memory:
        now = utc_now()
        sid = SourceId.new()
        memory.put(Source(sid, 'test', 'future', now))
        future = now + timedelta(days=365)
        observation = Observation(ObservationId.new(), 'futuremarker', 'text',
            Provenance(ProvenanceId.new(), sid, future), future, future)
        memory.put(observation)
        index = InvertedSeedIndex(memory)
        index.rebuild()
        result = RetrievalService(memory, index).recall(RecallRequest(RecallCue(text='futuremarker', temporal_context=now)))
        assert result.candidates[0].entity_id == observation.id
        print(json.dumps({'probe': 'P06', 'future_observation_returned': True}))


def test_p07_sdk_materialization_guard_unwired(tmp_path):
    config, _ = runtime_at(tmp_path)
    with SyuneRuntime.open(config) as runtime:
        assert runtime.retrieval.materialization_check is None
        assert not any(x.name in {'principal', 'tenant_id', 'purpose', 'permissions'} for x in fields(RecallCue))
        print(json.dumps({'probe': 'P07', 'sdk_materialization_check': None, 'recall_principal_contract': False}))


def test_p08_council_snapshots_enumerate_all_memory(tmp_path):
    from syune.cognition import CognitiveService, CognitiveRequest, ProfileName
    from syune.council import CouncilService, CouncilRequest, CouncilMemberSpec
    config, _ = runtime_at(tmp_path)
    with SyuneRuntime.open(config) as runtime:
        count = 0
        original = runtime.memory.iter_entities
        def counted():
            nonlocal count
            count += 1
            return original()
        runtime.memory.iter_entities = counted
        members = tuple(CouncilMemberSpec(runtime.profiles.by_name(x).id) for x in (ProfileName.GENERAL, ProfileName.RESEARCH))
        runtime.council.run(CouncilRequest(CouncilRequestId.new(), CognitiveRequest(CognitiveRequestId.new(), 'absent'), members))
        assert count == 3
        print(json.dumps({'probe': 'P08', 'members': 2, 'full_memory_enumerations': count}))
