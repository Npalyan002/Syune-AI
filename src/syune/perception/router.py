"""Deterministic modality router; providers are optional and explicit."""
from __future__ import annotations
from hashlib import sha256
from time import perf_counter
from uuid import NAMESPACE_URL,uuid5
from syune.core import PerceivedSegmentId,PerceptionRunId,SourceId,SourceVersionId,utc_now
from .inspect import MediaInspector
from .errors import PerceptionError, PerceptionErrorCode
from .model import *

class PerceptionRouter:
    version="1"
    def __init__(self,*,image_provider=None,audio_provider=None,video_provider=None,limits=PerceptionLimits()):
        self.inspector=MediaInspector();self.providers={Modality.IMAGE:image_provider,Modality.AUDIO:audio_provider,Modality.VIDEO:video_provider};self.limits=limits
    def supports(self,suffix):return suffix.lower() in __import__("syune.perception.inspect",fromlist=["FORMATS"]).FORMATS
    def perceive(self,path,data,source_id:SourceId,version_id:SourceVersionId,revision_id:SourceRevisionId):
        started=utc_now();tick=perf_counter();metadata=self.inspector.inspect(path,data,self.limits);inspection=(perf_counter()-tick)*1000
        modality=Modality(metadata.kind.value);provider=self.providers[modality];provider_key=(f"{provider.provider_id}:{provider.model_id}:{provider.model_version}:{provider.execution_location.value}" if provider else "none")
        config=sha256(f"perception-v1:{self.limits}:{provider_key}".encode()).hexdigest();run_id=PerceptionRunId(uuid5(NAMESPACE_URL,f"syune:perception:{revision_id}:{modality.value}:{config}"))
        provider_meta=(ProviderMetadata(provider.provider_id,provider.model_id,provider.model_version,config,provider.execution_location) if provider else None)
        locator=(ImageRegionLocator(0,0,1,1) if modality is Modality.IMAGE else AudioTimeRangeLocator(0,metadata.duration_ms or 0) if modality is Modality.AUDIO else VideoTimeRangeLocator(0,metadata.duration_ms or 0))
        detail=f"{modality.value.lower()} metadata: mime={metadata.mime_type}; bytes={metadata.byte_size}"
        if metadata.width:detail+=f"; dimensions={metadata.width}x{metadata.height}"
        if metadata.duration_ms is not None:detail+=f"; duration_ms={metadata.duration_ms}"
        proposals=[(detail,locator,RepresentationType.METADATA,None,PerceptionMethod.DETERMINISTIC_EXTRACTION,None)]
        components=[("inspection",ComponentState.COMPLETE)];warnings=[];errors=[];provider_ms=0
        if provider is None:
            components.append(("semantic_perception",ComponentState.UNAVAILABLE));warnings.append("semantic perceiver unavailable; no external call made")
        else:
            try:
                tick=perf_counter();outputs=provider.perceive(data,metadata);provider_ms=(perf_counter()-tick)*1000
                for item in outputs:
                    if len(proposals)>=self.limits.max_segments:
                        raise PerceptionError(PerceptionErrorCode.SEGMENT_LIMIT_EXCEEDED,"segment limit exceeded")
                    if sum(len(x[0].encode("utf-8")) for x in proposals)+len(item.content.encode("utf-8"))>self.limits.max_derived_artifact_bytes:
                        raise PerceptionError(PerceptionErrorCode.MEDIA_TOO_LARGE,"derived representation byte limit exceeded")
                    if perf_counter()-tick>self.limits.max_wall_time:
                        raise PerceptionError(PerceptionErrorCode.PROVIDER_TIMEOUT,"provider deadline exceeded")
                    proposals.append((item.content,item.locator,item.representation,item.confidence,PerceptionMethod.MODEL_ASSISTED,provider))
                components.append(("semantic_perception",ComponentState.COMPLETE))
            except PerceptionError:
                raise
            except Exception as exc:
                components.append(("semantic_perception",ComponentState.FAILED));errors.append(f"PROVIDER_FAILURE:{type(exc).__name__}")
        if len(proposals)>self.limits.max_segments:raise PerceptionError(PerceptionErrorCode.SEGMENT_LIMIT_EXCEEDED,"segment limit exceeded")
        segments=[]
        for n,(content,loc,representation,confidence,method,owner) in enumerate(proposals):
            fingerprint=segment_fingerprint(revision_id,loc,representation,config,content);sid=PerceivedSegmentId(uuid5(NAMESPACE_URL,f"syune:segment:{fingerprint}"));pm=None
            if owner:pm=provider_meta
            segments.append(PerceivedSegment(sid,source_id,version_id,revision_id,run_id,modality,loc,representation,content,method,fingerprint,utc_now(),confidence,pm))
        status=RunStatus.PARTIAL if errors or any(x[1] is ComponentState.UNAVAILABLE for x in components) else RunStatus.COMPLETE
        run=PerceptionRun(run_id,source_id,version_id,revision_id,"local-multimodal-router",self.version,config,started,utc_now(),status,tuple(x.id for x in segments),tuple(components),tuple(warnings),tuple(errors),(('bytes',len(data)),('segments',len(segments)),('provider_calls',int(provider is not None))),DeterminismClass.PROVIDER_DEPENDENT if provider else DeterminismClass.DETERMINISTIC,provider_meta)
        return PerceptionResult(run,tuple(segments),metadata,(("inspection",inspection),("provider",provider_ms)))
