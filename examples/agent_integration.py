"""Generic agent task → governed context → chosen model integration."""
from __future__ import annotations
import argparse
from pathlib import Path

from syune import ContextRequest, RememberRequest, Syune


def chosen_model(task: str, context: str) -> str:
    """Replace this deterministic stand-in with your model or ModelGateway call."""
    return f"Task: {task}\nGoverned context supplied: {bool(context.strip())}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--task", default="Prepare the release briefing")
    args = parser.parse_args()

    with Syune.open(state_root=args.state_root) as memory:
        memory.remember(RememberRequest(
            "The release briefing must cite the approved change record.",
            owner="agent:briefing-agent",
        ))
        context = memory.context(ContextRequest(
            args.task,
            agent_id="briefing-agent",
            purpose="release-briefing",
            task_id="briefing-001",
            max_chars=2_000,
        ))
        response = chosen_model(args.task, context.data["rendered"])
        print(response)
        print("audit correlation:", context.correlation_id)


if __name__ == "__main__":
    main()
