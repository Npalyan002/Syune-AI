"""Pure planning policy; decisions authorize review only."""
from uuid import NAMESPACE_URL,uuid5
from syune.core import PolicyDecisionId
from .model import *
class PolicyEvaluator:
    version="1"
    def evaluate(self,proposals,prohibited,hard_violation=False,critical_gap=False):
        records=[]
        for proposal in proposals:
            rules=[];reasons=[];outcome=PolicyOutcome.ALLOW_FOR_REVIEW;severity=proposal.estimated_risk
            if hard_violation:rules.append("POL-001");reasons.append("hard constraint violated");outcome=PolicyOutcome.BLOCK
            if proposal.action_type in prohibited:rules.append("POL-002");reasons.append("action category prohibited");outcome=PolicyOutcome.BLOCK
            if critical_gap:rules.append("POL-003");reasons.append("critical unresolved gap");outcome=PolicyOutcome.BLOCK
            if proposal.side_effect_class in (SideEffectClass.EXTERNAL_IRREVERSIBLE,SideEffectClass.LOCAL_IRREVERSIBLE):rules.append("POL-004");reasons.append("irreversible side effect requires approval");outcome=PolicyOutcome.REQUIRES_APPROVAL if outcome is not PolicyOutcome.BLOCK else outcome
            if proposal.side_effect_class is not SideEffectClass.NONE and proposal.estimated_risk is RiskLevel.UNKNOWN:rules.append("POL-005");reasons.append("unknown side-effect risk requires approval");outcome=PolicyOutcome.REQUIRES_APPROVAL if outcome is not PolicyOutcome.BLOCK else outcome
            if proposal.required_approval.mandatory and proposal.required_approval.kind is not ApprovalKind.NONE:rules.append("POL-006");reasons.append("mandatory reviewer required");outcome=PolicyOutcome.REQUIRES_APPROVAL if outcome is not PolicyOutcome.BLOCK else outcome
            if proposal.side_effect_class is SideEffectClass.NONE and not rules:rules.append("POL-007");reasons.append("read-only proposal may be reviewed")
            material=f"{proposal.id}:{'|'.join(rules)}:{outcome.value}";pid=PolicyDecisionId(uuid5(NAMESPACE_URL,material))
            records.append(PolicyDecisionRecord(pid,outcome,tuple(rules),(proposal.id,),tuple(reasons),severity,self.version,(proposal.action_type.value,proposal.side_effect_class.value)))
        return tuple(records)
