from pathlib import Path
import shutil,struct,wave
from syune.core import CognitiveRequestId,LearningSignalId,utc_now
from syune.cognition import CognitiveRequest,CognitiveService
from syune.learning import LearningService,LearningSignal,LearningSignalKind,LearningSource,LearningTarget,SQLiteLearningStore
from syune.memory import Claim,InMemoryReferenceRepository,Observation
from syune.perception import AudioTimeRangeLocator,ExecutionLocation,ImageRegionLocator,PerceptionRouter,ProviderOutput,RepresentationType,VideoTimeRangeLocator
from syune.retrieval import InvertedSeedIndex,RetrievalService
from syune.study import Classification,MaterializationState,SqliteStudyRegistry,StudyService

def png(width=3,height=2):return b"\x89PNG\r\n\x1a\n"+b"\0"*8+struct.pack(">II",width,height)+b"fixture"
def make_wav(path):
    with wave.open(str(path),"wb") as item:item.setnchannels(1);item.setsampwidth(2);item.setframerate(8000);item.writeframes(b"\0\0"*800)
def mp4():return b"\0\0\0\x18ftypisom"+b"synthetic-video"
class Provider:
    model_version="1";execution_location=ExecutionLocation.LOCAL
    def __init__(self,kind,fail=False):self.kind=kind;self.fail=fail;self.provider_id="fake-local";self.model_id=kind
    def perceive(self,data,metadata):
        if self.fail:raise RuntimeError("synthetic failure")
        if self.kind=="image":return (ProviderOutput("violet image bridge",ImageRegionLocator(0,0,1,1),RepresentationType.CAPTION,.8),)
        if self.kind=="audio":return (ProviderOutput("cobalt audio bridge",AudioTimeRangeLocator(0,metadata.duration_ms or 0),RepresentationType.TRANSCRIPT,.8),)
        return (ProviderOutput("silver video bridge",VideoTimeRangeLocator(0,1000),RepresentationType.SCENE_DESCRIPTION,.7),)

def observations(memory):return tuple(x for x in memory.iter_entities() if isinstance(x,Observation))
def test_image_audio_video_shared_pipeline_retrieval_cognition_learning_and_revision(tmp_path):
    image=tmp_path/"a.png";image.write_bytes(png());audio=tmp_path/"a.wav";make_wav(audio);video=tmp_path/"a.mp4";video.write_bytes(mp4())
    router=PerceptionRouter(image_provider=Provider("image"),audio_provider=Provider("audio"),video_provider=Provider("video"));memory=InMemoryReferenceRepository()
    with SqliteStudyRegistry(tmp_path/"study.sqlite3") as registry:
        service=StudyService(registry,memory,tmp_path,router);results=[service.study(x) for x in (image,audio,video)]
        assert all(x.materialization is MaterializationState.MATERIALIZED for x in results)
        obs=observations(memory);assert {"caption","transcript","scene_description"}<={x.content_kind for x in obs}
        assert all(x.provenance.locator and x.provenance.process_id.startswith("study:perception:") for x in obs)
        assert not any(isinstance(x,Claim) for x in memory.iter_entities())
        index=InvertedSeedIndex(memory);index.rebuild();retrieval=RetrievalService(memory,index)
        for phrase in ("violet image bridge","cobalt audio bridge","silver video bridge"):assert retrieval.recall(__import__("syune.retrieval",fromlist=["RecallRequest","RecallCue"]).RecallRequest(__import__("syune.retrieval",fromlist=["RecallCue"]).RecallCue(text=phrase))).candidates
        ids=tuple(x.id for x in obs if x.content_kind in {"caption","transcript","scene_description"});assert CognitiveService(memory,retrieval).process(CognitiveRequest(CognitiveRequestId.new(),entity_ids=ids)).context.entity_ids
        with SQLiteLearningStore(tmp_path/"learning.sqlite3") as store:
            target=next(x for x in obs if x.content_kind=="caption");before=target
            learning=LearningService(memory,store);learning.record(LearningSignal(LearningSignalId.new(),LearningSignalKind.POSITIVE_OUTCOME,utc_now(),(LearningTarget(target.id),),LearningSource.SYSTEM_TEST,"multimodal",target.provenance.id,outcome_value=1));learning.consolidate_once();assert memory.get(target.id)==before
        renamed=tmp_path/"renamed.png";shutil.copyfile(image,renamed);again=service.study(renamed);assert again.classification is Classification.ALREADY_STUDIED and again.status.source_id==results[0].status.source_id
        image.write_bytes(png(4,2));changed=service.study(image);assert changed.classification is Classification.CHANGED_SOURCE and changed.status.previous_revision_id==results[0].status.revision_id

def test_partial_failure_is_durable_and_restart_resumes_without_duplicates(tmp_path):
    video=tmp_path/"partial.mp4";video.write_bytes(mp4());memory=InMemoryReferenceRepository();db=tmp_path/"study.sqlite3"
    with SqliteStudyRegistry(db) as registry:
        first=StudyService(registry,memory,tmp_path,PerceptionRouter(video_provider=Provider("video",True))).study(video)
        assert registry.perception_summary(first.status.revision_id)[-1][1]=="PARTIAL";count=len(observations(memory))
    with SqliteStudyRegistry(db) as registry:
        resumed=StudyService(registry,memory,tmp_path,PerceptionRouter(video_provider=Provider("video"))).study(video)
        assert resumed.classification is Classification.INCOMPLETE
        assert registry.perception_summary(resumed.status.revision_id)[-1][1]=="COMPLETE"
        assert len(observations(memory))==count+1
        again=StudyService(registry,memory,tmp_path,PerceptionRouter(video_provider=Provider("video"))).study(video)
        assert again.classification is Classification.ALREADY_STUDIED and len(observations(memory))==count+1

def test_no_provider_makes_no_calls_and_records_unavailable(tmp_path):
    image=tmp_path/"local.png";image.write_bytes(png());memory=InMemoryReferenceRepository()
    with SqliteStudyRegistry(tmp_path/"study.sqlite3") as registry:
        result=StudyService(registry,memory,tmp_path).study(image)
        assert registry.perception_summary(result.status.revision_id)[-1][1]=="PARTIAL"
        assert len(observations(memory))==1 and observations(memory)[0].content_kind=="metadata"
