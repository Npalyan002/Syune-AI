# Evidence retention

Default policy: raw provider content 30 days, normalized committed result 180 days, audit lineage
365 days, aggregated usage/cost telemetry 730 days. Deployments may shorten raw retention based on
classification or legal policy; holds may extend it explicitly.

At 100K attempts, replacing raw bodies while retaining normalized evidence and identifiers reduced
the database from 279,990,272 to 94,879,744 bytes: 185,110,528 bytes or 66.11%. Attempt identity,
model, state, finish reason, usage, cost, timestamps, failure class and commit lineage remained.
