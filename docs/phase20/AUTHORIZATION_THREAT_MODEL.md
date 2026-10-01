# Authorization threat model

Protected threats include cross-user, cross-agent, cross-project, cross-organization, department, purpose, sensitivity, cache/principal-switch, learning-evidence, provenance, and association-metadata leakage.

Controls operate before ranking and context creation. Retrieval results are computed per request and are not cached across principals. Direct memory access returns the same not-found surface for absent and unauthorized resources. Timing is not constant-time; coarse result-count and timing inference remains a residual risk. Audit storage itself must be exposed only through future explicit administrative policy.
