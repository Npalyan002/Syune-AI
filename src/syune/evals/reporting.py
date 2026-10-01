"""Safe structured reports; no source bodies, approval tokens or exception text."""
from dataclasses import asdict
import json
from .model import Health, Readiness, EvalReport


def report(run, *, required_cases, limitations=()):
    observed = {o.case_id for o in run.observations}
    blocked = bool(run.failures) or not set(required_cases) <= observed
    return EvalReport(run, Health.UNHEALTHY if run.failures else Health.HEALTHY,
                      Readiness.BLOCKED if blocked else Readiness.READY_WITH_LIMITATIONS if limitations else Readiness.READY,
                      tuple(limitations))


def to_json(value):
    return json.dumps(asdict(value), indent=2, sort_keys=True, allow_nan=False)
