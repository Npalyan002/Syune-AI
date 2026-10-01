from uuid import NAMESPACE_URL,uuid5
from syune.core import CouncilSynthesisId
from .model import *
class CouncilSynthesizer:
    def synthesize(self,request_id,mode,members,evidence,agreements,disagreements,gaps,minority,limit):
        completed=sum(x.status is MemberStatus.COMPLETE for x in members);failed=len(members)-completed
        substantive=sum(x.level is DifferenceLevel.SUBSTANTIVE_DISAGREEMENT for x in disagreements);common=sum(x.kind is GapKind.COMMON_GAP for x in gaps)
        conflict=sum(bool(x.cognitive_result and x.cognitive_result.conflict) for x in members);completion=completed/max(1,len(members));overlap=len(evidence.intersection_entity_ids)/max(1,len(evidence.union_entity_ids));diversity=min(1,len(evidence.source_counts)/3)
        gap_penalty=min(1,common*.2);conflict_penalty=min(1,conflict*.2);resource_penalty=1 if evidence.truncated else 0
        readiness=max(0,min(1,.35*completion+.3*overlap+.2*diversity-.1*gap_penalty-.15*conflict_penalty-.1*resource_penalty))
        status=CouncilStatus.PARTIAL if failed else CouncilStatus.CONFLICTED if conflict or substantive else CouncilStatus.INSUFFICIENT_EVIDENCE if common or not evidence.union_entity_ids else CouncilStatus.READY
        components=(("member_completion",completion),("evidence_overlap",overlap),("source_diversity",diversity),("gap_penalty",gap_penalty),("conflict_penalty",conflict_penalty),("resource_penalty",resource_penalty))
        material=f"{request_id}:{mode.value}:{status.value}";sid=CouncilSynthesisId(uuid5(NAMESPACE_URL,material));next_need=(gaps[0].description if gaps else None)
        limitations=("agreement is structural convergence, not truth probability","minority evidence remains advisory","Council performs no Study, Learning, or action")
        return CouncilSynthesis(sid,status,mode,evidence.intersection_entity_ids,tuple(x.id for x in agreements[:limit]),tuple(x.id for x in disagreements[:limit]),tuple(x.entity_id for x in minority[:limit]),tuple(x.id for x in gaps[:limit]),tuple(x.id for x in disagreements if x.level is DifferenceLevel.SUBSTANTIVE_DISAGREEMENT)[:limit],readiness,components,next_need,limitations)
