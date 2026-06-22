from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class C33ConfigError(ValueError):
    """Raised when the C3.3 single-candidate evaluation config is invalid."""


@dataclass(frozen=True)
class C33SafetyPolicy:
    allow_network: bool
    allow_download: bool
    allow_model_cache: bool
    allow_local_execution: bool
    allow_training: bool
    allow_write_processed: bool


@dataclass(frozen=True)
class C33Prerequisites:
    c32_design_doc: Path
    c32_local_status: str


@dataclass(frozen=True)
class C33Candidate:
    model_id: str
    model_ref: str
    task_id: str
    dataset_view: str


@dataclass(frozen=True)
class C33MetricContract:
    forecasting_metrics: tuple[str, ...]
    adapter_status_fields: tuple[str, ...]
    leaderboard_allowed: bool


@dataclass(frozen=True)
class C33LocalFu13LikeConfig:
    days: int
    seed: int
    context_length: int
    prediction_length: int
    max_windows: int
    residual_top_k: int


@dataclass(frozen=True)
class C33LocalExecutionConfig:
    enabled: bool
    model_cache_dir: Path
    fu13_like: C33LocalFu13LikeConfig


@dataclass(frozen=True)
class C33Outputs:
    report: Path


@dataclass(frozen=True)
class C33Config:
    stage: str
    safety_policy: C33SafetyPolicy
    prerequisites: C33Prerequisites
    candidate: C33Candidate
    metric_contract: C33MetricContract
    local_execution: C33LocalExecutionConfig | None
    outputs: C33Outputs


@dataclass(frozen=True)
class C33RunResult:
    config_path: Path
    stage: str
    status: str
    go_no_go_decision: str
    safety_policy: C33SafetyPolicy
    prerequisites: C33Prerequisites
    candidate: C33Candidate
    metric_contract: C33MetricContract
    invalid_claims: tuple[str, ...]
    local_execution_blocked_reason: str = ""


_EXPECTED_STAGE = "C3_3_single_candidate_open_model_local_evaluation"
_EXPECTED_C32_LOCAL_STATUS = "local_execution_baseline_reference_ready"
_EXPECTED_CANDIDATE = {
    "model_id": "ttm",
    "task_id": "forecasting_residual",
    "dataset_view": "fu13_like_simulated_forecasting",
}
_CONTRACT_READY_STATUS = "contract_ready_single_candidate_local_execution_blocked"
_GO_DECISION = "Go for C3.3 explicit local TTM cache-first evaluation"
_INVALID_CLAIMS = (
    "no production RUL",
    "no production alarms",
    "no maintenance recommendations",
    "no candidate leaderboard",
    "no self-developed model superiority",
)
_SAFETY_FLAGS = (
    "allow_network",
    "allow_download",
    "allow_model_cache",
    "allow_local_execution",
    "allow_training",
    "allow_write_processed",
)


def load_c33_config(path: str | Path) -> C33Config:
    config_path = Path(path)
    raw = _load_yaml_mapping(config_path)
    stage = _required_string(raw, "stage")
    if stage != _EXPECTED_STAGE:
        raise C33ConfigError(f"stage must be {_EXPECTED_STAGE}")

    local_execution_enabled = _local_execution_enabled(raw)
    safety_policy = _load_safety_policy(
        raw,
        local_execution_enabled=local_execution_enabled,
    )
    prerequisites = _load_prerequisites(raw)
    candidate = _load_candidate(raw)
    metric_contract = _load_metric_contract(raw)
    local_execution = _load_local_execution(
        raw,
        safety_policy=safety_policy,
        config_root=_project_root_for_config(config_path),
    )
    outputs = _load_outputs(raw)

    return C33Config(
        stage=stage,
        safety_policy=safety_policy,
        prerequisites=prerequisites,
        candidate=candidate,
        metric_contract=metric_contract,
        local_execution=local_execution,
        outputs=outputs,
    )


def run_c33_single_candidate_open_model_local_evaluation(
    config: C33Config,
    config_path: str | Path,
    *,
    adapter_factory: Callable[[], object] | None = None,
) -> C33RunResult:
    if config.local_execution is None:
        return C33RunResult(
            config_path=Path(config_path),
            stage=config.stage,
            status=_CONTRACT_READY_STATUS,
            go_no_go_decision=_GO_DECISION,
            safety_policy=config.safety_policy,
            prerequisites=config.prerequisites,
            candidate=config.candidate,
            metric_contract=config.metric_contract,
            invalid_claims=_INVALID_CLAIMS,
            local_execution_blocked_reason=(
                "default C3.3 config disables local execution, model cache, "
                "network, and downloads"
            ),
        )

    return C33RunResult(
        config_path=Path(config_path),
        stage=config.stage,
        status=_CONTRACT_READY_STATUS,
        go_no_go_decision=_GO_DECISION,
        safety_policy=config.safety_policy,
        prerequisites=config.prerequisites,
        candidate=config.candidate,
        metric_contract=config.metric_contract,
        invalid_claims=_INVALID_CLAIMS,
        local_execution_blocked_reason=(
            "C3.3 local adapter execution is reserved for Task 2"
        ),
    )


def render_c33_report(result: C33RunResult) -> str:
    lines = [
        "# C3.3 Single-Candidate Open Model Local Evaluation Report",
        "",
        "## Summary",
        "",
        f"- Stage: {result.stage}",
        f"- Config: {result.config_path}",
        f"- Status: {result.status}",
        f"- Decision: {result.go_no_go_decision}",
        "- Default path validates the contract only; it does not instantiate adapters or inspect model cache.",
        "- Forecasting residual evidence is separated from RUL claims and model leaderboard claims.",
        "",
        "## Safety Policy",
        "",
    ]
    for flag in _SAFETY_FLAGS:
        lines.append(f"- {flag}: {getattr(result.safety_policy, flag)}")
    lines.extend(
        [
            "",
            "## C3.2 Anchor",
            "",
            f"- Design doc: {result.prerequisites.c32_design_doc}",
            f"- Required local status: {result.prerequisites.c32_local_status}",
            "- C3.2 remains the baseline reference anchor; C3.3 only adds a single TTM forecasting adapter contract.",
            "",
            "## Candidate Contract",
            "",
            f"- Candidate: {result.candidate.model_id}",
            f"- Model ref: {result.candidate.model_ref}",
            f"- Task: {result.candidate.task_id}",
            f"- Dataset view: {result.candidate.dataset_view}",
            "- Default adapter execution: disabled",
            "",
            "## Metric Contract",
            "",
            f"- Forecasting metrics: {', '.join(result.metric_contract.forecasting_metrics)}",
            f"- Adapter status fields: {', '.join(result.metric_contract.adapter_status_fields)}",
            f"- Leaderboard allowed: {result.metric_contract.leaderboard_allowed}",
            "- Residual ranking may be used only for sensor-level forecasting error explanation.",
            "",
        ]
    )
    if result.local_execution_blocked_reason:
        lines.extend(
            [
                "## Local Execution Blocked",
                "",
                f"- Status: {result.status}",
                f"- Reason: {result.local_execution_blocked_reason}",
                "",
            ]
        )
    lines.extend(
        [
            "## Go / No-Go",
            "",
            f"- Go: {result.go_no_go_decision}.",
            "- No-Go: local model execution by default, cache inspection by default, downloads without network permission, training, processed-data writes, production claims, or leaderboard claims.",
            "",
            "## Invalid Claims",
            "",
        ]
    )
    lines.extend(f"- {claim}" for claim in result.invalid_claims)
    lines.extend(
        [
            "",
            "## Next Step",
            "",
            "- Use the explicit local config in the next task to record TTM adapter/cache/dependency evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise C33ConfigError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise C33ConfigError(f"{path} must contain a mapping")
    return loaded


def _project_root_for_config(path: Path) -> Path:
    resolved = path.resolve()
    for candidate in (resolved.parent, *resolved.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return Path.cwd()


def _local_execution_enabled(raw: dict[str, Any]) -> bool:
    local_execution = raw.get("local_execution")
    if local_execution is None:
        return False
    if not isinstance(local_execution, dict):
        raise C33ConfigError("local_execution must be a mapping")
    return _optional_bool(local_execution, "enabled", "local_execution", False)


def _load_safety_policy(
    raw: dict[str, Any],
    *,
    local_execution_enabled: bool,
) -> C33SafetyPolicy:
    policy = _required_mapping(raw, "safety_policy")
    values = {
        flag: _required_bool(policy, flag, "safety_policy")
        for flag in _SAFETY_FLAGS
    }

    if values["allow_training"] is not False:
        raise C33ConfigError("safety_policy.allow_training must always be false")
    if values["allow_write_processed"] is not False:
        raise C33ConfigError(
            "safety_policy.allow_write_processed must always be false"
        )
    if values["allow_download"] and not values["allow_network"]:
        raise C33ConfigError(
            "safety_policy.allow_network must be true when allow_download is true"
        )

    if local_execution_enabled:
        if values["allow_local_execution"] is not True:
            raise C33ConfigError(
                "safety_policy.allow_local_execution must be true when "
                "local_execution.enabled is true"
            )
        if values["allow_model_cache"] is not True:
            raise C33ConfigError(
                "safety_policy.allow_model_cache must be true when "
                "local_execution.enabled is true"
            )
    else:
        for flag in _SAFETY_FLAGS:
            if values[flag] is not False:
                raise C33ConfigError(
                    f"safety_policy.{flag} must be false for default "
                    "contract-only C3.3 config"
                )

    return C33SafetyPolicy(**values)


def _load_prerequisites(raw: dict[str, Any]) -> C33Prerequisites:
    prerequisites = _required_mapping(raw, "prerequisites")
    c32_local_status = _required_string(
        prerequisites, "c32_local_status", "prerequisites"
    )
    if c32_local_status != _EXPECTED_C32_LOCAL_STATUS:
        raise C33ConfigError(
            f"prerequisites.c32_local_status must be {_EXPECTED_C32_LOCAL_STATUS}"
        )
    return C33Prerequisites(
        c32_design_doc=Path(
            _required_string(prerequisites, "c32_design_doc", "prerequisites")
        ),
        c32_local_status=c32_local_status,
    )


def _load_candidate(raw: dict[str, Any]) -> C33Candidate:
    candidate = _required_mapping(raw, "candidate")
    for field, expected in _EXPECTED_CANDIDATE.items():
        value = _required_string(candidate, field, "candidate")
        if value != expected:
            raise C33ConfigError(f"candidate.{field} must be {expected}")
    return C33Candidate(
        model_id=_EXPECTED_CANDIDATE["model_id"],
        model_ref=_required_string(candidate, "model_ref", "candidate"),
        task_id=_EXPECTED_CANDIDATE["task_id"],
        dataset_view=_EXPECTED_CANDIDATE["dataset_view"],
    )


def _load_metric_contract(raw: dict[str, Any]) -> C33MetricContract:
    metric_contract = _required_mapping(raw, "metric_contract")
    leaderboard_allowed = _required_bool(
        metric_contract,
        "leaderboard_allowed",
        "metric_contract",
    )
    if leaderboard_allowed is not False:
        raise C33ConfigError("metric_contract.leaderboard_allowed must be false")
    return C33MetricContract(
        forecasting_metrics=_required_string_list(
            metric_contract,
            "forecasting_metrics",
            "metric_contract",
        ),
        adapter_status_fields=_required_string_list(
            metric_contract,
            "adapter_status_fields",
            "metric_contract",
        ),
        leaderboard_allowed=leaderboard_allowed,
    )


def _load_local_execution(
    raw: dict[str, Any],
    *,
    safety_policy: C33SafetyPolicy,
    config_root: Path,
) -> C33LocalExecutionConfig | None:
    local_execution = raw.get("local_execution")
    if local_execution is None:
        return None
    if not isinstance(local_execution, dict):
        raise C33ConfigError("local_execution must be a mapping")
    enabled = _optional_bool(local_execution, "enabled", "local_execution", False)
    if not enabled:
        return None
    if not safety_policy.allow_local_execution:
        raise C33ConfigError(
            "safety_policy.allow_local_execution must be true when "
            "local_execution.enabled is true"
        )
    if not safety_policy.allow_model_cache:
        raise C33ConfigError(
            "safety_policy.allow_model_cache must be true when "
            "local_execution.enabled is true"
        )

    model_cache_dir = Path(
        _required_string(local_execution, "model_cache_dir", "local_execution")
    )
    if not model_cache_dir.is_absolute():
        model_cache_dir = config_root / model_cache_dir
    fu13_like = _load_local_fu13_like(local_execution)
    return C33LocalExecutionConfig(
        enabled=enabled,
        model_cache_dir=model_cache_dir,
        fu13_like=fu13_like,
    )


def _load_local_fu13_like(raw: dict[str, Any]) -> C33LocalFu13LikeConfig:
    fu13_like = _required_mapping(raw, "fu13_like")
    config = C33LocalFu13LikeConfig(
        days=_required_int(fu13_like, "days", "local_execution.fu13_like"),
        seed=_required_int(fu13_like, "seed", "local_execution.fu13_like"),
        context_length=_required_int(
            fu13_like,
            "context_length",
            "local_execution.fu13_like",
        ),
        prediction_length=_required_int(
            fu13_like,
            "prediction_length",
            "local_execution.fu13_like",
        ),
        max_windows=_required_int(
            fu13_like,
            "max_windows",
            "local_execution.fu13_like",
        ),
        residual_top_k=_required_int(
            fu13_like,
            "residual_top_k",
            "local_execution.fu13_like",
        ),
    )
    for field in (
        "days",
        "context_length",
        "prediction_length",
        "max_windows",
        "residual_top_k",
    ):
        if getattr(config, field) <= 0:
            raise C33ConfigError(f"local_execution.fu13_like.{field} must be positive")
    if config.seed < 0:
        raise C33ConfigError("local_execution.fu13_like.seed must be non-negative")
    return config


def _load_outputs(raw: dict[str, Any]) -> C33Outputs:
    outputs = _required_mapping(raw, "outputs")
    return C33Outputs(
        report=Path(_required_string(outputs, "report", "outputs")),
    )


def _required_mapping(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise C33ConfigError(f"{key} must be a mapping")
    return value


def _required_string(
    raw: dict[str, Any],
    key: str,
    context: str = "config",
) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise C33ConfigError(f"{context}.{key} must be a non-empty string")
    return value


def _required_string_list(
    raw: dict[str, Any],
    key: str,
    context: str,
) -> tuple[str, ...]:
    value = raw.get(key)
    if not isinstance(value, list) or not value:
        raise C33ConfigError(f"{context}.{key} must be a non-empty list")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise C33ConfigError(f"{context}.{key} must contain non-empty strings")
    return tuple(value)


def _required_bool(raw: dict[str, Any], key: str, context: str) -> bool:
    value = raw.get(key)
    if not isinstance(value, bool):
        raise C33ConfigError(f"{context}.{key} must be a boolean")
    return value


def _optional_bool(
    raw: dict[str, Any],
    key: str,
    context: str,
    default: bool,
) -> bool:
    value = raw.get(key, default)
    if not isinstance(value, bool):
        raise C33ConfigError(f"{context}.{key} must be a boolean")
    return value


def _required_int(raw: dict[str, Any], key: str, context: str) -> int:
    value = raw.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise C33ConfigError(f"{context}.{key} must be an integer")
    return value
