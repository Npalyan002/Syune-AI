# Lean v1 frozen validation

This page summarizes one controlled, synthetic validation of governance-aware context
selection. It is not a claim of universal superiority over RAG systems or datasets.

## Dataset and comparison

The frozen dataset contains useful authorized records together with records that should
not be model-visible because of authorization, version, temporal, or lifecycle state.
The comparison used the same useful-query workload for a Strong RAG baseline and Lean
SYUNE.

| Metric | Strong RAG | Lean SYUNE |
|---|---:|---:|
| Authorized useful recall | 100% | 100% |
| Precision | 45.5% | 100% |
| Context precision | 45.5% | 100% |

SYUNE excluded:

- 60 unauthorized records
- 1 superseded record
- 1 future-invalid record
- 6 lifecycle-ineligible records

## Interpretation

SYUNE did not improve authorized useful recall over Strong RAG in this dataset: both were
100%. The measured improvement was context cleanliness and governance. Records that were
relevant but ineligible were excluded before context became model-visible.

## Limitations

- The dataset is synthetic and frozen.
- The result establishes behavior for this controlled validation only.
- It does not establish universal task-quality, latency, or retrieval superiority.
- The default vector backend is local-linear, not a production ANN service.
- Results should be reproduced against the source and frozen gates before comparison with
  another retrieval stack.

## Canonical evidence

- [Release blocker closure](../lean_v1_blocker_closure/FINAL_REPORT.md)
- [Quality preregistration](../lean_v1_blocker_closure/QUALITY_PREREGISTRATION.md)
- [Release-candidate validation](../release/RC_VALIDATION.md)
- `benchmarks/lean_product.py`
- `benchmarks/lean_v1_quality_gate.py`
- `benchmarks/lean_v1_release_gate.py`
