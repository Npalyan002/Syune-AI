# Integrated value evaluation

The benchmark uses seed 255, eight task families, 24 training experiences, and 80 held-out task instances whose IDs never occur in training. Every condition uses the same task distribution and deterministic evaluator.

The integrated E path executes Study ingestion, canonical memory/provenance, truth and temporal eligibility, authorization, lifecycle-backed local promotion, retrieval, organizational promotion, cold-agent authorized retrieval, and future-task scoring. Production services are invoked; no model provider is simulated.

| Condition | Success | Repeated errors |
| --- | ---: | ---: |
| Model/task engine only | 50% | 50% |
| Basic exact memory | 50% | 50% |
| SYUNE memory + retrieval | 75% | 25% |
| Local verified learning | 75% | 25% |
| Controlled organizational learning | 87.5% | 12.5% |

Cold organization/agent performance moves from 50% to 87.5% after six organizational procedures are learned. The result is controlled deterministic evidence, not model improvement.
