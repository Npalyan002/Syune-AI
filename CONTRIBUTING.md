# Contributing to SYUNE

Thanks for helping improve SYUNE.

## Development setup

Use Python 3.12 or newer (below 4), create a virtual environment, and install the project
plus the pytest development dependency declared in `pyproject.toml`.

```console
python -m venv .venv
python -m pip install -e . pytest build
python -m pytest
```

## Stable v1 expectations

Public API v1, storage schemas, SDK behavior, Lean MCP contracts, authorization,
temporal/version semantics, lifecycle behavior, and ModelGateway semantics are release
contracts. Changes to them require explicit compatibility analysis, tests, documentation,
and a release decision. Do not silently broaden authority or model execution.

Research cognition, learning, Council, Planner, and Executive modules are experimental and
disabled by default. Keep experimental changes isolated from the Lean runtime and label
their status clearly.

## Contribution workflow

1. Open an issue for substantial behavior or contract changes.
2. Create a focused branch and keep unrelated changes out of the patch.
3. Add or update tests without weakening existing gates.
4. Run the full test suite and package build.
5. Update current public documentation when behavior changes.
6. Submit a pull request explaining compatibility, security, and validation impact.

Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md); do not open a
public issue containing sensitive details.
