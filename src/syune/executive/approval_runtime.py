from hashlib import sha256
from .model import Plan,RiskLevel
from .runtime_model import *
def parameter_hash(proposal,parameters=None):return sha256(repr((proposal.id,parameters if parameters is not None else proposal.parameters,proposal.target_descriptor)).encode()).hexdigest()
def approval_fingerprint(plan_id,version,proposal_ids,parameter_hashes,risk,side_effects,budget):
    return sha256(repr((plan_id,version,tuple(proposal_ids),tuple(parameter_hashes),risk,tuple(side_effects),budget)).encode()).hexdigest()
class ApprovalVerifier:
    def verify(self,plan:Plan,envelope,token,proposal,parameters,now):
        rules=[];reasons=[]
        if token is None:return ApprovalVerification(RuntimeApprovalStatus.INVALID,("APR-000",),("approval missing",),"")
        if token.status is RuntimeApprovalStatus.REVOKED or token.revoked_at:return ApprovalVerification(RuntimeApprovalStatus.REVOKED,("APR-001",),("approval revoked",),token.fingerprint)
        if token.status is not RuntimeApprovalStatus.VALID:return ApprovalVerification(token.status,("APR-002",),("approval is not valid",),token.fingerprint)
        if now>=token.expires_at:return ApprovalVerification(RuntimeApprovalStatus.EXPIRED,("APR-003",),("approval expired",),token.fingerprint)
        if now<token.issued_at:return ApprovalVerification(RuntimeApprovalStatus.INVALID,("APR-009",),("approval not yet issued",),token.fingerprint)
        if token.plan_id!=plan.id or token.plan_version!=plan.version or token.envelope_id!=envelope.id:return ApprovalVerification(RuntimeApprovalStatus.MISMATCHED,("APR-004",),("plan version or envelope mismatch",),token.fingerprint)
        if proposal.id not in token.proposal_ids or proposal.id not in envelope.proposal_ids:return ApprovalVerification(RuntimeApprovalStatus.INSUFFICIENT_SCOPE,("APR-005",),("proposal outside approved scope",),token.fingerprint)
        hashes=dict(token.parameter_hashes)
        if hashes.get(proposal.id)!=parameter_hash(proposal,parameters):return ApprovalVerification(RuntimeApprovalStatus.INSUFFICIENT_SCOPE,("APR-006",),("parameter scope changed",),token.fingerprint)
        expected=approval_fingerprint(token.plan_id,token.plan_version,token.proposal_ids,token.parameter_hashes,token.risk_ceiling,token.side_effect_classes,token.budget)
        if expected!=token.fingerprint:return ApprovalVerification(RuntimeApprovalStatus.INVALID,("APR-007",),("approval fingerprint invalid",),token.fingerprint)
        if proposal.side_effect_class not in token.side_effect_classes:return ApprovalVerification(RuntimeApprovalStatus.INSUFFICIENT_SCOPE,("APR-008",),("side effect outside scope",),token.fingerprint)
        ranks={RiskLevel.LOW:0,RiskLevel.MEDIUM:1,RiskLevel.HIGH:2,RiskLevel.CRITICAL:3,RiskLevel.UNKNOWN:4}
        if ranks[proposal.estimated_risk]>ranks[token.risk_ceiling]:return ApprovalVerification(RuntimeApprovalStatus.INSUFFICIENT_SCOPE,("APR-010",),("proposal risk exceeds approval",),token.fingerprint)
        return ApprovalVerification(RuntimeApprovalStatus.VALID,("APR-100","APR-101","APR-102"),("plan and version match","proposal and parameters match","approval fresh and scoped"),token.fingerprint)
