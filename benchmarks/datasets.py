from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict
from datetime import datetime, timezone

from .model import Case, Dataset, Edge, Record

GENERATOR_VERSION = "1.0.0"
CREATED_AT = "2026-09-25T00:00:00Z"


def _r(identifier: str, text: str, **kwargs: object) -> Record:
    return Record(identifier, text, f"source-{identifier}", f"synthetic://phase18/{identifier}", **kwargs)


def _canonical_cases() -> list[Case]:
    return [
        Case("recall-01", "recall", "quartz launch code", (_r("r1", "The quartz launch code is amber seven."), _r("r2", "The granite lunch menu is soup.")), ("r1",), measures=("G04", "G20")),
        Case("temporal-01", "temporal", "current Atlas region", (_r("t-old", "The current Atlas region is west.", valid_to="2025-12-31"), _r("t-new", "The current Atlas region is east.", valid_from="2026-01-01"), _r("t-future", "The current Atlas region is north.", valid_from="2028-01-01")), ("t-new",), forbidden_ids=("t-old", "t-future"), measures=("G02",)),
        Case("contradiction-01", "contradiction", "Falcon supports mode", (_r("c1", "Falcon supports silent mode."), _r("c2", "Falcon does not support silent mode.")), ("c2",), forbidden_ids=("c1",), measures=("G03", "G31"), tags=("contradiction",)),
        Case("provenance-01", "provenance", "Lumen owner", (_r("p1", "Lumen owner is Casey."),), ("p1",), measures=("G13",)),
        Case("associative-01", "associative", "project with cobalt badge", (_r("a1", "Project Kestrel has the cobalt badge."), _r("a2", "Kestrel deployment key is cedar."), _r("a3", "Project Sable has a silver badge.")), ("a2",), edges=(Edge("a1", "a2", "related"),), measures=("G04", "G31")),
        Case("multihop-01", "multi_hop", "who handles the aurora escalation", (_r("m1", "Aurora escalation begins at the north desk."), _r("m2", "The north desk routes to team Juniper."), _r("m3", "Team Juniper lead is Morgan."), _r("m4", "Team Cedar lead is Robin.")), ("m3",), edges=(Edge("m1", "m2", "routes"), Edge("m2", "m3", "owned_by")), measures=("G04", "G31")),
        Case("update-01", "update", "current Nimbus quota", (_r("u1", "The current Nimbus quota is 20."), _r("u2", "The current Nimbus quota is 40.")), ("u2",), forbidden_ids=("u1",), measures=("G02", "G12"), tags=("stale", "duplicate")),
        Case("abstention-01", "abstention", "Vega submarine password", (_r("z1", "Vega bicycle color is green."),), (), measures=("G20",), tags=("missing_evidence",)),
        Case("permission-01", "permission", "Opal payroll amount", (_r("sec1", "Opal payroll amount is 900.", principal="beta"), _r("sec2", "Opal public office is tower two.", principal="alpha")), (), forbidden_ids=("sec1",), measures=("G01",), tags=("permission_conflict",)),
        Case("cross-agent-01", "cross_agent", "private Helix note", (_r("x1", "Private Helix note says delta.", agent="agent-b"), _r("x2", "Public Helix note says gamma.", agent="agent-a")), ("x2",), forbidden_ids=("x1",), measures=("G10",), tags=("cross_agent_contamination",)),
        Case("learning-01", "learning", "verified procedure for Ion", (_r("l1", "Verified procedure for Ion is restart once.", verified=True), _r("l2", "Unverified procedure for Ion is erase all.", verified=False)), ("l1",), forbidden_ids=("l2",), measures=("G09", "G28"), tags=("unverified_feedback", "false_observation")),
        Case("compression-01", "compression", "Rook weekly pattern", tuple(_r(f"k{i}", f"Rook status week {i} is stable.") for i in range(1, 6)), ("k5",), measures=("G11",), tags=("distractor_chain",)),
        Case("task-01", "task_success", "exact owner of Mercury migration", (_r("q1", "Mercury migration owner is Avery."), _r("q2", "Mercury analytics owner is Blake."), _r("q3", "Mercury migration observer is Drew.")), ("q1",), measures=("G14", "G20"), tags=("similar_entities", "ambiguous_names")),
        Case("context-01", "context_efficiency", "Citrine retention days", (_r("e1", "Citrine retention is 30 days."), *tuple(_r(f"e{i}", f"Citrine unrelated policy item {i}.") for i in range(2, 10))), ("e1",), top_k=3, measures=("G04", "G20"), tags=("high_similarity_distractors", "near_duplicate")),
        Case("performance-01", "performance", "Sierra checkpoint", (_r("f1", "Sierra checkpoint is complete."), *tuple(_r(f"f{i}", f"Synthetic distractor {i} for scale.") for i in range(2, 25))), ("f1",), measures=("G05", "G17", "G21"), tags=("orphan_provenance",)),
    ]


def build_dataset(tier: str = "smoke", seed: int = 1801, scale: int | None = None, interactions: int | None = None) -> Dataset:
    if tier not in {"smoke", "standard", "heavy", "stress"}:
        raise ValueError("tier must be smoke, standard, heavy, or stress")
    allowed_scales = {10_000, 100_000, 1_000_000, 10_000_000, 100_000_000}
    allowed_interactions = {10, 100, 1_000, 10_000}
    if scale is not None and scale not in allowed_scales:
        raise ValueError("unsupported scale point")
    if interactions is not None and interactions not in allowed_interactions:
        raise ValueError("unsupported longitudinal point")
    cases = _canonical_cases()
    random.Random(seed).shuffle(cases)
    payload = json.dumps([asdict(case) for case in cases], sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    suffix = f"-s{scale}" if scale else f"-i{interactions}" if interactions else ""
    return Dataset("syune-competitive-baseline" + suffix, "1.0.0", seed, GENERATOR_VERSION, CREATED_AT, digest, tier, len(cases), tuple(cases))
