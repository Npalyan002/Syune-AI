"""Deterministic plan graph, coverage, constraint, and policy validation."""
from .errors import ExecutiveError,ExecutiveErrorCode
from .model import *
class PlanValidator:
    def topological_order(self,steps,dependencies):
        ids={x.id for x in steps};incoming={x:0 for x in ids};out={x:[] for x in ids}
        for edge in dependencies:
            if edge.predecessor_id not in ids or edge.successor_id not in ids:raise ExecutiveError(ExecutiveErrorCode.INVALID_EXECUTIVE_REQUEST,"dependency references unknown step")
            incoming[edge.successor_id]+=1;out[edge.predecessor_id].append(edge.successor_id)
        queue=sorted((x for x,n in incoming.items() if n==0),key=str);ordered=[]
        while queue:
            node=queue.pop(0);ordered.append(node)
            for successor in sorted(out[node],key=str):
                incoming[successor]-=1
                if incoming[successor]==0:queue.append(successor);queue.sort(key=str)
        if len(ordered)!=len(ids):raise ExecutiveError(ExecutiveErrorCode.PLAN_DEPENDENCY_CYCLE,"plan dependency graph contains a cycle")
        return tuple(ordered)
    def validate(self,goal,steps,dependencies,constraints,decisions,limits):
        errors=[];warnings=[]
        if len(steps)>limits.max_steps:errors.append("PLAN_LIMIT_EXCEEDED:max_steps")
        if len(dependencies)>limits.max_dependencies:errors.append("PLAN_LIMIT_EXCEEDED:max_dependencies")
        proposals=tuple(p for s in steps for p in s.action_proposals)
        if len(proposals)>limits.max_proposals:errors.append("PLAN_LIMIT_EXCEEDED:max_proposals")
        hard=tuple(c for c in constraints if c.kind in (ConstraintKind.HARD,ConstraintKind.SAFETY,ConstraintKind.POLICY) and c.satisfied is False)
        errors.extend(f"HARD_CONSTRAINT_VIOLATION:{c.subject}:{c.requirement}" for c in hard)
        coverage={criterion for step in steps for criterion in step.criterion_refs};uncovered=tuple(x for x in goal.success_criteria if x not in coverage)
        if uncovered:warnings.append("uncovered success criteria")
        order=self.topological_order(steps,dependencies)
        blocked={s.id for s in steps if s.status is StepStatus.BLOCKED}
        changed=True
        while changed:
            changed=False
            for edge in dependencies:
                if edge.predecessor_id in blocked and edge.successor_id not in blocked:blocked.add(edge.successor_id);changed=True
        if any(x.outcome is PolicyOutcome.BLOCK for x in decisions):errors.append("POLICY_BLOCKED")
        return PlanValidationResult(not errors,tuple(errors),tuple(warnings),uncovered,tuple(sorted(blocked,key=str)),order,decisions)
def constraint_conflicts(constraints):
    by_subject={}
    conflicts=[]
    for item in constraints:
        if item.kind not in (ConstraintKind.HARD,ConstraintKind.SAFETY,ConstraintKind.POLICY,ConstraintKind.SCOPE):continue
        prior=by_subject.get(item.subject)
        if prior and (prior.requirement!=item.requirement or prior.prohibits!=item.prohibits):conflicts.append(f"{item.subject}: {prior.requirement} <> {item.requirement}")
        else:by_subject[item.subject]=item
    return tuple(conflicts)
