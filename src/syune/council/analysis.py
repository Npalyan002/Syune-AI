"""Deterministic structural comparison of Council member results."""
from collections import defaultdict
from uuid import NAMESPACE_URL,uuid5
from syune.core import CouncilAgreementId,CouncilDisagreementId,CouncilGapId
from .model import *
def _key(value):return type(value).__name__,str(value)
def _aid(request_id,kind,material):return CouncilAgreementId(uuid5(NAMESPACE_URL,f"council:{request_id}:agreement:{kind.value}:{material}"))
def _did(request_id,kind,material):return CouncilDisagreementId(uuid5(NAMESPACE_URL,f"council:{request_id}:disagreement:{kind.value}:{material}"))
def _gid(request_id,kind,material):return CouncilGapId(uuid5(NAMESPACE_URL,f"council:{request_id}:gap:{kind.value}:{material}"))
class CouncilAnalyzer:
    def analyze(self,request_id,members,max_entries=512):
        complete=tuple(x for x in members if x.status is MemberStatus.COMPLETE and x.cognitive_result);profiles=tuple(x.profile_id for x in complete)
        usage=defaultdict(list);sources={}
        for member in complete:
            for item in member.cognitive_result.context.attention:
                usage[item.entity_id].append(member.profile_id);sources[item.entity_id]=item.source_id
        entries=tuple(EvidenceUsage(entity,sources.get(entity),tuple(sorted(set(ps),key=str))) for entity,ps in sorted(usage.items(),key=lambda x:_key(x[0])))
        truncated=len(entries)>max_entries;entries=entries[:max_entries];union=tuple(x.entity_id for x in entries);intersection=tuple(x.entity_id for x in entries if len(x.profiles)==len(complete) and complete)
        unique=tuple((p,tuple(x.entity_id for x in entries if x.profiles==(p,))) for p in sorted(profiles,key=str));source_counts=defaultdict(int)
        for item in entries:
            if item.source_id:source_counts[item.source_id]+=len(item.profiles)
        evidence=CouncilEvidenceMap(entries,union,intersection,unique,tuple(sorted(source_counts.items(),key=lambda x:str(x[0]))),truncated)
        agreements=[]
        for item in entries:
            if len(item.profiles)>=2:agreements.append(CouncilAgreement(_aid(request_id,AgreementKind.ENTITY_OVERLAP,item.entity_id),AgreementKind.ENTITY_OVERLAP,item.profiles,(item.entity_id,),((item.source_id,) if item.source_id else ()),coverage=len(item.profiles)/max(1,len(complete)),explanation=f"entity selected by {len(item.profiles)}/{len(complete)} completed profiles"))
        source_profiles=defaultdict(set)
        for item in entries:
            if item.source_id:source_profiles[item.source_id].update(item.profiles)
        for source_id,ps in sorted(source_profiles.items(),key=lambda x:str(x[0])):
            if len(ps)>=2:agreements.append(CouncilAgreement(_aid(request_id,AgreementKind.SOURCE_OVERLAP,source_id),AgreementKind.SOURCE_OVERLAP,tuple(sorted(ps,key=str)),source_ids=(source_id,),coverage=len(ps)/max(1,len(complete)),explanation="members selected evidence from the same source"))
        inference_profiles=defaultdict(set)
        for member in complete:
            for inference_id in member.inference_ids:inference_profiles[inference_id].add(member.profile_id)
        for inference_id,ps in sorted(inference_profiles.items(),key=lambda x:str(x[0])):
            if len(ps)>=2:agreements.append(CouncilAgreement(_aid(request_id,AgreementKind.INFERENCE_OVERLAP,inference_id),AgreementKind.INFERENCE_OVERLAP,tuple(sorted(ps,key=str)),inference_ids=(inference_id,),coverage=len(ps)/max(1,len(complete)),explanation="members produced the same structural inference"))
        status_groups=defaultdict(list)
        for member in complete:status_groups[member.cognitive_result.status.value].append(member.profile_id)
        for status,ps in sorted(status_groups.items()):
            if len(ps)>=2:agreements.append(CouncilAgreement(_aid(request_id,AgreementKind.STATUS_OVERLAP,status),AgreementKind.STATUS_OVERLAP,tuple(sorted(ps,key=str)),coverage=len(ps)/max(1,len(complete)),explanation=f"shared cognitive status {status}"))
        gaps_by_text=defaultdict(list)
        for member in complete:
            for gap in member.cognitive_result.unresolved_gaps:gaps_by_text[gap].append(member.profile_id)
        gaps=[]
        for text,ps in sorted(gaps_by_text.items()):
            kind=GapKind.COMMON_GAP if len(set(ps))>=2 else GapKind.PROFILE_SPECIFIC_GAP;unique_ps=tuple(sorted(set(ps),key=str));gaps.append(CouncilGap(_gid(request_id,kind,text),kind,unique_ps,text,(),()))
            if kind is GapKind.COMMON_GAP:agreements.append(CouncilAgreement(_aid(request_id,AgreementKind.GAP_OVERLAP,text),AgreementKind.GAP_OVERLAP,unique_ps,coverage=len(unique_ps)/max(1,len(complete)),explanation="members identify the same unresolved gap"))
        disagreements=[]
        if len(status_groups)>1:
            positions=tuple((m.profile_id,m.cognitive_result.status.value) for m in complete);substantive=any(x in status_groups for x in ("CONFLICTED","INSUFFICIENT_EVIDENCE"))
            disagreements.append(CouncilDisagreement(_did(request_id,DisagreementKind.READINESS_ASSESSMENT,str(positions)),DisagreementKind.READINESS_ASSESSMENT,profiles,positions,union,tuple(source_counts),("profile readiness thresholds",),.8 if substantive else .4,DisagreementDriver.PROFILE_DRIVEN,DifferenceLevel.SUBSTANTIVE_DISAGREEMENT if substantive else DifferenceLevel.DIFFERENCE,"requires more evidence","members recommend different readiness states"))
        selected={m.profile_id:set(m.evidence_ids) for m in complete}
        if len({frozenset(x) for x in selected.values()})>1:
            positions=tuple((p,",".join(str(x) for x in sorted(ids,key=_key))) for p,ids in sorted(selected.items(),key=lambda x:str(x[0])))
            disagreements.append(CouncilDisagreement(_did(request_id,DisagreementKind.EVIDENCE_SELECTION,str(positions)),DisagreementKind.EVIDENCE_SELECTION,profiles,positions,union,tuple(source_counts),("profile attention and retrieval overlay",),.35,DisagreementDriver.PROFILE_DRIVEN,DifferenceLevel.DIFFERENCE,"profile-dependent","members selected different supported evidence"))
        conflicts={m.profile_id:m.cognitive_result.conflict for m in complete}
        if len(set(conflicts.values()))>1:
            positions=tuple((p,str(v)) for p,v in sorted(conflicts.items(),key=lambda x:str(x[0])));disagreements.append(CouncilDisagreement(_did(request_id,DisagreementKind.CONFLICT_ASSESSMENT,str(positions)),DisagreementKind.CONFLICT_ASSESSMENT,profiles,positions,union,tuple(source_counts),("evidence reach","profile conflict sensitivity"),.9,DisagreementDriver.MIXED,DifferenceLevel.SUBSTANTIVE_DISAGREEMENT,"needs conflicting evidence review","conflict visibility differs; no winner selected"))
        elif conflicts and all(conflicts.values()):
            positions=tuple((p,"conflicting canonical relation preserved") for p in sorted(conflicts,key=str));disagreements.append(CouncilDisagreement(_did(request_id,DisagreementKind.CONFLICT_ASSESSMENT,"unanimous-structural-conflict"),DisagreementKind.CONFLICT_ASSESSMENT,profiles,positions,union,tuple(source_counts),("canonical conflict relation",),1,DisagreementDriver.EVIDENCE_DRIVEN,DifferenceLevel.SUBSTANTIVE_DISAGREEMENT,"requires additional evidence","all members preserve the conflict; Council selects no winner"))
        response_types={m.profile_id:tuple(x.type.value for x in m.cognitive_result.responses) for m in complete}
        if len(set(response_types.values()))>1:
            positions=tuple((p,",".join(v)) for p,v in sorted(response_types.items(),key=lambda x:str(x[0])));disagreements.append(CouncilDisagreement(_did(request_id,DisagreementKind.RESPONSE_EMPHASIS,str(positions)),DisagreementKind.RESPONSE_EMPHASIS,profiles,positions,union,tuple(source_counts),("profile response policy",),.25,DisagreementDriver.PROFILE_DRIVEN,DifferenceLevel.DIFFERENCE,"advisory","response emphasis differs"))
        minority=tuple(x for x in entries if len(x.profiles)==1)
        return evidence,tuple(sorted(agreements,key=lambda x:(x.kind.value,str(x.id)))),tuple(sorted(disagreements,key=lambda x:(x.kind.value,str(x.id)))),tuple(gaps),minority
