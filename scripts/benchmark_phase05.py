"""In-process MCP protocol overhead against synthetic local Study state."""
import asyncio
import json
import platform
import tempfile
from pathlib import Path
from statistics import median
from time import perf_counter

from mcp import Client

from syune.gateway.mcp import GatewayConfig, open_gateway


async def run(repeats: int = 20) -> dict:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "library"
        root.mkdir()
        source = root / "sample.md"
        source.write_text("# Orchard\n\nPlanning note for local benchmark.\n", encoding="utf-8")
        with open_gateway(GatewayConfig(Path(directory) / "state", (root,))) as (server, _):
            async with Client(server) as client:
                await client.call_tool("syune_study_source", {"path": str(source)})
                samples = []
                service = []
                for _ in range(repeats):
                    start = perf_counter()
                    result = await client.call_tool("syune_recall", {"text": "planning"})
                    samples.append((perf_counter() - start) * 1000)
                    service.append(result.structured_content["service_ms"])
                return {"transport": "in-process MCP", "repeats": repeats,
                        "python": platform.python_version(), "platform": platform.platform(),
                        "tool_total_p50_ms": round(median(samples), 3),
                        "retrieval_service_p50_ms": round(median(service), 3),
                        "gateway_protocol_overhead_p50_ms": round(median([total - inner for total, inner in zip(samples, service)]), 3)}


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run()), indent=2))
