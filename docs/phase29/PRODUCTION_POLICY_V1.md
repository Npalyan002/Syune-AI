# Production policy v1

| Role | Strategy | Output policy | Repair | Fallback | Terminal behavior |
|---|---|---|---|---|---|
| Classification | native structured | small role/schema estimate + 25% | JSON/schema only | explicit equivalent | fail closed |
| Decision | native structured | small estimate + 25% | JSON/schema only | exact by default | fail closed |
| Synthesis | native structured | schema estimate with large headroom | eligible, never semantic-wrong | explicit | classified terminal |
| Knowledge construction | native + semantic validator | medium/large estimate | JSON/schema only | explicit | fail closed |
| Verification | native compact | small estimate | normally off | exact by default | fail closed |
| Planning | native structured | large estimate | JSON/schema only | explicit | classified terminal |
| Scoring | native compact | small estimate | normally off | exact by default | fail closed |
| General | unstructured text | role estimate | off | explicit | classified terminal |

Two-stage is not default: live evidence showed no reliability gain and materially greater latency
and cost. Plain JSON remains the fallback for models without native schema support.
