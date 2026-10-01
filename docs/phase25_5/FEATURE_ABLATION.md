# Feature ablation

| Ablation | Result | Decision |
| --- | --- | --- |
| Verified local learning off | 75% → 75% versus strong RAG | No task-quality value demonstrated here |
| Organizational learning off | 87.5% → 75% | Measured 12.5-point contribution |
| Semantic retrieval off | No change | Fixture uses lexical retrieval; semantic value unvalidated |
| Associative retrieval off | No material fixture change | Keep as parity/research pending broader tasks |
| Temporal truth off | No timeless-fixture quality change | Keep safety-critical; not a safe production toggle |
| Lifecycle off | No all-active-fixture quality change | Keep for revocation/staleness correctness |

Security was not disabled on the production path. Prior isolated adversarial tests supply its counterfactual evidence.
