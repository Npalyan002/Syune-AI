# Benchmark reproducibility

Run commands from the repository root with `src` and the root importable.

```powershell
python scripts/run_benchmarks.py run --tier smoke
python scripts/run_benchmarks.py run --tier standard
python scripts/run_benchmarks.py run --tier smoke --family temporal
python scripts/run_benchmarks.py run --tier smoke --baseline B3_CURRENT_SYUNE
python scripts/run_benchmarks.py compare <baseline.json> <candidate.json>
python scripts/run_benchmarks.py report <result.json> --output report.md
```

Repeated model-backed runs use `--repeats N`; all samples are retained. Longitudinal and scale workload identities use `--interactions 100` and `--scale 100000`. Provider adapters must record provider, model, exact version when available, temperature, top-p, seed, maximum tokens, and system-prompt version. If a provider cannot expose an exact version, the limitation must remain in `model_parameters`.

The current environment uses the bundled Python runtime because the repository `.venv` launcher is broken, matching Phase 17 G30. See `PHASE_18_VALIDATION.md` for the exact validation command.
