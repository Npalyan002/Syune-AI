# Live repair validation

The preregistered finite trigger allowed three plain-JSON attempts. Attempt one returned a genuine
provider-generated markdown-fenced object and the gateway classified it `INVALID_JSON`. One repair
call committed a schema- and semantic-valid result while preserving marker `ALPHA-17`.

Repair overhead: 602 tokens, 1060.43 ms and $0.0005415. The malformed primary cost $0.00017775.
Repair remained limited to structural eligibility; semantic-invalid answers are not repaired.
Evidence: `evidence/repair_live_v1/report.json`.
