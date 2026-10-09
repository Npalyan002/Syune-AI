"""Operator-invoked cleanup for exactly one marked evaluation root."""
from __future__ import annotations

import argparse
from pathlib import Path

from syune.adapters.aml.v1 import cleanup_evaluation_state


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--confirm-root", required=True)
    args = parser.parse_args()
    cleanup_evaluation_state(args.root, confirm_root=args.confirm_root)


if __name__ == "__main__":
    main()
