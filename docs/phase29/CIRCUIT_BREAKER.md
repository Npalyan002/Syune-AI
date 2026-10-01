# Circuit breaker

Provider/model circuits move CLOSED to OPEN after a configured count of systemic failures. After
the recovery interval, one HALF_OPEN probe is admitted; success closes it and failure reopens it.
Rate limit, timeout, connection, provider 5xx and model availability contribute. Schema and semantic
wrong answers do not. Events record provider, model, reason and recovery.
