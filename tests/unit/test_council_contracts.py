import pytest
from syune.core import CouncilRequestId
from syune.cognition import CognitiveRequest
from syune.council import CouncilBudget,CouncilMemberSpec,CouncilRequest
from syune.core import CognitiveRequestId,ActivationProfileId

def base():return CognitiveRequest(CognitiveRequestId.new(),text="cue")
def test_membership_contract_minimum_duplicates_and_limits():
    a=CouncilMemberSpec(ActivationProfileId.new());b=CouncilMemberSpec(ActivationProfileId.new())
    assert CouncilRequest(CouncilRequestId.new(),base(),(a,b)).members==(a,b)
    with pytest.raises(ValueError):CouncilRequest(CouncilRequestId.new(),base(),(a,))
    with pytest.raises(ValueError):CouncilRequest(CouncilRequestId.new(),base(),(a,a))
    with pytest.raises(ValueError):CouncilBudget(max_members=7)
    with pytest.raises(TypeError):CouncilMemberSpec("GENERAL")
