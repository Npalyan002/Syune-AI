# Tests

`unit` covers typed contracts and pure rules; `integration` exercises actual services and durable stores; `architecture` enforces dependency/authority boundaries. `phase14` adds E2E, corruption, recovery, curated quality, concurrency, resource and regression checks. Fixtures are deterministic and local; multimodal adapters are fakes. Approval is supplied by an explicit test host.

Run `uv run --locked pytest` for all 203 tests. Long performance and soak runs are separate scripts, documented in [scripts](../scripts/README.md). Critical failure injection is test-only. The full eval CLI combines test evidence with completed performance artifacts and fails closed if required evidence is absent.
