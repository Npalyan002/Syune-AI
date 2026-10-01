# P0 classification

The production text-generation gateway and cognitive-transaction application boundary are P0 and
`GATEWAY_AUTHORITATIVE`. Named cognitive subsystems contain no model call, so their model migration
state is `REMOVED`—not `DIRECT` or `SHADOW`. Their deterministic mutation semantics remain unchanged.

Any future generative knowledge construction, verification, planning, decision, scoring, promotion,
demotion, or revocation must use `GatewayCognitiveTransactionService`; adding provider transport to
a P0 module is prohibited by architecture tests.
