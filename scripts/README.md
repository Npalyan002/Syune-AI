# Development scripts

Run from the repository root with the locked environment. Phase 14 commands are local and use synthetic fixtures:

```powershell
uv run --locked pytest
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check_architecture.ps1
uv run --locked python scripts/run_phase14_evals.py quick
uv run --locked python scripts/run_phase14_evals.py security
uv run --locked python scripts/run_phase14_evals.py resilience
uv run --locked python scripts/run_phase14_evals.py e2e
uv run --locked python scripts/run_phase14_evals.py performance
uv run --locked python scripts/run_phase14_evals.py soak
uv run --locked python scripts/benchmark_phase14_subsystems.py
uv run --locked python scripts/benchmark_phase14_cold.py
uv run --locked python scripts/capture_phase14_proof.py
uv run --locked python scripts/run_phase14_evals.py full
git diff --check
```

`full` runs the whole test suite and requires completed scale and soak JSON artifacts from the preceding commands. `pytest` alone does not run the long benchmarks. Performance and soak are separate local/CI jobs; the soak defaults to 600 seconds. Reports are generated under `.syune/`; the proof capture explicitly refreshes its versioned synthetic evidence file under `docs/evals/`. Scripts use explicit fixed Python child processes for test orchestration, never expose a shell capability to the runtime. Do not invoke the historical legacy shadow probe for Phase 14.

Phase 15 packaging validation:

```powershell
uv build --out-dir .syune/phase15-dist
python scripts/audit_phase15_artifacts.py --dist .syune/phase15-dist --output .syune/phase15-artifact-audit.json
python scripts/validate_phase15_installed.py --syune <clean-venv>/Scripts/syune.exe --output .syune/phase15-installed.json
```

The installed validation must run with the wheel installed in a clean environment and from outside the repository. It uses the official MCP client, temporary state and synthetic local content. These scripts do not alter product state or contact a remote service.
