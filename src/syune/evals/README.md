# System evaluation layer

Typed local eval contracts, finite metrics, explicit expectations, evidence references,
read-only invariant auditing and coarse versioned regression comparison. Runtime health
and release readiness are distinct from cognitive readiness and truth.

Run `uv run python scripts/run_phase14_evals.py full` from the repository root.
Modes: quick, full, security, resilience, e2e, performance, soak. Performance and soak
are separate from the default pytest run. The script uses the existing runtime services
through deterministic test fixtures; it introduces no execution authority or automatic learning.
