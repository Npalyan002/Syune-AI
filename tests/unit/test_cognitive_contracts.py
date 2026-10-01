import pytest
from syune.core import CognitiveRequestId,ObservationId
from syune.cognition import CognitiveBudget,CognitiveRequest

def test_intake_contract_and_budget_validation():
    with pytest.raises(ValueError):CognitiveRequest(CognitiveRequestId.new())
    with pytest.raises(TypeError):CognitiveRequest("bad",text="cue")
    with pytest.raises(TypeError):CognitiveRequest(CognitiveRequestId.new(),entity_ids=("bad",))
    with pytest.raises(ValueError):CognitiveBudget(max_recall_rounds=0)
    request=CognitiveRequest(CognitiveRequestId.new(),text="  stable   cue  ",entity_ids=(ObservationId.new(),))
    assert request.text=="  stable   cue  " and request.budget.max_recall_rounds==2
