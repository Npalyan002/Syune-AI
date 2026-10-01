"""Assemble bounded context for an authorized agent and show a denied request."""
from __future__ import annotations
import argparse
from pathlib import Path

from syune import ContextRequest, ProvenanceMode, RememberRequest, Syune, SyuneError


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", type=Path, required=True)
    args = parser.parse_args()

    with Syune.open(state_root=args.state_root) as memory:
        memory.remember(RememberRequest(
            "Release project alpha is approved for Friday.",
            owner="agent:release-bot",
        ))

        allowed = memory.context(ContextRequest(
            "project alpha",
            agent_id="release-bot",
            purpose="release-planning",
            task_id="prepare-release",
            max_chars=1_000,
            provenance_mode=ProvenanceMode.FULL,
        ))
        print("authorized context:", allowed.data["rendered"])

        try:
            memory.context(ContextRequest("project alpha", purpose="unscoped-request"))
        except SyuneError as error:
            print("denied:", error.code)


if __name__ == "__main__":
    main()
