# Cross-process end-to-end recovery

Two real subprocess kill boundaries passed:

| Boundary | Provider calls | Gateway commits | Cognitive commits | Effects | Recovery |
|---|---:|---:|---:|---:|---:|
| after gateway commit, before cognitive transaction | 1 | 1 | 1 | 1 | 6363.67 ms |
| after cognitive DB commit, before acknowledgement | 1 | 1 | 1 | 1 | 6340.52 ms |

The first restart reused the gateway commit and applied cognition once. The second detected APPLIED,
returned the stored transaction result and did not mutate again. Evidence is in
`evidence/cross_process_v1/report.json`.
