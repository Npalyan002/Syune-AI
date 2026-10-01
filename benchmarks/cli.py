from __future__ import annotations

import argparse
import json
from pathlib import Path

from .datasets import build_dataset
from .model import Baseline
from .reporting import compare, evaluate_policy, load_result, markdown_report
from .runner import BenchmarkRunner, write_raw_result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="syune-benchmark")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--tier", choices=("smoke", "standard", "heavy", "stress"), default="smoke")
    run.add_argument("--baseline", choices=[item.value for item in Baseline], action="append")
    run.add_argument("--family")
    run.add_argument("--seed", type=int, default=1801)
    run.add_argument("--repeats", type=int, default=1)
    run.add_argument("--scale", type=int)
    run.add_argument("--interactions", type=int)
    run.add_argument("--output", type=Path, default=Path("docs/evals/phase18/raw"))
    comp = commands.add_parser("compare")
    comp.add_argument("baseline", type=Path); comp.add_argument("candidate", type=Path)
    comp.add_argument("--policy", type=Path, default=Path("benchmarks/config/regression_policy.v1.json"))
    report = commands.add_parser("report")
    report.add_argument("result", type=Path); report.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    if args.command == "run":
        dataset = build_dataset(args.tier, args.seed, args.scale, args.interactions)
        baselines = [Baseline(value) for value in (args.baseline or [Baseline.BASIC_RAG.value, Baseline.CURRENT_SYUNE.value])]
        for baseline in baselines:
            result = BenchmarkRunner(root).run(baseline, dataset, args.family, args.repeats)
            path = write_raw_result(result, root / args.output)
            print(path)
        return 0
    if args.command == "compare":
        comparison = compare(load_result(args.baseline), load_result(args.candidate))
        policy = json.loads((root / args.policy).read_text(encoding="utf-8"))
        print(json.dumps({"comparison": comparison, "regression_gate": evaluate_policy(comparison, policy)}, indent=2))
        return 0
    result = load_result(args.result)
    text = markdown_report(result)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else: print(text)
    return 0


if __name__ == "__main__": raise SystemExit(main())
