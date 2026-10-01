# Call role mapping

| Cognitive operation | Role | Model policy | Data policy | Output policy |
|---|---|---|---|---|
| action selection | DECISION | exact by default | explicitly resolved | native, 25% headroom |
| retrieval synthesis | SYNTHESIS | explicit equivalent allowed | authorized context only | native, 40% |
| knowledge construction | KNOWLEDGE_CONSTRUCTION | exact/equivalent explicit | authorized context only | native + semantic validator, 40% |
| hypothesis verification | VERIFICATION | exact by default | provider/local explicit | compact native, 25% |
| planning | PLANNING | explicit | authorized task state | native, role estimate |
| scoring | SCORING | exact by default | synthetic/authorized | compact native, 25% |

`GENERAL` is not permitted when a specific role applies. No current deterministic subsystem was
converted into an unnecessary model call.
