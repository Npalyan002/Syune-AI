import json
from pathlib import Path
from benchmarks.phase31 import BUDGET, DECISION_RULES, SAMPLE, TREATMENTS, dataset, freeze
from benchmarks.phase31_execution import Runner
from benchmarks.phase31_reporting import analyze

def test_dataset_and_ground_truth_are_separate_and_complete(tmp_path):
 tasks,truth=dataset();assert len(tasks)==len(truth)==200
 assert len({x["task_family"] for x in tasks})==20 and len({x["department"] for x in tasks})==5
 assert len({x["epoch"] for x in tasks})==10
 forbidden={"expected_action","outcomes_by_action","ground_truth_reason"}
 assert all(not forbidden.intersection(x) for x in tasks)
 assert all("expected_action" in x for x in truth)

def test_preregistered_decision_and_budget_are_frozen(tmp_path):
 result=freeze(tmp_path);manifest=json.loads((tmp_path/"freeze_manifest.json").read_text())
 assert result==manifest and DECISION_RULES and BUDGET["max_provider_calls"]>=800
 assert SAMPLE["tasks_per_treatment"]==200 and tuple(TREATMENTS)==("STRONG_RAG","RAG_SYNTHESIS","PRODUCTION_SYUNE")

def test_full_fake_gateway_traversal_and_analysis(tmp_path):
 freeze(tmp_path/"freeze");runner=Runner(tmp_path,False)
 try: result=runner.run()
 finally:runner.close()
 assert result["status"]=="COMPLETE" and result["rows"]==600 and result["provider_calls"]==800
 report=analyze(tmp_path,tmp_path/"docs")
 assert report["experiment"]["calls"]==800 and report["phase_31_status"]=="PASS"
 assert report["product_decision"] in {"BUILD_SYUNE_FULL_PRODUCT","BUILD_SYUNE_LEAN_PRODUCT","PIVOT_TO_GOVERNED_MEMORY_PLATFORM","DO_NOT_PRODUCTIZE_CURRENT_ARCHITECTURE"}

def test_phase31_live_path_imports_production_gateway_only():
 source=Path("benchmarks/phase31_execution.py").read_text(encoding="utf-8")
 assert "OpenAIResponsesAdapter" in source and "ModelGateway" in source
 assert "urllib.request" not in source and "requests." not in source and "httpx." not in source
