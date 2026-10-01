"""Phase 28R production learning, blind scoring, and frozen analysis integration."""
from __future__ import annotations
import hashlib,json,math,random,sqlite3,statistics
from collections import Counter,defaultdict
from dataclasses import asdict,dataclass
from datetime import datetime
from pathlib import Path
from uuid import NAMESPACE_URL,uuid5
from typing import Any

from syune.core import ProvenanceId,SourceId
from syune.learning import (AttributionQuality,EvidenceKind,EvidenceQuality,Experience,ExperienceId,
 KnowledgeScope,OrganizationalLearningService,OutcomeStatus,ScopeExpansionGrant,ScopeRef,SharedExperience,
 SQLiteOrganizationalLearningStore,SQLiteVerifiedLearningStore,VerifiedExperienceLearningService)
from syune.memory import (DefaultAccessPolicy,SQLiteMemoryRepository,Provenance,SecurityEnvelope,
 Sensitivity,Source)
from syune.retrieval import InvertedSeedIndex
from benchmarks.phase28r import PRODUCT_RULES,SCORER_CONFIG,STATISTICS_CONFIG,sha

ORG="northstar-works";PURPOSE="phase28r-operations";BOOTSTRAP_SEED=281001;BOOTSTRAP_REPS=10000

def uid(namespace:str,value:str):return uuid5(NAMESPACE_URL,f"phase28r:{namespace}:{value}")

class Phase28RExperienceAdapter:
 """Maps provider task + finalized action + sealed outcome; never accepts ground truth records."""
 forbidden={"expected_action","ground_truth_reason","scoring_rubric","outcomes_by_action"}
 def map(self,task:dict[str,Any],selected_action:str,outcome:dict[str,Any],condition:str)->Experience:
  if self.forbidden & set(task):raise ValueError("ground truth cannot enter learning adapter")
  status=OutcomeStatus.SUCCESS if outcome["success"] and not outcome["policy_violation"] else OutcomeStatus.FAILURE
  sid=SourceId(uid("source",task["task_id"]));provenance=Provenance(ProvenanceId(uid("provenance",task["task_id"])),sid,datetime.fromisoformat(task["simulation_timestamp"]))
  auth=task["authorization_context"]
  security=SecurityEnvelope(organization_scope=ORG,project_scope=auth["project"],department_scope=auth["department"],
    agent_scope=auth["agent_id"],purpose_constraints=(task["purpose"],),sensitivity=Sensitivity.INTERNAL,default_policy=DefaultAccessPolicy.SECURE_DENY)
  # Stable operational conditions intentionally exclude epoch labels; otherwise identical situations
  # could never reinforce or contradict one another across time.
  stable_facts=tuple(x for x in task["observable_facts"] if not x.startswith("Current epoch event:"))
  stable_environment={"system_generation":task["environment_state_visible_to_agent"]["system_generation"]}
  conditions=(("facts",json.dumps(stable_facts,sort_keys=True)),("environment",json.dumps(stable_environment,sort_keys=True)))
  return Experience(ExperienceId(uid("experience",f"{condition}:{task['task_id']}")),task["task_family"],conditions,(selected_action,),status,
    EvidenceKind.DETERMINISTIC_TEST,AttributionQuality.DIRECT,EvidenceQuality(.95,1,.95,1,1),datetime.fromisoformat(task["simulation_timestamp"]),
    provenance,f"phase28r:{condition}:{task['task_id']}","sealed-world",task["agent_id"],principal_scope=f"agent:{task['agent_id']}",
    purpose_constraints=(task["purpose"],),environment=json.dumps(task["environment_state_visible_to_agent"],sort_keys=True),
    desired_result_verified=status is OutcomeStatus.SUCCESS,independence_key=task["task_id"],security=security,
    valid_from=datetime.fromisoformat(task["simulation_timestamp"]),limitations=(f"family={task['task_family']}",))


class LearningRuntime:
 def __init__(self,root:Path,condition:str,tasks:list[dict[str,Any]]|None=None):
  self.root=root/condition;self.root.mkdir(parents=True,exist_ok=True);self.condition=condition
  self.memory=SQLiteMemoryRepository(self.root/"memory.sqlite3");self.index=InvertedSeedIndex(self.memory)
  if condition in ("SYUNE_LOCAL","SYUNE_ORGANIZATIONAL"):
   with self.memory._db:
    for task in tasks or ():
     sid=SourceId(uid("source",task["task_id"]));
     if not self.memory.exists(sid):self.memory.put(Source(sid,"synthetic",task["task_id"],datetime.fromisoformat(task["simulation_timestamp"])))
  self.index.rebuild()
  self.local_store=SQLiteVerifiedLearningStore(self.root/"verified.sqlite3") if condition=="SYUNE_LOCAL" else None
  self.org_store=SQLiteOrganizationalLearningStore(self.root/"organizational.sqlite3") if condition=="SYUNE_ORGANIZATIONAL" else None
  self.local=VerifiedExperienceLearningService(self.memory,self.local_store,index=None) if self.local_store else None
  self.org=OrganizationalLearningService(self.memory,self.org_store,index=None) if self.org_store else None
  self.adapter=Phase28RExperienceAdapter();self.processed=set();self.current_epoch=None
 def close(self):
  if self.local_store:self.local_store.close()
  if self.org_store:self.org_store.close()
  self.memory.close()
 def process(self,task,selected_action,outcome):
  if self.current_epoch is not None and task["epoch"]!=self.current_epoch:self.index.rebuild()
  self.current_epoch=task["epoch"]
  exp=self.adapter.map(task,selected_action,outcome,self.condition)
  if str(exp.id) in self.processed:return {"replayed":True}
  if not self.memory.exists(exp.provenance.source_id):
   self.memory.put(Source(exp.provenance.source_id,"synthetic",task["task_id"],exp.occurred_at));self.index.rebuild()
  if self.local:
   self.local.record(exp);states=self.local.maintain();result=states[-1].state.value if states else "UNCHANGED"
  elif self.org:
   auth=task["authorization_context"];source=ScopeRef(KnowledgeScope.AGENT_PRIVATE,ORG,agent_id=task["agent_id"],project_id=auth["project"],department_id=auth["department"])
   item=SharedExperience(exp,source,(f"For {task['task_family']} under the observed conditions, select {selected_action}.",),True,(),(),task["task_id"])
   self.org.submit(item);target=ScopeRef(KnowledgeScope.ORGANIZATION,ORG)
   grant=ScopeExpansionGrant(KnowledgeScope.AGENT_PRIVATE,target,"phase28r-scope-policy","phase28r-learning","verified cross-agent reuse",(task["task_family"],),(task["purpose"],),exp.occurred_at)
   value=self.org.promote(item,target,grant);result=value.state.value if value else "BLOCKED"
  else:result="NOT_APPLICABLE"
  self.processed.add(str(exp.id));return {"replayed":False,"learning_state":result,"experience_id":str(exp.id)}
 def fingerprint(self):
  def db(path,tables):
   if not path.exists():return {}
   con=sqlite3.connect(path);out={t:con.execute(f"select count(*) from {t}").fetchone()[0] for t in tables};con.close();return out
  local=db(self.root/"verified.sqlite3",("verified_experiences","verified_hypotheses","verified_learning_events"))
  org=db(self.root/"organizational.sqlite3",("cross_agent_experiences","organizational_knowledge","organizational_learning_events"))
  lifecycle=self.memory.lifecycle_metrics()
  return {"condition":self.condition,"local":local,"organizational":org,"lifecycle":asdict(lifecycle),"processed":len(self.processed)}


def opaque_evaluation_id(task_id:str,index:int)->str:return f"EV_{index:06d}_{hashlib.sha256(task_id.encode()).hexdigest()[:8]}"
def scorer_input(provider_task,candidate,ground_truth,index):
 return {"evaluation_unit":opaque_evaluation_id(provider_task["task_id"],index),"scenario":provider_task["scenario_narrative"],
  "observable_facts":provider_task["observable_facts"],"available_actions":provider_task["available_actions"],"candidate":candidate,
  "reference":{"expected_action":ground_truth["expected_action"],"rubric":ground_truth["scoring_rubric"]}}
def deterministic_score(candidate,truth):
 selected=candidate.get("selected_action") if isinstance(candidate,dict) else None
 return {"task_success":selected==truth["expected_action"] or selected in truth["acceptable_alternatives"],"abstained":bool(candidate.get("abstain")) if isinstance(candidate,dict) else False,
  "policy_violation":truth["outcomes_by_action"].get(selected,{}).get("policy_violation",False)}
def disagreement(exact,semantic,rubric):
 if exact and semantic and all(rubric.values()):return "ALL_AGREE"
 if not exact and semantic:return "EXACT_FAIL_SEMANTIC_PASS"
 if exact and not all(rubric.values()):return "EXACT_PASS_RUBRIC_FAIL"
 if semantic!=all(rubric.values()):return "SEMANTIC_RUBRIC_DISAGREE"
 return "ALL_FAIL"


def canonical_result(task,treatment,candidate,truth,telemetry=None,knowledge=None):
 telemetry=telemetry or {};knowledge=knowledge or {};score=deterministic_score(candidate,truth)
 return {"task_id":task["task_id"],"treatment":treatment,"epoch":task["epoch"],"agent":task["agent_id"],"department":task["department"],"task_family":task["task_family"],
  "selected_action":candidate.get("selected_action"),"task_success":score["task_success"],"abstained":score["abstained"],"repeated_error":False,
  "cold_agent":task["agent_id"].endswith("replacement"),"knowledge_retrieved":knowledge.get("retrieved",False),"knowledge_included":knowledge.get("included",False),
  "knowledge_reused":knowledge.get("used",False),"negative_transfer":knowledge.get("used",False) and not score["task_success"],"stale_knowledge_used":knowledge.get("stale",False),
  "revocation_violation":knowledge.get("post_revocation",False),"false_promotion":knowledge.get("false_promotion",False),"context_tokens":telemetry.get("context_tokens",0),
  "decision_tokens":telemetry.get("decision_tokens",0),"synthesis_tokens":telemetry.get("synthesis_tokens",0),"learning_tokens":telemetry.get("learning_tokens",0),
  "maintenance_tokens":telemetry.get("maintenance_tokens",0),"operating_cost":telemetry.get("operating_cost",0.0),"decision_latency":telemetry.get("decision_latency",0.0),
  "total_operating_latency":telemetry.get("total_operating_latency",0.0),"security_violation":False,"truth_violation":False}


def mark_repeated_errors(rows):
 seen=set()
 for r in sorted(rows,key=lambda x:(x["treatment"],x["epoch"],x["task_id"])):
  signature=(r["treatment"],r["task_family"],r["selected_action"],r["epoch"]//4)
  r["repeated_error"]=not r["task_success"] and signature in seen
  if not r["task_success"]:seen.add(signature)
 return rows
def time_to_competence(rows,window=20,threshold=.9,hold=10):
 vals=[]
 for i in range(window,len(rows)-hold+1):
  if sum(x["task_success"] for x in rows[i-window:i])/window>=threshold and sum(x["task_success"] for x in rows[i:i+hold])/hold>=threshold:return i
 return None


def endpoints(rows):
 by=defaultdict(list)
 for r in rows:by[r["treatment"]].append(r)
 out={}
 for t,xs in by.items():
  success=sum(r["task_success"] for r in xs);cold=[r for r in xs if r["cold_agent"]]
  out[t]={"tasks":len(xs),"task_success":success/len(xs),"repeated_error_rate":sum(r["repeated_error"] for r in xs)/len(xs),
   "cold_first":cold[0]["task_success"] if cold else None,"cold_first5":sum(r["task_success"] for r in cold[:5])/max(1,len(cold[:5])),"cold_first10":sum(r["task_success"] for r in cold[:10])/max(1,len(cold[:10])),
   "time_to_competence":time_to_competence(xs),"knowledge_reuse":sum(r["knowledge_reused"] for r in xs),"negative_transfer":sum(r["negative_transfer"] for r in xs),
   "stale_use":sum(r["stale_knowledge_used"] for r in xs),"revocation_violations":sum(r["revocation_violation"] for r in xs),"false_promotions":sum(r["false_promotion"] for r in xs),
   "cost_task":sum(r["operating_cost"] for r in xs)/len(xs),"cost_success":sum(r["operating_cost"] for r in xs)/max(1,success),"cumulative_cost":sum(r["operating_cost"] for r in xs),
   "context_tokens":statistics.mean(r["context_tokens"] for r in xs),"latency_p50":statistics.median(r["total_operating_latency"] for r in xs),
   "knowledge_construction_cost":sum(r["operating_cost"] for r in xs if r["learning_tokens"]),"maintenance_cost":sum(r["operating_cost"] for r in xs if r["maintenance_tokens"])}
 return out


def paired_hierarchical_bootstrap(rows,a="RAG_SYNTHESIS",b="SYUNE_ORGANIZATIONAL",reps=BOOTSTRAP_REPS):
 pair=defaultdict(dict)
 for r in rows:
  if r["treatment"] in (a,b):pair[r["task_id"]][r["treatment"]]=r
 complete=[v for v in pair.values() if len(v)==2];groups=defaultdict(list)
 for p in complete:groups[(p[a]["department"],p[a]["task_family"])].append(p)
 rng=random.Random(BOOTSTRAP_SEED);depts=sorted({k[0] for k in groups});draws=[]
 for _ in range(reps):
  sample=[]
  for d in (rng.choice(depts) for _ in depts):
   fams=sorted(k for k in groups if k[0]==d)
   for f in (rng.choice(fams) for _ in fams):sample.extend(groups[f])
  draws.append(statistics.mean(float(p[b]["task_success"])-float(p[a]["task_success"]) for p in sample))
 draws.sort();est=statistics.mean(float(p[b]["task_success"])-float(p[a]["task_success"]) for p in complete)
 return {"estimate":est,"ci_low":draws[int(.025*reps)],"ci_high":draws[int(.975*reps)-1],"reps":reps,"seed":BOOTSTRAP_SEED,"hierarchy":["department","task_family","paired_task"]}


def classify(metrics,comparison,invariants):
 if any(invariants.get(k,0) for k in ("security_violations","future_leaks","cross_treatment_leaks","truth_violations")):return "NEGATIVE"
 syn,org=metrics["RAG_SYNTHESIS"],metrics["SYUNE_ORGANIZATIONAL"]
 quality_ok=comparison["ci_low"]>-.02; economic=org["cost_success"]<.85*syn["cost_success"];learning=org["repeated_error_rate"]<.75*syn["repeated_error_rate"]
 continuity=(org["cold_first10"] or 0)>=(syn["cold_first10"] or 0)-.02;operational=org["latency_p50"]<.8*syn["latency_p50"]
 if comparison["ci_high"]<-.02 or org["stale_use"]>syn["stale_use"]+20:return "NEGATIVE"
 wins=sum((economic,learning,continuity,operational))
 if quality_ok and wins==4:return "STRONGLY_SUPPORTED"
 if quality_ok and economic and wins>=3:return "SUPPORTED"
 if quality_ok and wins==0:return "NOT_SUPPORTED"
 return "INCONCLUSIVE"
