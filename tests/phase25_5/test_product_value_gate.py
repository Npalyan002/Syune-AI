from benchmarks.phase25_5 import run_phase25_5


def test_integrated_value_gate_uses_held_out_tasks_and_all_boundaries(tmp_path):
    result=run_phase25_5(tmp_path)
    assert not set(result["train_experience_ids"]) & set(result["held_out_task_ids"])
    assert all(result["integrated_path"].values())
    conditions=result["conditions"]
    assert conditions["syune_memory_retrieval"]["task_success"] < conditions["controlled_organizational_learning"]["task_success"]
    assert conditions["local_verified_learning"]["task_success"] < conditions["controlled_organizational_learning"]["task_success"]
    assert result["cold_agent"]["delta"] > 0


def test_utility_abstention_negative_transfer_and_invariants(tmp_path):
    result=run_phase25_5(tmp_path)
    knowledge=result["knowledge"]
    assert knowledge["utility_precision"] == 1
    assert knowledge["negative_transfer_rate"] == 0
    assert knowledge["abstention_rate"] > 0
    assert all(value == 0 for value in result["security"].values())
    assert result["truth"] == {"temporal_accuracy":1.0,"contradiction_accuracy":1.0,"false_memory_selections":0}


def test_knowledge_growth_is_bounded_and_raw_sharing_is_worse(tmp_path):
    result=run_phase25_5(tmp_path)
    growth=result["knowledge"]["growth"]
    assert growth["100"]["organizational"] == growth["10000"]["organizational"]
    assert result["raw_vs_verified"]["raw_contamination"] > result["raw_vs_verified"]["verified_contamination"]
    assert result["complexity"]["llm_calls"] == result["complexity"]["tokens"] == 0
