# Authorization and data policy

Authorization and purpose filtering occur before `CognitiveOperation` and `ModelExecutionRequest`
construction. The operation records only authorized context identifiers as a stable hash; the
request contains only eligible context. Principal and purpose must exactly match across operation
and request or construction fails. Every P0 request must select external allowed, local-only, or an
explicit provider allowlist. Gateway routing cannot broaden that decision.
