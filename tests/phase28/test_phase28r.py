import json
import pytest
from benchmarks.phase28r import build_dataset,build_prompt,family_specs,prepare,roster,semantic_audit
from benchmarks.phase28r_dev import blind_review,full_fake_run,information_sufficiency,leakage_tests,prefreeze

def test_complete_semantic_dataset_and_physical_separation():
 p,g,e=build_dataset();assert len(p)==len(g)==1000 and len(e)==10 and len(family_specs())==20
 assert len({x["department"] for x in p})==5 and all("expected_action" not in x for x in p)
 assert all("scenario_narrative" not in x for x in g) and {x["task_id"] for x in p}=={x["task_id"] for x in g}

def test_prompt_builder_rejects_ground_truth_and_poison_never_leaks():
 p,g,_=build_dataset();assert leakage_tests(p,g)["passed"]
 with pytest.raises(ValueError):build_prompt({**p[0],"expected_action":"GROUND_TRUTH_SENTINEL_DO_NOT_EXPOSE"})

def test_counterfactual_ground_truth_prompt_is_byte_identical():
 p,g,_=build_dataset();before=build_prompt(p[0]);g[0]["expected_action"]="COUNTERFACTUAL"
 assert build_prompt(p[0])==before

def test_semantic_audit_blind_review_and_information_sufficiency():
 p,g,_=build_dataset();assert semantic_audit(p)["passed"] and blind_review(p)["passed"] and information_sufficiency(p,g)["passed"]

def test_actions_are_meaningful_and_department_specific():
 specs=family_specs();assert all(len(s["actions"])==3 and all(a["description"] for a in s["actions"]) for s in specs)
 assert len({a["id"] for s in specs for a in s["actions"]})>=45

def test_roster_turnover_and_cold_agents():
 r=roster();assert len(r)==30 and sum(x["start_epoch"]==7 and x["cold"] for x in r)==5

def test_full_fake_provider_and_prefreeze_gate(tmp_path):
 prepare(tmp_path);result=prefreeze(tmp_path)
 assert result["fake_run"]["decisions"]==6000 and result["fake_run"]["provider_calls"]==7850
 assert not result["ready_to_freeze"]
 assert set(result["remaining_blockers"])=={"learning_orchestration_complete","scorers_complete","statistics_complete"}
 assert json.loads((tmp_path/"PREFREEZE_REPORT.json").read_text())["development_status"]=="DEVELOPMENT_INCOMPLETE"
