# Production policy v2

| Role | Strategy | Output headroom | Retry | Repair | Fallback / terminal |
|---|---|---:|---|---|---|
| Decision | native structured | 25% | systemic/truncation, max 2 | structural only | exact default / fail closed |
| Synthesis | native structured | 40% | systemic/truncation, max 2 | JSON/schema only | explicit equivalent / finite terminal |
| Knowledge construction | native + semantic validator | 40% | systemic/truncation, max 2 | structural only | explicit / fail closed |
| Verification | compact native | 25% | systemic, max 2 | normally off | exact / fail closed |
| Scoring | compact native | 25% | systemic, max 2 | normally off | exact / fail closed |

The stress matrix used three strategies and shows complete success through 75% of configured
capacity, with deterministic truncation at 100%. Accordingly high-volume synthesis and knowledge
construction reserve at least 40% headroom; compact fixed-shape roles retain 25%. Plain JSON is the
fallback for providers without native schema. Two-stage remains non-default. Budgets precede every
attempt; ambiguous usage stays conservatively reserved.
