from datetime import timedelta

import pytest

from syune.core import LearningSignalId, ObservationId, ProvenanceId, utc_now
from syune.learning import (
    FeedbackLabel, LearningSignal, LearningSignalKind, LearningSource,
    LearningTarget, PlasticityConfig, PlasticityPolicy,
)
from syune.learning.errors import LearningError


def signal(kind, target, key="one", label=None):
    return LearningSignal(LearningSignalId.new(), kind, utc_now(), (LearningTarget(target),),
                          LearningSource.HUMAN if kind is LearningSignalKind.HUMAN_FEEDBACK else LearningSource.SYSTEM_TEST,
                          key, ProvenanceId.new(), feedback_label=label)


def test_policy_bounds_diminishing_negative_and_human_feedback():
    target = ObservationId.new()
    policy = PlasticityPolicy(PlasticityConfig(max_total_delta=0.5))
    current = {}
    first = policy.propose(signal(LearningSignalKind.POSITIVE_OUTCOME, target), (f"ObservationId:{target}",), current)[0]
    second = policy.propose(signal(LearningSignalKind.POSITIVE_OUTCOME, target, "two"), (f"ObservationId:{target}",), current)[0]
    assert 0 < first.after.utility_delta < second.after.utility_delta <= 0.5
    assert second.after.utility_delta - first.after.utility_delta < first.after.utility_delta
    negative = policy.propose(signal(LearningSignalKind.NEGATIVE_OUTCOME, target, "three"), (f"ObservationId:{target}",), current)[0]
    assert negative.after.utility_delta < second.after.utility_delta
    feedback = policy.propose(signal(LearningSignalKind.HUMAN_FEEDBACK, target, "four", FeedbackLabel.NOT_USEFUL),
                              (f"ObservationId:{target}",), current)[0]
    assert feedback.after.utility_delta < negative.after.utility_delta
    for index in range(100):
        policy.propose(signal(LearningSignalKind.POSITIVE_OUTCOME, target, f"p{index}"),
                       (f"ObservationId:{target}",), current)
    assert current[f"ObservationId:{target}"].utility_delta <= 0.5


def test_invalid_policy_and_signal_contracts():
    with pytest.raises(LearningError): PlasticityConfig(max_total_delta=0)
    with pytest.raises(ValueError):
        LearningSignal(LearningSignalId.new(), LearningSignalKind.CO_ACTIVATION, utc_now(),
                       (LearningTarget(ObservationId.new()),), LearningSource.SYSTEM_TEST,
                       "bad", ProvenanceId.new())
    with pytest.raises(ValueError):
        LearningSignal(LearningSignalId.new(), LearningSignalKind.POSITIVE_OUTCOME,
                       utc_now() - timedelta(0), (LearningTarget(ObservationId.new()),),
                       LearningSource.SYSTEM_TEST, "bad-value", ProvenanceId.new(), outcome_value=2)
