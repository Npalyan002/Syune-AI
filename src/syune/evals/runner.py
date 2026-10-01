"""Runs caller-supplied local checks; exceptions and missing evidence fail closed."""
from datetime import datetime, timezone
import platform
from time import perf_counter
from .model import EvalFailure, EvalObservation, EvalRun


def run_suite(suite, checks, trace_id):
    if not trace_id:
        raise ValueError("explicit correlation required")
    started = datetime.now(timezone.utc).isoformat()
    observations, failures = [], []
    for case in suite.cases:
        tick = perf_counter()
        try:
            metrics, evidence = checks[case.id]()
            values = {m.name: m.value for m in metrics}
            if len(values) != len(metrics) or not evidence:
                raise ValueError("duplicate metric or missing evidence")
            for expected in case.expectations:
                value = values.get(expected.metric)
                if value is None or not expected.minimum <= value <= expected.maximum:
                    failures.append(EvalFailure(case.id, expected.invariant, "metric missing or outside declared bounds"))
            observations.append(EvalObservation(case.id, tuple(metrics), tuple(evidence), (perf_counter()-tick)*1000))
        except Exception as exc:
            # Exception messages can contain source content or secrets.
            failures.append(EvalFailure(case.id, "check completes with evidence", type(exc).__name__))
    return EvalRun(suite.name, suite.version, trace_id, started,
                   (("python", platform.python_version()), ("platform", platform.platform())),
                   tuple(observations), tuple(failures))
