# Research isolation

`syune.product.runtime` has no top-level imports from cognition, council, executive, or learning. Default instances hold `None` for those services. Explicit `[features] research_cognition=true` or a deprecated research SDK call loads them lazily.

Learning is off and retrieval uses `NullPlasticityView`. Cognitive transactions remain importable for experiments but are not reachable from memory, recall, context, health, startup, or model execution. Historical phase documents are retained as historical evidence and are not current product claims.
