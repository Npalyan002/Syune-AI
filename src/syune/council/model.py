"""Typed advisory Council contracts; none are canonical memory."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from syune.core import ActivationProfileId,CouncilAgreementId,CouncilDisagreementId,CouncilGapId,CouncilRequestId,CouncilRunId,CouncilSynthesisId,InferenceId,SourceId
from syune.cognition import ActivationProfileVersion,CognitiveRequest,CognitiveResult
from syune.memory.model import NodeId
class CouncilStatus(str,Enum):READY="READY";PARTIAL="PARTIAL";INSUFFICIENT_EVIDENCE="INSUFFICIENT_EVIDENCE";CONFLICTED="CONFLICTED";LIMIT_REACHED="LIMIT_REACHED";FAILED="FAILED"
class CouncilStage(str,Enum):CREATED="CREATED";MEMBERS_RESOLVED="MEMBERS_RESOLVED";MEMBERS_RUNNING="MEMBERS_RUNNING";MEMBERS_COMPLETE="MEMBERS_COMPLETE";ANALYSIS_COMPLETE="ANALYSIS_COMPLETE";SYNTHESIS_COMPLETE="SYNTHESIS_COMPLETE";RESULT_READY="RESULT_READY";FAILED="FAILED"
class MemberStatus(str,Enum):COMPLETE="COMPLETE";FAILED="FAILED";NOT_RUN="NOT_RUN"
class SynthesisMode(str,Enum):BALANCED="BALANCED";EVIDENCE_FIRST="EVIDENCE_FIRST";DIVERGENCE_FIRST="DIVERGENCE_FIRST"
class AgreementKind(str,Enum):ENTITY_OVERLAP="ENTITY_OVERLAP";SOURCE_OVERLAP="SOURCE_OVERLAP";INFERENCE_OVERLAP="INFERENCE_OVERLAP";GAP_OVERLAP="GAP_OVERLAP";CONFLICT_OVERLAP="CONFLICT_OVERLAP";STATUS_OVERLAP="STATUS_OVERLAP";CANDIDATE_TYPE_OVERLAP="CANDIDATE_TYPE_OVERLAP"
class DisagreementKind(str,Enum):EVIDENCE_SELECTION="EVIDENCE_SELECTION";INFERENCE_PRIORITY="INFERENCE_PRIORITY";READINESS_ASSESSMENT="READINESS_ASSESSMENT";GAP_ASSESSMENT="GAP_ASSESSMENT";CONFLICT_ASSESSMENT="CONFLICT_ASSESSMENT";RESPONSE_EMPHASIS="RESPONSE_EMPHASIS";RESOURCE_LIMIT_EFFECT="RESOURCE_LIMIT_EFFECT"
class DisagreementDriver(str,Enum):PROFILE_DRIVEN="PROFILE_DRIVEN";EVIDENCE_DRIVEN="EVIDENCE_DRIVEN";RESOURCE_DRIVEN="RESOURCE_DRIVEN";MIXED="MIXED"
class DifferenceLevel(str,Enum):DIFFERENCE="DIFFERENCE";SUBSTANTIVE_DISAGREEMENT="SUBSTANTIVE_DISAGREEMENT"
class GapKind(str,Enum):COMMON_GAP="COMMON_GAP";PROFILE_SPECIFIC_GAP="PROFILE_SPECIFIC_GAP";MISSING_SOURCE="MISSING_SOURCE";MISSING_RELATION="MISSING_RELATION";MATERIALIZATION_GAP="MATERIALIZATION_GAP";CONFLICT_NEEDS_EVIDENCE="CONFLICT_NEEDS_EVIDENCE";RESOURCE_LIMIT_GAP="RESOURCE_LIMIT_GAP"
@dataclass(frozen=True,slots=True)
class CouncilBudget:
    max_members:int=6;max_total_recall_rounds:int=12;max_total_retrieval_candidates:int=192;max_total_inference_records:int=288;max_per_member_cycle_ms:float=2000;max_evidence_map_entries:int=512;max_synthesis_records:int=128;max_wall_time:float=10000
    def __post_init__(self):
        if any(type(x) is not int or x<1 for x in (self.max_members,self.max_total_recall_rounds,self.max_total_retrieval_candidates,self.max_total_inference_records,self.max_evidence_map_entries,self.max_synthesis_records)) or self.max_members>6 or any(not isfinite(x) or x<=0 for x in (self.max_per_member_cycle_ms,self.max_wall_time)):raise ValueError("bounded positive council limits required")
GLOBAL_COUNCIL_HARD_LIMITS=CouncilBudget()
@dataclass(frozen=True,slots=True)
class CouncilMemberSpec:
    profile_id:ActivationProfileId
    def __post_init__(self):
        if type(self.profile_id) is not ActivationProfileId:raise TypeError("ActivationProfileId required")
@dataclass(frozen=True,slots=True)
class CouncilRequest:
    id:CouncilRequestId;cognitive_request:CognitiveRequest;members:tuple[CouncilMemberSpec,...];budget:CouncilBudget=CouncilBudget();diagnostics:bool=True;synthesis_mode:SynthesisMode=SynthesisMode.BALANCED;correlation_id:str|None=None
    def __post_init__(self):
        if type(self.id) is not CouncilRequestId or not isinstance(self.cognitive_request,CognitiveRequest):raise TypeError("typed Council request required")
        if len(self.members)<2:raise ValueError("at least two explicit Council members required")
        if len(self.members)>self.budget.max_members:raise ValueError("Council member limit exceeded")
        if len({x.profile_id for x in self.members})!=len(self.members):raise ValueError("duplicate Council member")
        if self.cognitive_request.activation_profile is not None:raise ValueError("base CognitiveRequest must not preselect a profile")
@dataclass(frozen=True,slots=True)
class CouncilCognitiveSnapshot:
    memory_fingerprint:str;retrieval_fingerprint:str;learning_fingerprint:str;profiles_fingerprint:str;cognitive_core_version:str;materialization_state:str="NOT_EXPOSED"
@dataclass(frozen=True,slots=True)
class CouncilMemberResult:
    profile_id:ActivationProfileId;profile_version:ActivationProfileVersion;profile_fingerprint:str;status:MemberStatus;cognitive_result:CognitiveResult|None;evidence_ids:tuple[NodeId,...];source_ids:tuple[SourceId,...];inference_ids:tuple[InferenceId,...];timings_ms:tuple[tuple[str,float],...];error_code:str|None=None;error_message:str|None=None
@dataclass(frozen=True,slots=True)
class CouncilRun:
    id:CouncilRunId;request_id:CouncilRequestId;stages:tuple[CouncilStage,...];snapshot:CouncilCognitiveSnapshot;member_profiles:tuple[ActivationProfileId,...]
@dataclass(frozen=True,slots=True)
class EvidenceUsage:
    entity_id:NodeId;source_id:SourceId|None;profiles:tuple[ActivationProfileId,...]
@dataclass(frozen=True,slots=True)
class CouncilEvidenceMap:
    entries:tuple[EvidenceUsage,...];union_entity_ids:tuple[NodeId,...];intersection_entity_ids:tuple[NodeId,...];unique_by_profile:tuple[tuple[ActivationProfileId,tuple[NodeId,...]],...];source_counts:tuple[tuple[SourceId,int],...];truncated:bool=False
@dataclass(frozen=True,slots=True)
class CouncilAgreement:
    id:CouncilAgreementId;kind:AgreementKind;profiles:tuple[ActivationProfileId,...];entity_ids:tuple[NodeId,...]=();source_ids:tuple[SourceId,...]=();inference_ids:tuple[InferenceId,...]=();coverage:float=0;explanation:str="";limitations:tuple[str,...]=("structural convergence is not truth probability",)
@dataclass(frozen=True,slots=True)
class CouncilDisagreement:
    id:CouncilDisagreementId;kind:DisagreementKind;profiles:tuple[ActivationProfileId,...];positions:tuple[tuple[ActivationProfileId,str],...];entity_ids:tuple[NodeId,...];source_ids:tuple[SourceId,...];profile_factors:tuple[str,...];severity:float;driver:DisagreementDriver;level:DifferenceLevel;resolvability:str;explanation:str
@dataclass(frozen=True,slots=True)
class CouncilGap:
    id:CouncilGapId;kind:GapKind;profiles:tuple[ActivationProfileId,...];description:str;entity_ids:tuple[NodeId,...];source_ids:tuple[SourceId,...]
@dataclass(frozen=True,slots=True)
class CouncilSynthesis:
    id:CouncilSynthesisId;status:CouncilStatus;mode:SynthesisMode;shared_entity_ids:tuple[NodeId,...];agreement_ids:tuple[CouncilAgreementId,...];disagreement_ids:tuple[CouncilDisagreementId,...];minority_entity_ids:tuple[NodeId,...];gap_ids:tuple[CouncilGapId,...];unresolved_conflicts:tuple[CouncilDisagreementId,...];council_readiness:float;readiness_components:tuple[tuple[str,float],...];next_information_need:str|None;limitations:tuple[str,...]
@dataclass(frozen=True,slots=True)
class CouncilDiagnostics:
    member_execution_ms:float;analysis_ms:float;synthesis_ms:float;total_ms:float;evidence_entries:int;agreements:int;disagreements:int;completed_members:int;failed_members:int;truncated:tuple[str,...]
@dataclass(frozen=True,slots=True)
class CouncilResult:
    request_id:CouncilRequestId;status:CouncilStatus;run:CouncilRun;members:tuple[CouncilMemberResult,...];evidence_map:CouncilEvidenceMap;agreements:tuple[CouncilAgreement,...];disagreements:tuple[CouncilDisagreement,...];gaps:tuple[CouncilGap,...];minority_insights:tuple[EvidenceUsage,...];synthesis:CouncilSynthesis;diagnostics:CouncilDiagnostics
