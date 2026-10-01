from dataclasses import replace
from pathlib import Path
import sqlite3
import pytest
from test_supervised_execution import fixture
from test_multimodal_study import png, Provider, make_wav
from test_study_service import pdf_bytes
from syune.core import *
from syune.executive import *
from syune.memory import InMemoryReferenceRepository
from syune.study import StudyService, SqliteStudyRegistry, StudyError
from syune.perception import PerceptionRouter, PerceptionLimits, PerceptionError


@pytest.mark.parametrize('kind',['bytes','pages','segments','duration'])
def test_study_resource_limits_fail_explicitly(tmp_path,kind):
    limits=PerceptionLimits()
    if kind=='bytes': path=tmp_path/'source.txt';path.write_bytes(b'x'*20);limits=replace(limits,max_source_bytes=10)
    if kind=='pages': path=tmp_path/'source.pdf';path.write_bytes(pdf_bytes('first','second'));limits=replace(limits,max_document_pages=1)
    if kind=='segments': path=tmp_path/'source.txt';path.write_text('first\n\nsecond');limits=replace(limits,max_segments=1)
    if kind=='duration': path=tmp_path/'source.wav';make_wav(path);limits=replace(limits,max_audio_duration_ms=1)
    before=path.read_bytes()
    with SqliteStudyRegistry(tmp_path/'study.sqlite3') as registry:
        with pytest.raises(StudyError): StudyService(registry,InMemoryReferenceRepository(),tmp_path,PerceptionRouter(limits=limits)).study(path)
    assert path.read_bytes()==before


def test_provider_output_is_bounded_and_timeout_is_explicit(tmp_path):
    from time import sleep
    class Endless(Provider):
        def perceive(self,data,metadata):
            while True: yield from super().perceive(data,metadata)
    path=tmp_path/'image.png';path.write_bytes(png())
    router=PerceptionRouter(image_provider=Endless('image'),limits=PerceptionLimits(max_segments=2))
    with pytest.raises(PerceptionError) as error: router.perceive(path,path.read_bytes(),SourceId.new(),SourceVersionId.new(),SourceId.new())
    assert error.value.code.value=='SEGMENT_LIMIT_EXCEEDED'
    class Slow(Provider):
        def perceive(self,data,metadata):
            sleep(.01);return super().perceive(data,metadata)
    router=PerceptionRouter(image_provider=Slow('image'),limits=PerceptionLimits(max_wall_time=.001))
    with pytest.raises(PerceptionError) as error: router.perceive(path,path.read_bytes(),SourceId.new(),SourceVersionId.new(),SourceId.new())
    assert error.value.code.value=='PROVIDER_TIMEOUT'


@pytest.mark.parametrize('path',['../escape.txt','nested/../../escape.txt','C:/escape.txt','file.txt:alternate'])
def test_sandbox_traversal_has_zero_file_effect(tmp_path,path):
    runtime,request,adapter,store,plan,envelope,proposal,descriptor=fixture(tmp_path)
    try:
        invocation=CapabilityInvocation(descriptor.id,proposal.id,(('path',path),('content','never')), 'test',SideEffectClass.LOCAL_REVERSIBLE,(),None,None)
        with pytest.raises(ValueError): adapter.invoke(invocation)
        assert not tuple(adapter.root.rglob('*'))
    finally: store.close()


def test_sandbox_artifact_storage_ceiling(tmp_path):
    adapter=LocalSandboxFileAdapter(tmp_path,max_file_bytes=10,max_storage_bytes=10)
    invocation=CapabilityInvocation(CapabilityId.new(),ActionProposalId.new(),(('path','x.txt'),('content','x'*11)),'test',SideEffectClass.LOCAL_REVERSIBLE,(),None,None)
    with pytest.raises(ValueError): adapter.invoke(invocation)
    assert not (tmp_path/'x.txt').exists()


def test_actual_capability_failures_open_circuit_for_later_plan_version(tmp_path):
    runtime,request,adapter,store,plan,envelope,proposal,descriptor=fixture(tmp_path,mode='verify_fail')
    try:
        for version in (1,2,3):
            if version>1:
                current=replace(plan,version=version,prior_version=version-1)
                envelope=ExecutiveService()._envelope(current);runtime.plans.save(current,None,envelope)
                token=replace(request.approval,plan_version=version,envelope_id=envelope.id,
                    fingerprint=approval_fingerprint(plan.id,version,(proposal.id,),request.approval.parameter_hashes,
                    request.approval.risk_ceiling,request.approval.side_effect_classes,request.runtime_budget))
                request=replace(request,plan_version=version,approval_envelope_id=envelope.id,approval=token)
            result=runtime.execute_approved(request)
        assert runtime.circuit.state(descriptor.id) is CircuitState.OPEN
        assert adapter.calls==2 and result.status is RuntimeResultStatus.EXECUTION_BLOCKED
        assert result.gate_decisions[-1].rule_ids==('RUN-030',)
    finally: store.close()


def test_study_schema_current_compatibility_and_missing_table_rejected(tmp_path):
    path=tmp_path/'study.sqlite3'
    with SqliteStudyRegistry(path) as registry:
        registry._db.execute('PRAGMA user_version=0');registry._db.commit()
    with SqliteStudyRegistry(path) as registry:
        assert registry._db.execute('PRAGMA user_version').fetchone()[0]==1
        registry._db.execute('DROP TABLE perception_segments');registry._db.commit()
    with pytest.raises(ValueError,match='schema'): SqliteStudyRegistry(path)
