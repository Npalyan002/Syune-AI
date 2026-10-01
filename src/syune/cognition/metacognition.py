"""Deterministic quality assessment for transient cognitive state."""
from .model import CognitiveStatus, InferenceRecord, InferenceType, MetacognitiveAssessment, UncertaintyCategory


class MetacognitionService:
    """Decompose readiness without treating it as factual probability."""

    def assess(self, *, active_count: int, active_capacity: int, source_count: int,
               inferences: tuple[InferenceRecord, ...], confidence_values: tuple[float, ...],
               truncated: tuple[str, ...], degraded: bool = False, ready_threshold:float=.5,
               single_source_penalty:float=0,conflict_penalty:float=.25,missing_penalty:float=.2) -> MetacognitiveAssessment:
        conflicts = sum(item.type is InferenceType.CONFLICT_SIGNAL for item in inferences)
        gaps = sum(item.type is InferenceType.MISSING_LINK for item in inferences)
        uncertainties = []
        if gaps: uncertainties.append(UncertaintyCategory.MISSING_INFORMATION)
        if conflicts: uncertainties.append(UncertaintyCategory.CONFLICTING_INFORMATION)
        if confidence_values and min(confidence_values) < .5: uncertainties.append(UncertaintyCategory.LOW_CONFIDENCE)
        if source_count <= 1 and active_count: uncertainties.append(UncertaintyCategory.SINGLE_SOURCE_DEPENDENCE)
        if degraded: uncertainties.append(UncertaintyCategory.DEGRADED_MEMORY)
        if truncated: uncertainties.append(UncertaintyCategory.RESOURCE_LIMIT)
        coverage = min(1, active_count / max(1, min(2, active_capacity)))
        support = sum(item.support for item in inferences) / max(1, len(inferences))
        readiness = max(0, min(1, .6 * coverage + .4 * support - conflict_penalty * conflicts - missing_penalty * gaps - (single_source_penalty if source_count<=1 and active_count else 0)))
        if degraded: status = CognitiveStatus.DEGRADED_MEMORY
        elif conflicts: status = CognitiveStatus.CONFLICTED
        elif truncated: status = CognitiveStatus.LIMIT_REACHED
        elif not active_count: status = CognitiveStatus.INSUFFICIENT_EVIDENCE
        elif gaps or readiness<ready_threshold: status = CognitiveStatus.PARTIAL
        else: status = CognitiveStatus.READY
        distribution = (("minimum", min(confidence_values)), ("maximum", max(confidence_values)),
                        ("mean", sum(confidence_values) / len(confidence_values))) if confidence_values else ()
        summary = f"{status.value}; coverage={coverage:.2f}; support={support:.2f}; gaps={gaps}; conflicts={conflicts}"
        return MetacognitiveAssessment(status, readiness, coverage, source_count, gaps, conflicts,
            degraded, bool(truncated), support, distribution, summary, tuple(uncertainties), summary)
