"""Revise a record and compare current, point-in-time, and lineage results."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from pathlib import Path

from syune import RecallRequest, ReviseRequest, Syune, TypedId


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", type=Path, required=True)
    args = parser.parse_args()

    with Syune.open(state_root=args.state_root) as memory:
        first = memory.remember("The release channel is amber.")
        before_revision = datetime.now(timezone.utc).isoformat()
        second = memory.revise(ReviseRequest(
            TypedId.parse(first.data["memory_id"]),
            "The release channel is green.",
        ))

        current = memory.recall(RecallRequest("release channel", query_mode="CURRENT"))
        historical = memory.recall(RecallRequest(
            "release channel",
            query_mode="AS_OF",
            valid_at=before_revision,
            knowledge_at=before_revision,
        ))
        lineage = memory.history(second.data["memory_id"])

        print("current:", current.data["candidates"])
        print("as of:", historical.data["candidates"])
        print("revision_of:", lineage.data["truth"]["revision_of"])


if __name__ == "__main__":
    main()
