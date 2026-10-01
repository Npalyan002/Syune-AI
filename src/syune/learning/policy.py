"""Deterministic bounded plasticity policy v1."""
from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import NAMESPACE_URL, uuid5

from syune.core import LearningProposalId
from .errors import LearningError, LearningErrorCode
from .model import (
    FeedbackLabel, LearningProposal, LearningSignal, LearningSignalKind,
    PlasticityState, TargetKind,
)


@dataclass(frozen=True, slots=True)
class PlasticityConfig:
    version: str = "1"
    max_total_delta: float = 0.5
    positive_utility: float = 0.20
    positive_salience: float = 0.10
    negative_utility: float = -0.20
    negative_salience: float = -0.10
    coactivation_association: float = 0.15
    retraction_utility: float = -0.30
    max_signals_per_batch: int = 1000
    max_proposals_per_batch: int = 4096

    def __post_init__(self) -> None:
        if not 0 < self.max_total_delta <= 1 or self.max_signals_per_batch < 1 or self.max_proposals_per_batch < 1:
            raise LearningError(LearningErrorCode.INVALID_POLICY, "invalid policy bounds")
        for value in (self.positive_utility, self.positive_salience, -self.negative_utility,
                      -self.negative_salience, self.coactivation_association, -self.retraction_utility):
            if not 0 <= value <= self.max_total_delta:
                raise LearningError(LearningErrorCode.INVALID_POLICY, "per-signal delta exceeds bound")


class PlasticityPolicy:
    def __init__(self, config: PlasticityConfig | None = None):
        self.config = config or PlasticityConfig()

    def _step(self, current: float, raw: float) -> float:
        bound = self.config.max_total_delta
        headroom = (bound - current) / bound if raw >= 0 else (bound + current) / bound
        return max(-bound, min(bound, current + raw * max(0.0, headroom)))

    @staticmethod
    def coactivation_key(signal: LearningSignal) -> str:
        return "coactivation:" + "|".join(sorted(target.key for target in signal.targets))

    def propose(self, signal: LearningSignal, targets: tuple[str, ...],
                current: dict[str, PlasticityState]) -> tuple[LearningProposal, ...]:
        if signal.kind is LearningSignalKind.CO_ACTIVATION:
            planned = ((self.coactivation_key(signal), TargetKind.CO_ACTIVATION, 0.0, 0.0,
                        self.config.coactivation_association, False, "explicit co-activation"),)
        else:
            if signal.kind is LearningSignalKind.POSITIVE_OUTCOME:
                utility, salience, flag, reason = self.config.positive_utility, self.config.positive_salience, False, "positive outcome"
            elif signal.kind is LearningSignalKind.NEGATIVE_OUTCOME:
                utility, salience, flag, reason = self.config.negative_utility, self.config.negative_salience, False, "negative outcome"
            elif signal.kind is LearningSignalKind.HUMAN_FEEDBACK:
                positive = signal.feedback_label in {FeedbackLabel.USEFUL, FeedbackLabel.RELEVANT, FeedbackLabel.CORRECT_IN_CONTEXT}
                utility = self.config.positive_utility if positive else self.config.negative_utility
                salience = self.config.positive_salience if positive else self.config.negative_salience
                flag, reason = False, f"explicit human feedback: {signal.feedback_label.value}"
            elif signal.kind is LearningSignalKind.SOURCE_RETRACTION_NOTICE:
                utility, salience, flag, reason = self.config.retraction_utility, 0.0, True, "source retraction notice"
            else:
                raise LearningError(LearningErrorCode.INVALID_SIGNAL, "unsupported signal kind")
            planned = tuple((key, TargetKind.ENTITY, utility, salience, 0.0, flag, reason) for key in targets)

        proposals = []
        for key, kind, utility, salience, association, flag, reason in planned:
            before = current.get(key, PlasticityState(key, kind))
            after = replace(before,
                utility_delta=self._step(before.utility_delta, utility),
                salience_delta=self._step(before.salience_delta, salience),
                association_delta=self._step(before.association_delta, association),
                retraction_flag=before.retraction_flag or flag,
                update_count=before.update_count + 1,
                updated_at=signal.occurred_at)
            proposal_id = LearningProposalId(uuid5(NAMESPACE_URL, f"{signal.id}:{key}:{self.config.version}"))
            proposals.append(LearningProposal(proposal_id, signal.id, key, kind, before, after,
                                               reason, self.config.version, signal.occurred_at))
            current[key] = after
        return tuple(proposals)
