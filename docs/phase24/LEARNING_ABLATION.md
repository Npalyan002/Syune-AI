# Learning ablation

| Arm | Task success | Repeated-error rate | Mean context | Decision latency |
| --- | ---: | ---: | ---: | ---: |
| Learning off | 50% | 50% | 0.0 | 0.0458 ms |
| Memory only | 60% | 40% | 0.2 | 0.0282 ms |
| Verified learning | 90% | 10% | 0.8 | 0.0301 ms |

Memory-only helps exact repeats. Verified learning also helps shifted tasks in known classes. This is controlled synthetic evidence, not production-model evidence.
