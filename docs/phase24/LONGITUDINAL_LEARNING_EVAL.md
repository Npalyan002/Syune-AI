# Longitudinal learning evaluation

The deterministic synthetic experiment used one unchanged policy model and executed 10, 100, 1,000, and 10,000 interactions. Six workflow classes have contextual strategy patterns; future tasks include exact repeats, shifted instances, and OOD cases.

| Interaction | Task success | Repeated-error rate | Verified knowledge | Precision | Recall |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 60% | 40% | 0 | 0% | 0% |
| 100 | 90% | 10% | 6 | 100% | 100% |
| 1,000 | 90% | 10% | 6 | 100% | 100% |
| 10,000 | 90% | 10% | 6 | 100% | 100% |

OOD tasks receive no forced learned strategy. No LLM calls, tokens, or model updates occur.
