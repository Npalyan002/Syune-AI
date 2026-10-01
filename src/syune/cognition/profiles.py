"""Immutable versioned Domain Activation Profiles over one cognitive core."""
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json
from math import isfinite
from uuid import NAMESPACE_URL, uuid5

from syune.core import ActivationProfileId
from .model import CORE_VERSION, CognitiveBudget

PROFILE_SCHEMA_VERSION="1"

class ProfileName(str,Enum):
    GENERAL="GENERAL";CREATIVE="CREATIVE";SYSTEMS="SYSTEMS";STRATEGY="STRATEGY";PRODUCT="PRODUCT";RESEARCH="RESEARCH"
class ProfileStatus(str,Enum): ACTIVE="ACTIVE";INACTIVE="INACTIVE"
class ProfileSelectionSource(str,Enum): EXPLICIT_CALLER="EXPLICIT_CALLER";DEFAULT_GENERAL="DEFAULT_GENERAL"

@dataclass(frozen=True,slots=True)
class ActivationProfileVersion:
    value:int=1
    def __post_init__(self):
        if type(self.value) is not int or self.value<1:raise ValueError("positive profile version required")
@dataclass(frozen=True,slots=True)
class AttentionProfileConfig:
    direct_weight:float=.55;activation_weight:float=.35;learned_weight:float=.10;diversity_bonus:float=0
    def __post_init__(self):
        if any(not isfinite(x) or x<0 for x in (self.direct_weight,self.activation_weight,self.learned_weight,self.diversity_bonus)):raise ValueError("invalid attention profile")
@dataclass(frozen=True,slots=True)
class RetrievalProfileConfig:
    max_results:int=16;max_hops:int=2;max_fanout:int=16;provenance_weight:float=.1;pattern_weight:float=1
    def __post_init__(self):
        if any(type(x) is not int or x<1 for x in (self.max_results,self.max_hops,self.max_fanout)) or any(not isfinite(x) or x<0 for x in (self.provenance_weight,self.pattern_weight)):raise ValueError("invalid retrieval profile")
@dataclass(frozen=True,slots=True)
class InferenceProfileConfig:
    priorities:tuple[str,...]=("DIRECT_RELATION","MULTI_HOP_SUPPORT","CONVERGENT_SUPPORT","CONFLICT_SIGNAL","MISSING_LINK","SOURCE_OVERLAP","TEMPORAL_ORDER")
@dataclass(frozen=True,slots=True)
class MetacognitionProfileConfig:
    ready_threshold:float=.5;single_source_penalty:float=0;conflict_penalty:float=.25;missing_penalty:float=.2
    def __post_init__(self):
        if any(not isfinite(x) or not 0<=x<=1 for x in (self.ready_threshold,self.single_source_penalty,self.conflict_penalty,self.missing_penalty)):raise ValueError("invalid metacognition profile")
@dataclass(frozen=True,slots=True)
class ResponseProfileConfig:
    max_candidates:int=1;emphasis:str="balanced"
    def __post_init__(self):
        if type(self.max_candidates) is not int or self.max_candidates<1 or not self.emphasis.strip():raise ValueError("invalid response profile")
@dataclass(frozen=True,slots=True)
class ActivationProfile:
    id:ActivationProfileId;name:ProfileName;version:ActivationProfileVersion;description:str;status:ProfileStatus
    attention:AttentionProfileConfig;retrieval:RetrievalProfileConfig;inference:InferenceProfileConfig
    metacognition:MetacognitionProfileConfig;budget:CognitiveBudget;response:ResponseProfileConfig
    allowed_capabilities:tuple[str,...];prohibited_capabilities:tuple[str,...]
    definition_source:str="builtin:src/syune/cognition/profiles.py";core_version:str=CORE_VERSION;schema_version:str=PROFILE_SCHEMA_VERSION
    @property
    def fingerprint(self):
        material=json.dumps(asdict(self),sort_keys=True,separators=(",",":"),default=lambda x:x.value if isinstance(x,Enum) else str(x))
        return sha256(material.encode()).hexdigest()
@dataclass(frozen=True,slots=True)
class ProfileSelection: profile_id:ActivationProfileId|None=None
@dataclass(frozen=True,slots=True)
class ProfileActivation:
    profile_id:ActivationProfileId;name:ProfileName;version:ActivationProfileVersion;selection_source:ProfileSelectionSource
    activated_at:datetime;fingerprint:str;effective_budget:CognitiveBudget;clipped_settings:tuple[str,...]
@dataclass(frozen=True,slots=True)
class ProfileDiagnostics:
    activation:ProfileActivation;modified_dimensions:tuple[str,...];effective_weights:tuple[tuple[str,float],...]

class ProfileErrorCode(str,Enum):
    INVALID_PROFILE="INVALID_PROFILE";PROFILE_INACTIVE="PROFILE_INACTIVE";PROFILE_INCOMPATIBLE="PROFILE_INCOMPATIBLE";PROFILE_REGISTRY_CONFLICT="PROFILE_REGISTRY_CONFLICT"
class ProfileError(Exception):
    def __init__(self,code:ProfileErrorCode,message:str):self.code=code;super().__init__(message)

GLOBAL_HARD_LIMITS=CognitiveBudget(max_recall_rounds=2,max_recall_candidates=32,max_active_entities=12,max_inference_paths=96,max_inference_records=48,max_inference_depth=4,max_graph_edges=384,max_response_candidates=4,max_cycle_ms=2000)
GLOBAL_RETRIEVAL_HARD_LIMITS=RetrievalProfileConfig(32,4,32,2,2)
def _budget(**kw):return replace(CognitiveBudget(),**kw)
def _profile(name,attention=AttentionProfileConfig(),retrieval=RetrievalProfileConfig(),inference=InferenceProfileConfig(),meta=MetacognitionProfileConfig(),budget=CognitiveBudget(),response=ResponseProfileConfig()):
    return ActivationProfile(ActivationProfileId(uuid5(NAMESPACE_URL,f"syune-profile:{name.value}:1")),name,ActivationProfileVersion(),f"{name.value} cognitive emphasis",ProfileStatus.ACTIVE,attention,retrieval,inference,meta,budget,response,("attention","retrieval","inference","metacognition","response"),("memory_write","learning_write","external_actions","agents"))

BUILTIN_PROFILES=(
 _profile(ProfileName.GENERAL),
 _profile(ProfileName.CREATIVE,AttentionProfileConfig(.42,.38,.08,.12),RetrievalProfileConfig(24,3,24,.08,1.2),InferenceProfileConfig(("CONVERGENT_SUPPORT","SOURCE_OVERLAP","MULTI_HOP_SUPPORT","DIRECT_RELATION","MISSING_LINK","CONFLICT_SIGNAL","TEMPORAL_ORDER")),MetacognitionProfileConfig(.42,0,.2,.15),_budget(max_recall_candidates=24,max_active_entities=12,max_inference_paths=80,max_inference_depth=4,max_response_candidates=3),ResponseProfileConfig(3,"alternatives and supported novelty")),
 _profile(ProfileName.SYSTEMS,AttentionProfileConfig(.48,.42,.08,.02),RetrievalProfileConfig(20,3,20,.15,1.1),InferenceProfileConfig(("DIRECT_RELATION","MULTI_HOP_SUPPORT","MISSING_LINK","CONFLICT_SIGNAL","CONVERGENT_SUPPORT","SOURCE_OVERLAP","TEMPORAL_ORDER")),MetacognitionProfileConfig(.55,0,.3,.3),_budget(max_recall_candidates=20,max_active_entities=10,max_inference_paths=90,max_inference_records=40,max_inference_depth=4),ResponseProfileConfig(2,"dependencies constraints and failure modes")),
 _profile(ProfileName.STRATEGY,AttentionProfileConfig(.5,.34,.08,.08),RetrievalProfileConfig(18,3,18,.18,1),InferenceProfileConfig(("CONFLICT_SIGNAL","TEMPORAL_ORDER","MULTI_HOP_SUPPORT","SOURCE_OVERLAP","DIRECT_RELATION","CONVERGENT_SUPPORT","MISSING_LINK")),MetacognitionProfileConfig(.62,.08,.35,.25),_budget(max_recall_candidates=18,max_active_entities=9,max_inference_paths=72),ResponseProfileConfig(2,"alternatives tradeoffs and uncertainty")),
 _profile(ProfileName.PRODUCT,AttentionProfileConfig(.62,.27,.09,.02),RetrievalProfileConfig(16,2,14,.14,.9),InferenceProfileConfig(("DIRECT_RELATION","MISSING_LINK","MULTI_HOP_SUPPORT","CONFLICT_SIGNAL","SOURCE_OVERLAP","CONVERGENT_SUPPORT","TEMPORAL_ORDER")),MetacognitionProfileConfig(.57,.04,.28,.24),_budget(max_active_entities=9,max_inference_paths=56),ResponseProfileConfig(2,"requirements constraints and implementation relevance")),
 _profile(ProfileName.RESEARCH,AttentionProfileConfig(.45,.28,.07,.2),RetrievalProfileConfig(20,2,16,.3,1.15),InferenceProfileConfig(("SOURCE_OVERLAP","CONFLICT_SIGNAL","MISSING_LINK","DIRECT_RELATION","MULTI_HOP_SUPPORT","CONVERGENT_SUPPORT","TEMPORAL_ORDER")),MetacognitionProfileConfig(.75,.2,.4,.35),_budget(max_recall_candidates=20,max_active_entities=10,max_inference_records=40),ResponseProfileConfig(2,"provenance evidence and limitations")),
)

class ProfileRegistry:
    def __init__(self,profiles=BUILTIN_PROFILES):
        self._profiles={};self._names={}
        for profile in profiles:self.register(profile)
    def register(self,profile):
        if profile.id in self._profiles or profile.name in self._names:raise ProfileError(ProfileErrorCode.PROFILE_REGISTRY_CONFLICT,"duplicate profile")
        self._profiles[profile.id]=profile;self._names[profile.name]=profile.id
    def list(self):return tuple(self._profiles[x] for x in sorted(self._profiles,key=str))
    def by_name(self,name:ProfileName):
        profile_id=self._names.get(name)
        if profile_id is None:raise ProfileError(ProfileErrorCode.INVALID_PROFILE,"unknown activation profile")
        return self.resolve(profile_id)
    def resolve(self,profile_id=None):
        profile=self._profiles.get(profile_id or self._names[ProfileName.GENERAL])
        if profile is None:raise ProfileError(ProfileErrorCode.INVALID_PROFILE,"unknown activation profile")
        if profile.status is not ProfileStatus.ACTIVE:raise ProfileError(ProfileErrorCode.PROFILE_INACTIVE,"inactive activation profile")
        if profile.schema_version!=PROFILE_SCHEMA_VERSION or profile.core_version!=CORE_VERSION:raise ProfileError(ProfileErrorCode.PROFILE_INCOMPATIBLE,"incompatible activation profile")
        return profile

def effective_budget(request,profile):
    fields=CognitiveBudget.__dataclass_fields__;values={};clipped=[]
    for name in fields:
        values[name]=min(getattr(request,name),getattr(profile.budget,name),getattr(GLOBAL_HARD_LIMITS,name))
        if values[name]<getattr(request,name):clipped.append(name)
    return CognitiveBudget(**values),tuple(clipped)
