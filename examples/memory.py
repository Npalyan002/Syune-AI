"""Remember, retrieve with provenance, close, and retrieve after restart."""
from __future__ import annotations
import argparse
from pathlib import Path

from syune import ContextRequest, ProvenanceMode, Syune


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", type=Path, required=True)
    args = parser.parse_args()

    with Syune.open(state_root=args.state_root) as memory:
        stored = memory.remember("The deployment window is Friday at 18:00 UTC.")
        context = memory.context(ContextRequest(
            "deployment window", provenance_mode=ProvenanceMode.FULL
        ))
        print("stored:", stored.data["memory_id"])
        print("context:", context.data["rendered"])
        print("provenance:", context.data["items"][0]["provenance"])

    with Syune.open(state_root=args.state_root) as restarted:
        print("after restart:", restarted.context("deployment window").data["rendered"])


if __name__ == "__main__":
    main()
