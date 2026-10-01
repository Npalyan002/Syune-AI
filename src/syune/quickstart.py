"""Fresh-install executable example for the Lean v1 quickstart."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile

from syune import (
    ContextRequest,
    ErrorCategory,
    ProvenanceMode,
    RecallRequest,
    ReviseRequest,
    Syune,
    SyuneError,
    TypedId,
)
from syune.product.config import load_config
from syune.product.state import initialize_state


def emit(name, value):
    print(json.dumps({name: value.data}, default=str, sort_keys=True))


def _state_root(value: str | None) -> Path:
    if value is None:
        return (Path(tempfile.gettempdir()) / "syune-quickstart").resolve()
    return Path(value).expanduser().resolve(strict=False)


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the SYUNE fresh-install quickstart")
    parser.add_argument(
        "--state-root",
        help="demo state directory (default: the system temporary directory)",
    )
    args = parser.parse_args(argv)
    root = _state_root(args.state_root)
    try:
        metadata, created = initialize_state(load_config(cli_state_root=root))
        print(json.dumps({
            "initialized": True,
            "created": created,
            "state_root": str(root),
            "instance_id": str(metadata.instance_id),
        }, sort_keys=True))
        with Syune.open(state_root=root) as syune:
            remembered = syune.remember("The release channel is amber.")
            emit("remember", remembered)
            old_id = remembered.data["memory_id"]
            emit("context", syune.context(ContextRequest(
                "release channel", provenance_mode=ProvenanceMode.FULL,
            )))
            before = datetime.now(timezone.utc).isoformat()
            revised = syune.revise(ReviseRequest(
                TypedId.parse(old_id), "The release channel is green.",
            ))
            emit("revise", revised)
            emit("current", syune.recall(RecallRequest("release channel", query_mode="CURRENT")))
            emit("historical", syune.recall(RecallRequest(
                "release channel", query_mode="AS_OF", valid_at=before, knowledge_at=before,
            )))
            emit("history", syune.history(revised.data["memory_id"]))
            emit("archive", syune.archive(old_id))
            emit("audit", syune.audit())
        with Syune.open(state_root=root) as syune:
            emit("restart", syune.recall("release channel"))
        print(json.dumps({"closed": True}, sort_keys=True))
        return 0
    except SyuneError as exc:
        if exc.category is ErrorCategory.INTERNAL:
            raise
        print(f"error: {exc.message}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
