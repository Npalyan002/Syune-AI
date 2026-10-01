# Phase 29 architecture

`ModelGateway.execute(ModelExecutionRequest)` is the only production text-generation boundary.
It resolves an authorized capable route, reserves budget, executes a bounded provider attempt,
persists sanitized raw evidence, classifies finish state, parses and validates, then creates one
semantic commit. Cognitive mutation remains a caller-owned transaction after commit.

OpenAI and OpenAI-compatible Responses transports are implemented. Anthropic and Gemini use the
same adapter contract but remain contract-only. The gateway contains no benchmark-name branches.
