# Architecture checks

Run `powershell -ExecutionPolicy Bypass -NoProfile -File scripts/check_architecture.ps1` (or `pwsh` where available) and `uv run pytest`. Static and AST checks preserve subsystem direction and accepted ADRs. Phase 13 permits only the supervised entry point and registered local sandbox adapters; it forbids generic shell/code/HTTP capability, production agents, live Control Core, wildcard/self approval, autonomous goals/replanning, automatic learning, and ART-DEP-AI coupling.
