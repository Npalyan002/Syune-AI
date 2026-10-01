# SYUNE documentation

The public v1 contract is the Lean runtime: governed memory, bounded context, reliable
model execution, and durable audit. Historical phase material is retained for
reproducibility but is not the recommended learning path.

## Getting started

- [Installation](installation.md)
- [Quickstart](QUICKSTART.md)
- [Examples](../examples/README.md)
- [Configuration](CONFIGURATION.md)
- [Local operations](LOCAL_OPERATIONS.md)

## Concepts

- [Lean v1 product boundary](product_refactor/V1_PRODUCT_BOUNDARY.md)
- [Compatibility matrix](COMPATIBILITY_MATRIX.md)
- [Known limitations](known_limitations.md)

## Guides

- [Backup and restore](backup_restore.md)
- [Migration](migration.md)
- [Host integration protocol](HOST_INTEGRATION_PROTOCOL_V1.md)

## API

- [Public API v1](PUBLIC_API_V1.md)
- [Python SDK](PYTHON_SDK.md)
- [MCP v1](MCP_V1.md)

## Security

- [Security policy](../SECURITY.md)
- [Threat model](threat_model.md)
- [Security preservation](product_refactor/SECURITY_PRESERVATION.md)

## Architecture

- [Lean v1 architecture](architecture/LEAN_V1_ARCHITECTURE.md)
- [Lean v1 API](product_refactor/LEAN_V1_API.md)
- [ModelGateway contract](phase29/MODEL_GATEWAY_CONTRACT.md)

## Benchmarks

- [Lean v1 validation](benchmarks/LEAN_V1_VALIDATION.md)
- [Historical evaluation summary](benchmarks/HISTORICAL_EVALUATION_SUMMARY.md)

## Research and experimental material

- [Research context](research/README.md)
- [Experimental modules](product_refactor/EXPERIMENTAL_MODULES.md)

Research cognition, learning, Council, Planner, and Executive surfaces are disabled by
default and are outside the stable v1 product contract.

## Release

- [v1.0.0 release notes](release/v1.0.0.md)
- [Release-candidate validation](release/RC_VALIDATION.md)
- [Source-tree audit](release/SOURCE_TREE_AUDIT.md)

## Historical development documents

Documents named `PHASE_*` and the numbered `phase*/` directories record development and
validation history. They remain available for reproducibility and compatibility review,
but they are not primary product documentation and may describe superseded states.
