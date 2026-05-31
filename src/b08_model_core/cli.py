from __future__ import annotations

import argparse
from pathlib import Path

from b08_model_core.evaluation.benchmark import run_benchmark
from b08_model_core.simulation.export_dataset import simulate_dataset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="b08-model-core")
    sub = parser.add_subparsers(dest="command", required=True)

    simulate = sub.add_parser("simulate")
    simulate.add_argument("--days", type=int, default=45)
    simulate.add_argument("--seed", type=int, default=42)
    simulate.add_argument("--output", required=True)

    benchmark = sub.add_parser("benchmark")
    benchmark.add_argument("--dataset", required=True)
    benchmark.add_argument("--output", required=True)

    args = parser.parse_args(argv)
    if args.command == "simulate":
        simulate_dataset(days=args.days, seed=args.seed, output=args.output)
        return 0
    if args.command == "benchmark":
        run_benchmark(args.dataset, args.output)
        return 0
    raise ValueError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
