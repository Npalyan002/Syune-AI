# Observability validation

The combined deterministic, crash, live truncation, live repair and scale evidence distinguishes
transport failures, remote ambiguity, truncation, JSON parse, schema, semantic, repair, fallback and
terminal failures. Provider/model, role, tokens, latency and cost are reconstructable per attempt.

Content validation failures leave provider health healthy. Repeated systemic 5xx opens the
provider/model circuit; blocked routes report `CIRCUIT_OPEN`. Unavailable adapters report
`UNAVAILABLE`, mixed usable/unusable routes report `DEGRADED`, and fallback is explicit in result
quality and audit metadata.
