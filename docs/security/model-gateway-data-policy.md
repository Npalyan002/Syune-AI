# ModelGateway data policy

Authorization and data policy are enforced before provider routing. `LOCAL_ONLY`, external-provider disablement, and provider allowlists are hard gates.

API keys remain in process memory and are never written to evidence. Authorization headers, credentials, secrets, cookies, and session fields are recursively removed, including when embedded in JSON-encoded bodies. Retrieved or user-supplied content remains untrusted data and is never promoted to system authority by an adapter.

Raw provider evidence, when enabled by deployment policy, must be sanitized before persistence, access-controlled, and retained for less time than normalized audit records. Deployments are responsible for applying their data classification, residency, and deletion requirements. Public source distributions contain no raw provider requests or responses.

Audit records may include provider request identifiers, resolved model/version, finish metadata, usage, latency, cost reservation, policy version, attempt state, and normalized failure, subject to deployment policy.
