from __future__ import annotations

import argparse
from pathlib import Path

from b08_model_core.evaluation.benchmark import run_benchmark
from b08_model_core.experiments.forecasting import run_forecasting_experiment
from b08_model_core.real_data.validation_report import validate_real_data_file
from b08_model_core.simulation.export_dataset import simulate_dataset


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="b08-model-core")
    sub = parser.add_subparsers(dest="command", required=True)

    simulate = sub.add_parser("simulate")
    simulate.add_argument("--days", type=int, default=45)
    simulate.add_argument("--seed", type=int, default=42)
    simulate.add_argument("--output", required=True)
    simulate.add_argument("--config", default="configs/furnace_fu13_sim.yaml")

    benchmark = sub.add_parser("benchmark")
    benchmark.add_argument("--dataset", required=True)
    benchmark.add_argument("--output", required=True)

    real_data = sub.add_parser("real-data")
    real_data_sub = real_data.add_subparsers(dest="real_data_command", required=True)
    validate = real_data_sub.add_parser("validate")
    validate.add_argument("--input", required=True)
    validate.add_argument("--schema-map", required=True)
    validate.add_argument("--output", required=True)

    experiment = sub.add_parser("experiment")
    experiment_sub = experiment.add_subparsers(dest="experiment_command", required=True)
    forecasting = experiment_sub.add_parser("forecasting")
    forecasting.add_argument("--dataset", required=True)
    forecasting.add_argument("--output", required=True)
    forecasting.add_argument("--max-windows", type=_positive_int, default=120)

    args = parser.parse_args(argv)
    if args.command == "simulate":
        simulate_dataset(days=args.days, seed=args.seed, output=args.output, config_path=args.config)
        return 0
    if args.command == "benchmark":
        run_benchmark(args.dataset, args.output)
        return 0
    if args.command == "real-data" and args.real_data_command == "validate":
        report = validate_real_data_file(args.input, args.schema_map, args.output)
        return 0 if report.schema_valid else 1
    if args.command == "experiment" and args.experiment_command == "forecasting":
        run_forecasting_experiment(args.dataset, args.output, max_windows=args.max_windows)
        return 0
    raise ValueError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
