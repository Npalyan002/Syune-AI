"""Typed, provider-neutral multimodal perception contracts."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from hashlib import sha256
from math import isfinite
from syune.core import DerivedArtifactId,PerceivedSegmentId,PerceptionRunId,SourceId,SourceVersionId,require_utc

SCHEMA_VERSION="1"
class SourceKind(str,Enum):TEXT="TEXT";MARKDOWN="MARKDOWN";PDF="PDF";DOCUMENT="DOCUMENT";IMAGE="IMAGE";AUDIO="AUDIO";VIDEO="VIDEO"
class Modality(str,Enum):TEXT="TEXT";DOCUMENT="DOCUMENT";IMAGE="IMAGE";AUDIO="AUDIO";VIDEO="VIDEO"
class RepresentationType(str,Enum):EXTRACTED_TEXT="EXTRACTED_TEXT";OCR_TEXT="OCR_TEXT";TRANSCRIPT="TRANSCRIPT";SUBTITLE="SUBTITLE";CAPTION="CAPTION";SCENE_DESCRIPTION="SCENE_DESCRIPTION";VISUAL_ATTRIBUTE="VISUAL_ATTRIBUTE";OBJECT_DESCRIPTION="OBJECT_DESCRIPTION";DOCUMENT_STRUCTURE="DOCUMENT_STRUCTURE";TABLE_STRUCTURE="TABLE_STRUCTURE";AUDIO_EVENT_DESCRIPTION="AUDIO_EVENT_DESCRIPTION";MUSIC_STRUCTURE_DESCRIPTION="MUSIC_STRUCTURE_DESCRIPTION";METADATA="METADATA"
class PerceptionMethod(str,Enum):DETERMINISTIC_EXTRACTION="DETERMINISTIC_EXTRACTION";MODEL_ASSISTED="MODEL_ASSISTED"
class ComponentState(str,Enum):COMPLETE="COMPLETE";PARTIAL="PARTIAL";SKIPPED="SKIPPED";UNAVAILABLE="UNAVAILABLE";FAILED="FAILED"
class RunStatus(str,Enum):COMPLETE="COMPLETE";PARTIAL="PARTIAL";FAILED="FAILED"
class DeterminismClass(str,Enum):DETERMINISTIC="DETERMINISTIC";PROVIDER_DEPENDENT="PROVIDER_DEPENDENT"
class ExecutionLocation(str,Enum):LOCAL="LOCAL";EXTERNAL="EXTERNAL"
class ArtifactPolicy(str,Enum):METADATA_ONLY="METADATA_ONLY";CACHE="CACHE";PERSIST="PERSIST"

@dataclass(frozen=True,slots=True)
class TextLocator:
    start:int;end:int
    def __post_init__(self):
        if self.start<0 or self.end<self.start:raise ValueError("invalid text range")
@dataclass(frozen=True,slots=True)
class PageLocator:
    page:int;numbering:str="ONE_BASED"
    def __post_init__(self):
        if self.page<1 or self.numbering!="ONE_BASED":raise ValueError("invalid page locator")
@dataclass(frozen=True,slots=True)
class ImageRegionLocator:
    x:float;y:float;width:float;height:float;coordinate_space:str="NORMALIZED_0_1"
    def __post_init__(self):
        if self.coordinate_space=="NORMALIZED_0_1" and any(not 0<=v<=1 for v in (self.x,self.y,self.width,self.height)):raise ValueError("invalid normalized region")
@dataclass(frozen=True,slots=True)
class AudioTimeRangeLocator:
    start_ms:int;end_ms:int;timebase:str="MILLISECONDS"
    def __post_init__(self):
        if self.start_ms<0 or self.end_ms<self.start_ms:raise ValueError("invalid audio range")
@dataclass(frozen=True,slots=True)
class VideoTimeRangeLocator:
    start_ms:int;end_ms:int;timebase:str="MILLISECONDS"
    def __post_init__(self):
        if self.start_ms<0 or self.end_ms<self.start_ms:raise ValueError("invalid video range")
@dataclass(frozen=True,slots=True)
class VideoFrameLocator:
    timestamp_ms:int;frame_index:int|None=None;timebase:str="MILLISECONDS"
    def __post_init__(self):
        if self.timestamp_ms<0 or (self.frame_index is not None and self.frame_index<0):raise ValueError("invalid video frame")
Locator=TextLocator|PageLocator|ImageRegionLocator|AudioTimeRangeLocator|VideoTimeRangeLocator|VideoFrameLocator

@dataclass(frozen=True,slots=True)
class ProviderMetadata:
    provider_id:str;model_id:str;model_version:str|None;config_fingerprint:str;execution_location:ExecutionLocation
    def __post_init__(self):
        if not self.provider_id.strip() or not self.model_id.strip() or len(self.config_fingerprint)!=64 or not isinstance(self.execution_location,ExecutionLocation):raise ValueError("invalid provider metadata")
@dataclass(frozen=True,slots=True)
class MediaMetadata:
    kind:SourceKind;mime_type:str;byte_size:int;width:int|None=None;height:int|None=None;duration_ms:int|None=None;sample_rate:int|None=None;channels:int|None=None;page_count:int|None=None;frame_rate:float|None=None
    def __post_init__(self):
        if self.byte_size<0 or not self.mime_type.strip() or any(value is not None and value<0 for value in (self.width,self.height,self.duration_ms,self.sample_rate,self.channels,self.page_count)):raise ValueError("invalid media metadata")
@dataclass(frozen=True,slots=True)
class PerceptionLimits:
    max_source_bytes:int=100_000_000;max_document_pages:int=500;max_image_pixels:int=100_000_000;max_audio_duration_ms:int=7_200_000;max_video_duration_ms:int=7_200_000;max_video_keyframes:int=120;max_segments:int=1000;max_provider_calls:int=10;max_derived_artifact_bytes:int=100_000_000;max_wall_time:float=300;max_retry_attempts:int=2
    def __post_init__(self):
        if any(value<=0 for value in (self.max_source_bytes,self.max_document_pages,self.max_image_pixels,self.max_audio_duration_ms,self.max_video_duration_ms,self.max_video_keyframes,self.max_segments,self.max_provider_calls,self.max_derived_artifact_bytes,self.max_wall_time,self.max_retry_attempts)):raise ValueError("positive perception limits required")
@dataclass(frozen=True,slots=True)
class PerceivedSegment:
    id:PerceivedSegmentId;source_id:SourceId;source_version_id:SourceVersionId;source_revision_id:SourceRevisionId;run_id:PerceptionRunId;modality:Modality;locator:Locator;representation:RepresentationType;content:str;method:PerceptionMethod;fingerprint:str;created_at:datetime;perception_confidence:float|None=None;provider:ProviderMetadata|None=None;warnings:tuple[str,...]=()
    def __post_init__(self):
        require_utc(self.created_at)
        if not self.content.strip() or len(self.fingerprint)!=64:raise ValueError("segment content/fingerprint required")
        if self.perception_confidence is not None and (not isfinite(self.perception_confidence) or not 0<=self.perception_confidence<=1):raise ValueError("invalid perception confidence")
@dataclass(frozen=True,slots=True)
class PerceptionRun:
    id:PerceptionRunId;source_id:SourceId;source_version_id:SourceVersionId;source_revision_id:SourceRevisionId;perceiver_id:str;perceiver_version:str;config_fingerprint:str;started_at:datetime;completed_at:datetime;status:RunStatus;segment_ids:tuple[PerceivedSegmentId,...];components:tuple[tuple[str,ComponentState],...];warnings:tuple[str,...];errors:tuple[str,...];resource_usage:tuple[tuple[str,int|float],...];determinism:DeterminismClass;provider:ProviderMetadata|None=None;schema_version:str=SCHEMA_VERSION
    def __post_init__(self):
        require_utc(self.started_at);require_utc(self.completed_at)
        if type(self.id) is not PerceptionRunId or len(self.config_fingerprint)!=64 or not self.perceiver_id.strip():raise ValueError("invalid perception run")
@dataclass(frozen=True,slots=True)
class PerceptionResult: run:PerceptionRun;segments:tuple[PerceivedSegment,...];metadata:MediaMetadata;timings_ms:tuple[tuple[str,float],...]
@dataclass(frozen=True,slots=True)
class DerivedArtifact:
    id:DerivedArtifactId;source_id:SourceId;source_version_id:SourceVersionId;source_revision_id:SourceRevisionId;kind:str;locator:Locator;fingerprint:str;generation_method:str;generation_version:str;storage_policy:ArtifactPolicy
    def __post_init__(self):
        if type(self.id) is not DerivedArtifactId or len(self.fingerprint)!=64 or not self.kind.strip():raise ValueError("invalid derived artifact")

def segment_fingerprint(revision,locator,representation,perceiver_version,content):return sha256(f"{revision}|{locator!r}|{representation.value}|{perceiver_version}|{content}".encode()).hexdigest()
