# Phase 20 validation

`PHASE_20_STATUS = PASS`

Adversarial tests cover same-scope access, different users/agents/projects/organizations/departments, explicit allow and deny, allow-deny conflicts, purpose mismatch, missing principal, restricted and public sensitivity, legacy strict/compatible behavior, principal-switch cache isolation, persistence/restart, audit decisions, and unauthorized learning evidence.

SDK, MCP, public request contracts, direct memory access, retrieval, cognition, Council-derived context, and learning use the same authorization types. The Phase 18 harness remains operational and now reports a passing permission gate. The remaining meaningful leakage risk is coarse timing/count inference; constant-time retrieval is out of scope.
