"""Typed transient Cognitive Core contracts."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite
from typing import TYPE_CHECKING
from syune.core import ActivationProfileId,CognitiveRequestId, InferenceId, ResponseCandidateId, SourceId, require_utc
from syune.memory.model import NodeId
from syune.memory.security import AccessContext
if TYPE_CHECKING:
    from .profiles import ProfileDiagnostics

CORE_VERSION = "1"

class CognitiveStatus(str, Enum):
    READY="READY"; PARTIAL="PARTIAL"; INSUFFICIENT_EVIDENCE="INSUFFICIENT_EVIDENCE"
    CONFLICTED="CONFLICTED"; DEGRADED_MEMORY="DEGRADED_MEMORY"; LIMIT_REACHED="LIMIT_REACHED"; FAILED="FAILED"

class InferenceType(str, Enum):
    DIRECT_RELATION="DIRECT_RELATION"; MULTI_HOP_SUPPORT="MULTI_HOP_SUPPORT"
    CONVERGENT_SUPPORT="CONVERGENT_SUPPORT"; CONFLICT_SIGNAL="CONFLICT_SIGNAL"
    MISSING_LINK="MISSING_LINK"; SOURCE_OVERLAP="SOURCE_OVERLAP"; TEMPORAL_ORDER="TEMPORAL_ORDER"

class UncertaintyCategory(str, Enum):
    MISSING_INFORMATION="MISSING_INFORMATION"; CONFLICTING_INFORMATION="CONFLICTING_INFORMATION"
    LOW_CONFIDENCE="LOW_CONFIDENCE"; SINGLE_SOURCE_DEPENDENCE="SINGLE_SOURCE_DEPENDENCE"
    DEGRADED_MEMORY="DEGRADED_MEMORY"; RESOURCE_LIMIT="RESOURCE_LIMIT"; UNSUPPORTED_INFERENCE="UNSUPPORTED_INFERENCE"

class ResponseType(str, Enum):
    ANSWER_SUMMARY="ANSWER_SUMMARY"; REQUEST_MORE_CONTEXT="REQUEST_MORE_CONTEXT"
    REPORT_CONFLICT="REPORT_CONFLICT"; REPORT_INSUFFICIENT_EVIDENCE="REPORT_INSUFFICIENT_EVIDENCE"
    SUGGEST_RECALL_FOCUS="SUGGEST_RECALL_FOCUS"

class CognitiveStage(str, Enum):
    CREATED="CREATED"; INTAKE_COMPLETE="INTAKE_COMPLETE"; RECALL_COMPLETE="RECALL_COMPLETE"
    ATTENTION_COMPLETE="ATTENTION_COMPLETE"; CONTEXT_READY="CONTEXT_READY"; INFERENCE_COMPLETE="INFERENCE_COMPLETE"
    METACOGNITION_COMPLETE="METACOGNITION_COMPLETE"; RESULT_READY="RESULT_READY"; FAILED="FAILED"

@dataclass(frozen=True, slots=True)
class CognitiveCycle:
    request_id:CognitiveRequestId; stages:tuple[CognitiveStage,...]
    def __post_init__(self):
        if type(self.request_id) is not CognitiveRequestId or not self.stages or self.stages[0] is not CognitiveStage.CREATED: raise ValueError("valid cognitive cycle required")

@dataclass(frozen=True, slots=True)
class CognitiveBudget:
    max_recall_rounds:int=2; max_recall_candidates:int=16; max_active_entities:int=8
    max_inference_paths:int=64; max_inference_records:int=32; max_inference_depth:int=3
    max_graph_edges:int=256; max_response_candidates:int=3; max_cycle_ms:float=1000.0
    def __post_init__(self):
        values=(self.max_recall_rounds,self.max_recall_candidates,self.max_active_entities,self.max_inference_paths,
                self.max_inference_records,self.max_inference_depth,self.max_graph_edges,self.max_response_candidates)
        if any(type(x) is not int or x<1 for x in values) or not isfinite(self.max_cycle_ms) or self.max_cycle_ms<=0: raise ValueError("positive cognitive limits required")

@dataclass(frozen=True, slots=True)
class CognitiveRequest:
    id:CognitiveRequestId; text:str|None=None; entity_ids:tuple[NodeId,...]=(); source_ids:tuple[SourceId,...]=()
    context_ids:tuple[NodeId,...]=(); temporal_context:datetime|None=None; correlation_id:str|None=None
    budget:CognitiveBudget=CognitiveBudget(); diagnostics:bool=True;activation_profile:ActivationProfileId|None=None
    access_context:AccessContext|None=None
    def __post_init__(self):
        if type(self.id) is not CognitiveRequestId: raise TypeError("CognitiveRequestId required")
        if self.activation_profile is not None and type(self.activation_profile) is not ActivationProfileId:raise TypeError("ActivationProfileId required")
        if not (self.text and self.text.strip()) and not self.entity_ids and not self.source_ids and not self.context_ids: raise ValueError("nonempty cue required")
        for ids in (self.entity_ids,self.context_ids):
            if not isinstance(ids,tuple) or any(not isinstance(x,NodeId.__args__) for x in ids): raise TypeError("typed memory IDs required")
        if not isinstance(self.source_ids,tuple) or any(type(x) is not SourceId for x in self.source_ids): raise TypeError("typed SourceIds required")
        if self.temporal_context is not None: require_utc(self.temporal_context)
        if self.access_context is not None and not isinstance(self.access_context,AccessContext): raise TypeError("AccessContext required")

@dataclass(frozen=True, slots=True)
class AttentionItem:
    entity_id:NodeId; rank:int; score:float; components:tuple[tuple[str,float],...]; reason:str; source_id:SourceId|None

@dataclass(frozen=True, slots=True)
class WorkingContext:
    entity_ids:tuple[NodeId,...]; provenance_source_ids:tuple[SourceId,...]; attention:tuple[AttentionItem,...]
    truncated:tuple[str,...]; recall_rounds:int

@dataclass(frozen=True, slots=True)
class InferenceRecord:
    id:InferenceId; type:InferenceType; entity_ids:tuple[NodeId,...]; association_ids:tuple[str,...]
    source_ids:tuple[SourceId,...]; rule_id:str; support:float; explanation:str; structural:bool=True

@dataclass(frozen=True, slots=True)
class MetacognitiveAssessment:
    status:CognitiveStatus; readiness:float; evidence_coverage:float; source_diversity:int
    gap_count:int; conflict_count:int; materialization_degraded:bool; retrieval_truncated:bool
    inference_support:float; confidence_distribution:tuple[tuple[str,float],...]; epistemic_summary:str
    uncertainties:tuple[UncertaintyCategory,...]; explanation:str

@dataclass(frozen=True, slots=True)
class ResponseCandidate:
    id:ResponseCandidateId; type:ResponseType; content:str; entity_ids:tuple[NodeId,...]
    inference_ids:tuple[InferenceId,...]; source_ids:tuple[SourceId,...]; status:CognitiveStatus
    readiness:float; limitations:tuple[str,...]; selection_reason:str

@dataclass(frozen=True, slots=True)
class CognitiveResult:
    request_id:CognitiveRequestId; status:CognitiveStatus; cycle:CognitiveCycle; context:WorkingContext
    inferences:tuple[InferenceRecord,...]; assessment:MetacognitiveAssessment
    responses:tuple[ResponseCandidate,...]; unresolved_gaps:tuple[str,...]; conflict:bool
    provenance_source_ids:tuple[SourceId,...]; timings_ms:tuple[tuple[str,float],...]
    diagnostics:tuple[tuple[str,int|float|str],...]; truncated:tuple[str,...]; profile_diagnostics:ProfileDiagnostics|None=None;version:str=CORE_VERSION
