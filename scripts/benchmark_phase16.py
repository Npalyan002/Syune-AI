"""Local Phase 16 facade and MCP transport overhead sample."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
from time import perf_counter

from mcp import Client

from syune import CognitiveRequest, PlanRequest, RecallRequest, RuntimeMode, StudyRequest, Syune
from syune.cognition import CognitiveRequest as InternalCognitiveRequest
from syune.core import CognitiveRequestId, ExecutiveRequestId, GoalId
from syune.executive import ExecutiveRequest, Goal, GoalSource
from syune.gateway.mcp import GatewayConfig, open_gateway
from syune.product.config import StudyConfig, SyuneConfig, StateConfig
from syune.product.runtime import SyuneRuntime
from syune.product.state import initialize_state
from syune.retrieval import RecallCue, RecallRequest as InternalRecallRequest


def sample(operation, count=20):
    values=[]
    for _ in range(count):
        start=perf_counter(); operation(); values.append((perf_counter()-start)*1000)
    return round(median(values), 4)


async def mcp_samples(root: Path, library: Path):
    values={name: [] for name in ("health", "recall", "cognition", "plan")}
    with open_gateway(GatewayConfig(root, (library,))) as (server, services):
        services.study.study(library / "fixture.txt"); services.index.sync()
        async with Client(server) as client:
            calls={
                "health": ("syune_health", {}), "recall": ("syune_recall", {"text":"bounded evidence"}),
                "cognition": ("syune_cognize", {"text":"bounded evidence"}),
                "plan": ("syune_plan", {"goal":"review bounded evidence"}),
            }
            for name,(tool,args) in calls.items():
                for _ in range(10):
                    start=perf_counter(); await client.call_tool(tool,args); values[name].append((perf_counter()-start)*1000)
    return {name: round(median(items),4) for name,items in values.items()}


def main():
    with TemporaryDirectory() as temporary:
        base=Path(temporary); library=base/"library"; library.mkdir()
        (library/"fixture.txt").write_text("bounded evidence requires provenance and review",encoding="utf-8")
        config=SyuneConfig(StateConfig(base/"product"),StudyConfig((library,)))
        initialize_state(config)
        (base/"product"/"config.toml").write_text(f'[study]\nroots = ["{library.as_posix()}"]\n',encoding="utf-8")
        with Syune.open(state_root=base/"product",mode=RuntimeMode.TEST) as brain:
            brain.study(StudyRequest(str(library/"fixture.txt")))
            sdk={"health":sample(brain.health),"recall":sample(lambda:brain.recall(RecallRequest(cue="bounded evidence"))),
                 "cognition":sample(lambda:brain.cognize(CognitiveRequest(cue="bounded evidence"))),
                 "plan":sample(lambda:brain.plan(PlanRequest("review bounded evidence")))}
        with SyuneRuntime.open(config) as runtime:
            direct={"health":sample(runtime.health),
                    "recall":sample(lambda:runtime.retrieval.recall(InternalRecallRequest(RecallCue(text="bounded evidence")))),
                    "cognition":sample(lambda:runtime.cognition.process(InternalCognitiveRequest(CognitiveRequestId.new(),"bounded evidence"))),
                    "plan":sample(lambda:runtime.planner.plan(ExecutiveRequest(ExecutiveRequestId.new(),Goal(GoalId.new(),"review bounded evidence",source=GoalSource.TEST))))}
        mcp=asyncio.run(mcp_samples(base/"mcp",library))
        print(json.dumps({"unit":"median_ms","samples":{"sdk":20,"mcp":10},"direct":direct,"sdk":sdk,"mcp":mcp},sort_keys=True))


if __name__ == "__main__": main()
