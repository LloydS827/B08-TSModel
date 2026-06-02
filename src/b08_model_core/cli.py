from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from b08_model_core.evaluation.benchmark import run_benchmark
from b08_model_core.experiments.forecasting import run_forecasting_experiment_with_status
from b08_model_core.foundation import FoundationModelStatus
from b08_model_core.real_data.diagnostics import build_fu13_diagnostics, render_fu13_diagnostics
from b08_model_core.real_data.forecasting import (
    render_real_data_forecasting_report,
    run_real_data_forecasting,
)
from b08_model_core.real_data.fu13_config import load_fu13_real_data_config
from b08_model_core.real_data.fu13_loader import assemble_fu13_observations
from b08_model_core.real_data.validation_report import validate_real_data_file
from b08_model_core.simulation.export_dataset import simulate_dataset
from b08_model_core.tasks.schema import validate_observation_frame


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
    assemble_fu13 = real_data_sub.add_parser("assemble-fu13")
    assemble_fu13.add_argument("--input-dir", required=True)
    assemble_fu13.add_argument("--config", required=True)
    assemble_fu13.add_argument("--output", required=True)
    assemble_fu13.add_argument("--report", required=True)
    diagnose_fu13 = real_data_sub.add_parser("diagnose-fu13")
    diagnose_fu13.add_argument("--dataset", required=True)
    diagnose_fu13.add_argument("--config", required=True)
    diagnose_fu13.add_argument("--output", required=True)
    forecast_fu13 = real_data_sub.add_parser("forecast-fu13")
    forecast_fu13.add_argument("--dataset", required=True)
    forecast_fu13.add_argument("--config", required=True)
    forecast_fu13.add_argument("--output", required=True)
    forecast_fu13.add_argument("--model", choices=["baseline", "ttm"], required=True)
    forecast_fu13.add_argument("--window-mode", choices=["stage-local", "cross-stage"], default="cross-stage")
    forecast_fu13.add_argument("--context-length", type=_positive_int, default=90)
    forecast_fu13.add_argument("--prediction-length", type=_positive_int, default=16)
    forecast_fu13.add_argument("--max-windows", type=_positive_int, default=40)
    forecast_fu13.add_argument("--model-cache-dir")
    forecast_download = forecast_fu13.add_mutually_exclusive_group()
    forecast_download.add_argument("--allow-download", action="store_true", dest="allow_download")
    forecast_download.add_argument("--no-download", action="store_false", dest="allow_download")
    forecast_fu13.set_defaults(allow_download=False)

    experiment = sub.add_parser("experiment")
    experiment_sub = experiment.add_subparsers(dest="experiment_command", required=True)
    forecasting = experiment_sub.add_parser("forecasting")
    forecasting.add_argument("--dataset", required=True)
    forecasting.add_argument("--output", required=True)
    forecasting.add_argument("--max-windows", type=_positive_int, default=120)
    forecasting.add_argument("--model", choices=["baseline", "ttm"], default="baseline")
    forecasting.add_argument("--context-length", type=_positive_int, default=128)
    forecasting.add_argument("--prediction-length", type=_positive_int, default=32)
    forecasting.add_argument("--model-cache-dir")
    download = forecasting.add_mutually_exclusive_group()
    download.add_argument("--allow-download", action="store_true", dest="allow_download")
    download.add_argument("--no-download", action="store_false", dest="allow_download")
    forecasting.set_defaults(allow_download=False)

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
    if args.command == "real-data" and args.real_data_command == "assemble-fu13":
        observations, cycle_summary = assemble_fu13_observations(args.input_dir, args.config)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        observations.to_parquet(output, index=False)
        validation = validate_observation_frame(observations)
        report = [
            "# Real FU13 Data Validation",
            "",
            f"- schema_valid: {validation.valid}",
            f"- rows: {len(observations)}",
            f"- sensors: {observations['sensor_id'].nunique()}",
            f"- stages: {observations['stage'].nunique()}",
            f"- cycle_summary: {cycle_summary}",
            f"- quality_counts: {dict(observations['quality_flag'].value_counts())}",
        ]
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
        return 0 if validation.valid else 1
    if args.command == "real-data" and args.real_data_command == "diagnose-fu13":
        cfg = load_fu13_real_data_config(args.config)
        df = pd.read_parquet(args.dataset)
        report = build_fu13_diagnostics(df, cfg)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_fu13_diagnostics(report), encoding="utf-8")
        return 0
    if args.command == "real-data" and args.real_data_command == "forecast-fu13":
        cfg = load_fu13_real_data_config(args.config)
        sensor_scenario = {sensor.sensor_id: sensor.scenario for sensor in cfg.sensors}
        result = run_real_data_forecasting(
            args.dataset,
            model=args.model,
            window_mode=args.window_mode,
            context_length=args.context_length,
            prediction_length=args.prediction_length,
            max_windows=args.max_windows,
            allow_download=args.allow_download,
            model_cache_dir=args.model_cache_dir,
            sensor_scenario=sensor_scenario,
        )
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_real_data_forecasting_report(result), encoding="utf-8")
        if args.model == "ttm" and result.foundation_result.status != FoundationModelStatus.AVAILABLE_AND_RAN:
            return 1
        return 0
    if args.command == "experiment" and args.experiment_command == "forecasting":
        _, status = run_forecasting_experiment_with_status(
            args.dataset,
            args.output,
            context_length=args.context_length,
            prediction_length=args.prediction_length,
            max_windows=args.max_windows,
            model=args.model,
            model_cache_dir=args.model_cache_dir,
            allow_download=args.allow_download,
        )
        if args.model != "baseline" and status != FoundationModelStatus.AVAILABLE_AND_RAN:
            return 1
        return 0
    raise ValueError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
