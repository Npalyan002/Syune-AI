import json
from pathlib import Path
from benchmarks.phase28r import build_dataset
from benchmarks.phase28r_freeze import run_gate
from benchmarks.phase28r_integration import (LearningRuntime,Phase28RExperienceAdapter,canonical_result,
 classify,deterministic_score,disagreement,endpoints,paired_hierarchical_bootstrap,scorer_input)

def test_adapter_maps_every_documented_field_without_ground_truth(tmp_path):
 tasks,truth,_=build_dataset();t=tasks[0];g=truth[0];action=g["expected_action"]
 exp=Phase28RExperienceAdapter().map(t,action,g["outcomes_by_action"][action],"SYUNE_LOCAL")
 assert exp.task_class==t["task_family"] and exp.strategy==(action,) and exp.purpose_constraints==(t["purpose"],)
 assert "expected_action" not in json.dumps(exp,default=str)

def test_isolated_stores_resume_and_replay_idempotency(tmp_path):
 tasks,truth,_=build_dataset();subset=tasks[:20];gt={x["task_id"]:x for x in truth}
 uninterrupted=LearningRuntime(tmp_path/"a","SYUNE_LOCAL",subset)
 for t in subset:
  g=gt[t["task_id"]];uninterrupted.process(t,g["expected_action"],g["outcomes_by_action"][g["expected_action"]])
 expected=uninterrupted.fingerprint();uninterrupted.close()
 first=LearningRuntime(tmp_path/"b","SYUNE_LOCAL",subset)
 for t in subset[:10]:
  g=gt[t["task_id"]];first.process(t,g["expected_action"],g["outcomes_by_action"][g["expected_action"]])
 first.close();resumed=LearningRuntime(tmp_path/"b","SYUNE_LOCAL",subset)
 for t in subset[:10]:
  g=gt[t["task_id"]];resumed.process(t,g["expected_action"],g["outcomes_by_action"][g["expected_action"]])
 for t in subset[10:]:
  g=gt[t["task_id"]];resumed.process(t,g["expected_action"],g["outcomes_by_action"][g["expected_action"]])
 actual=resumed.fingerprint();resumed.close()
 assert expected["local"]==actual["local"] and expected["lifecycle"]==actual["lifecycle"]

def test_blind_scorer_and_disagreement():
 tasks,truth,_=build_dataset();candidate={"selected_action":truth[0]["expected_action"],"abstain":False}
 blind=scorer_input(tasks[0],candidate,truth[0],1);raw=json.dumps(blind)
 assert all(x not in raw for x in ("SYUNE","RAG_SYNTHESIS","treatment"))
 assert deterministic_score(candidate,truth[0])["task_success"]
 assert disagreement(True,True,{"action":True})=="ALL_AGREE"

def test_endpoints_bootstrap_and_all_classifier_labels_reachable():
 tasks,truth,_=build_dataset();rows=[]
 for treatment in ("RAG_SYNTHESIS","SYUNE_ORGANIZATIONAL"):
  for t,g in zip(tasks[:100],truth[:100]):rows.append(canonical_result(t,treatment,{"selected_action":g["expected_action"],"abstain":False},g,{"operating_cost":1,"total_operating_latency":1},{}))
 metrics=endpoints(rows);comparison=paired_hierarchical_bootstrap(rows,reps=100)
 assert comparison["reps"]==100 and set(metrics)=={"RAG_SYNTHESIS","SYUNE_ORGANIZATIONAL"}
 assert classify(metrics,{**comparison,"ci_high":-.03},{})=="NEGATIVE"
 assert classify(metrics,comparison,{"security_violations":1})=="NEGATIVE"
