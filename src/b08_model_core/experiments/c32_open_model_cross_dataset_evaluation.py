from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class C32ConfigError(ValueError):
    """Raised when the C3.2 cross-dataset evaluation config is invalid."""


@dataclass(frozen=True)
class C32SafetyPolicy:
    allow_network: bool
    allow_download: bool
    allow_local_raw_data: bool
    allow_model_cache: bool
    allow_training: bool
    allow_write_processed: bool


@dataclass(frozen=True)
class C32Prerequisites:
    c31_review_doc: Path
    required_status: str
    required_readiness_detail: str
    reviewed_raw_file_count: int
    leakage_guard_passed: bool


@dataclass(frozen=True)
class C32DatasetView:
    dataset_id: str
    display_name: str
    status: str
    source: str
    local_path: str
    task_families: tuple[str, ...]
    default_action: str
    comparable_scope: str


@dataclass(frozen=True)
class C32TaskContract:
    task_id: str
    status: str
    compatible_dataset_views: tuple[str, ...]
    required_metrics: tuple[str, ...]
    default_action: str


@dataclass(frozen=True)
class C32ModelCandidate:
    model_id: str
    role: str
    status: str
    task_ids: tuple[str, ...]
    default_action: str


@dataclass(frozen=True)
class C32ModelCachePolicy:
    cache_dir: Path
    default_action: str


@dataclass(frozen=True)
class C32MetricContract:
    rul_metrics: tuple[str, ...]
    forecasting_metrics: tuple[str, ...]
    representation_metrics: tuple[str, ...]
    cross_dataset_summary: str
    leaderboard_allowed: bool


@dataclass(frozen=True)
class C32Outputs:
    report: Path


@dataclass(frozen=True)
class C32Config:
    stage: str
    safety_policy: C32SafetyPolicy
    prerequisites: C32Prerequisites
    dataset_views: tuple[C32DatasetView, ...]
    task_contracts: tuple[C32TaskContract, ...]
    model_candidates: tuple[C32ModelCandidate, ...]
    model_cache_policy: C32ModelCachePolicy
    metric_contract: C32MetricContract
    outputs: C32Outputs


@dataclass(frozen=True)
class C32DatasetResult:
    dataset_id: str
    display_name: str
    status: str
    source: str
    local_path: str
    task_families: tuple[str, ...]
    default_action: str
    comparable_scope: str


@dataclass(frozen=True)
class C32TaskResult:
    task_id: str
    status: str
    compatible_dataset_views: tuple[str, ...]
    required_metrics: tuple[str, ...]
    default_action: str


@dataclass(frozen=True)
class C32ModelResult:
    model_id: str
    role: str
    status: str
    task_ids: tuple[str, ...]
    default_action: str


@dataclass(frozen=True)
class C32RunResult:
    config_path: Path
    stage: str
    status: str
    go_no_go_decision: str
    safety_policy: C32SafetyPolicy
    prerequisites: C32Prerequisites
    dataset_results: tuple[C32DatasetResult, ...]
    task_results: tuple[C32TaskResult, ...]
    model_results: tuple[C32ModelResult, ...]
    model_cache_policy: C32ModelCachePolicy
    metric_contract: C32MetricContract
    invalid_claims: tuple[str, ...]


_EXPECTED_STAGE = "C3_2_open_model_cross_dataset_evaluation"
_EXPECTED_C31_STATUS = "schema_validated_ready_for_c32"
_EXPECTED_C31_READINESS_DETAIL = "full_classic_cmapss_validated"
_EXPECTED_C31_REVIEWED_RAW_FILE_COUNT = 12
_CONTRACT_READY_STATUS = "contract_ready_local_execution_blocked"
_GO_DECISION = "Go for C3.2 local execution design"
_INVALID_CLAIMS = (
    "no production RUL",
    "no production alarms",
    "no maintenance recommendations",
    "no benchmark leaderboard",
    "no self-developed model superiority",
)
_SAFETY_FLAGS = (
    "allow_network",
    "allow_download",
    "allow_local_raw_data",
    "allow_model_cache",
    "allow_training",
    "allow_write_processed",
)
_REQUIRED_DATASET_IDS = {
    "cmapss_classic_rul",
    "fu13_real_forecasting_evidence",
    "fu13_like_simulated_forecasting",
}
_REQUIRED_TASK_IDS = {
    "rul_regression",
    "forecasting_residual",
    "representation_diagnostics",
}
_REQUIRED_MODEL_IDS = {
    "baseline",
    "ttm",
    "chronos",
    "timesfm",
    "moirai",
    "moment",
    "units",
}
_ALLOWED_DATASET_STATUSES = {
    "eligible_but_local_raw_required",
    "documented_evidence_only",
    "contract_ready_no_scoring",
}
_ALLOWED_TASK_STATUSES = {
    "blocked_in_default",
    "contract_ready_no_scoring",
    "planned_not_executed",
}
_ALLOWED_MODEL_STATUSES = {
    "contract_ready_no_scoring",
    "skipped_model_cache_disabled",
    "planned_not_executed",
}
_ALLOWED_DEFAULT_ACTIONS = {
    "skipped_local_raw_disabled",
    "skipped_real_data_not_read_by_default",
    "contract_only_no_metrics",
    "skipped_planned_task",
    "contract_only_no_model_run",
    "skipped_no_cache_or_dependencies",
    "not_inspected_model_cache_disabled",
}
_FORBIDDEN_OVERCLAIMING_TOKENS = (
    "score",
    "scored",
    "scoring",
    "rank",
    "ranked",
    "leaderboard",
    "train",
    "training",
    "executed",
    "available_and_ran",
)


def load_c32_config(path: str | Path) -> C32Config:
    raw = _load_yaml_mapping(Path(path))
    stage = _required_string(raw, "stage")
    if stage != _EXPECTED_STAGE:
        raise C32ConfigError(f"stage must be {_EXPECTED_STAGE}")

    safety_policy = _load_safety_policy(raw)
    prerequisites = _load_prerequisites(raw)
    dataset_views = _load_dataset_views(raw)
    task_contracts = _load_task_contracts(raw, dataset_views)
    model_candidates = _load_model_candidates(raw, task_contracts)
    model_cache_policy = _load_model_cache_policy(raw)
    metric_contract = _load_metric_contract(raw)
    _validate_task_metrics(task_contracts, metric_contract)
    outputs = _load_outputs(raw)

    return C32Config(
        stage=stage,
        safety_policy=safety_policy,
        prerequisites=prerequisites,
        dataset_views=dataset_views,
        task_contracts=task_contracts,
        model_candidates=model_candidates,
        model_cache_policy=model_cache_policy,
        metric_contract=metric_contract,
        outputs=outputs,
    )


def run_c32_open_model_cross_dataset_evaluation(
    config: C32Config,
    config_path: str | Path,
) -> C32RunResult:
    return C32RunResult(
        config_path=Path(config_path),
        stage=config.stage,
        status=_CONTRACT_READY_STATUS,
        go_no_go_decision=_GO_DECISION,
        safety_policy=config.safety_policy,
        prerequisites=config.prerequisites,
        dataset_results=tuple(
            C32DatasetResult(
                dataset_id=item.dataset_id,
                display_name=item.display_name,
                status=item.status,
                source=item.source,
                local_path=item.local_path,
                task_families=item.task_families,
                default_action=item.default_action,
                comparable_scope=item.comparable_scope,
            )
            for item in config.dataset_views
        ),
        task_results=tuple(
            C32TaskResult(
                task_id=item.task_id,
                status=item.status,
                compatible_dataset_views=item.compatible_dataset_views,
                required_metrics=item.required_metrics,
                default_action=item.default_action,
            )
            for item in config.task_contracts
        ),
        model_results=tuple(
            C32ModelResult(
                model_id=item.model_id,
                role=item.role,
                status=item.status,
                task_ids=item.task_ids,
                default_action=item.default_action,
            )
            for item in config.model_candidates
        ),
        model_cache_policy=config.model_cache_policy,
        metric_contract=config.metric_contract,
        invalid_claims=_INVALID_CLAIMS,
    )


def render_c32_report(result: C32RunResult) -> str:
    lines = [
        "# C3.2 Open Model Cross-Dataset Evaluation Report",
        "",
        "## Summary",
        "",
        f"- Stage: {result.stage}",
        f"- Config: {result.config_path}",
        f"- Status: {result.status}",
        f"- Decision: {result.go_no_go_decision}",
        "- No model training, scoring, or leaderboard is executed.",
        "- C-MAPSS RUL results and FU13 forecasting results are not directly interchangeable.",
        "- Do not claim production RUL, production alarms, maintenance recommendations, benchmark leadership, or self-developed model superiority.",
        "",
        "## Safety Policy",
        "",
    ]
    for flag in _SAFETY_FLAGS:
        lines.append(f"- {flag}: {getattr(result.safety_policy, flag)}")
    lines.extend(
        [
            "",
            "## C3.1 Prerequisites",
            "",
            f"- Review doc: {result.prerequisites.c31_review_doc}",
            f"- Required status: {result.prerequisites.required_status}",
            f"- Required readiness detail: {result.prerequisites.required_readiness_detail}",
            f"- Reviewed raw file count: {result.prerequisites.reviewed_raw_file_count}",
            f"- Leakage guard passed: {result.prerequisites.leakage_guard_passed}",
            "",
            "## Dataset View Matrix",
            "",
            "| Dataset | Display name | Status | Source | Local path | Task families | Default action | Comparable scope |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in result.dataset_results:
        lines.append(
            "| "
            + " | ".join(
                [
                    item.dataset_id,
                    item.display_name,
                    item.status,
                    item.source,
                    item.local_path or "(none)",
                    ", ".join(item.task_families),
                    item.default_action,
                    item.comparable_scope,
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Task Compatibility",
            "",
            "| Task | Status | Compatible dataset views | Required metrics | Default action |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for item in result.task_results:
        lines.append(
            "| "
            + " | ".join(
                [
                    item.task_id,
                    item.status,
                    ", ".join(item.compatible_dataset_views),
                    ", ".join(item.required_metrics),
                    item.default_action,
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Model Candidate Status",
            "",
            "| Model | Role | Status | Task IDs | Default action |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for item in result.model_results:
        lines.append(
            "| "
            + " | ".join(
                [
                    item.model_id,
                    item.role,
                    item.status,
                    ", ".join(item.task_ids),
                    item.default_action,
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Metric Contract",
            "",
            f"- RUL metrics: {', '.join(result.metric_contract.rul_metrics)}",
            f"- Forecasting metrics: {', '.join(result.metric_contract.forecasting_metrics)}",
            f"- Representation metrics: {', '.join(result.metric_contract.representation_metrics)}",
            f"- Cross-dataset summary: {result.metric_contract.cross_dataset_summary}",
            f"- Leaderboard allowed: {result.metric_contract.leaderboard_allowed}",
            f"- Model cache policy: {result.model_cache_policy.default_action} ({result.model_cache_policy.cache_dir})",
            "",
            "## Go / No-Go",
            "",
            f"- Go: {result.go_no_go_decision}.",
            "- No-Go: benchmark claims, production claims, model scoring, training, or leaderboard claims.",
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
            "- Design explicit local execution for C3.2 with separate RUL and forecasting metrics.",
            "",
        ]
    )
    return "\n".join(lines)


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise C32ConfigError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise C32ConfigError(f"{path} must contain a mapping")
    return loaded


def _load_safety_policy(raw: dict[str, Any]) -> C32SafetyPolicy:
    policy = _required_mapping(raw, "safety_policy")
    values = {
        flag: _required_bool(policy, flag, "safety_policy") for flag in _SAFETY_FLAGS
    }
    for flag, value in values.items():
        if value is not False:
            raise C32ConfigError(f"safety_policy.{flag} must be false by default")
    return C32SafetyPolicy(**values)


def _load_prerequisites(raw: dict[str, Any]) -> C32Prerequisites:
    prerequisites = _required_mapping(raw, "prerequisites")
    loaded = C32Prerequisites(
        c31_review_doc=Path(
            _required_string(prerequisites, "c31_review_doc", "prerequisites")
        ),
        required_status=_required_string(
            prerequisites, "required_status", "prerequisites"
        ),
        required_readiness_detail=_required_string(
            prerequisites, "required_readiness_detail", "prerequisites"
        ),
        reviewed_raw_file_count=_required_int(
            prerequisites, "reviewed_raw_file_count", "prerequisites"
        ),
        leakage_guard_passed=_required_bool(
            prerequisites, "leakage_guard_passed", "prerequisites"
        ),
    )
    if loaded.required_status != _EXPECTED_C31_STATUS:
        raise C32ConfigError(
            f"prerequisites.required_status must be {_EXPECTED_C31_STATUS}"
        )
    if loaded.required_readiness_detail != _EXPECTED_C31_READINESS_DETAIL:
        raise C32ConfigError(
            "prerequisites.required_readiness_detail must be "
            f"{_EXPECTED_C31_READINESS_DETAIL}"
        )
    if loaded.reviewed_raw_file_count != _EXPECTED_C31_REVIEWED_RAW_FILE_COUNT:
        raise C32ConfigError(
            "prerequisites.reviewed_raw_file_count must be "
            f"{_EXPECTED_C31_REVIEWED_RAW_FILE_COUNT}"
        )
    if loaded.leakage_guard_passed is not True:
        raise C32ConfigError("prerequisites.leakage_guard_passed must be true")
    return loaded


def _load_dataset_views(raw: dict[str, Any]) -> tuple[C32DatasetView, ...]:
    items = _required_list(raw, "dataset_views")
    seen: set[str] = set()
    entries: list[C32DatasetView] = []
    for index, item in enumerate(items):
        entry_raw = _list_item_mapping(item, "dataset_views", index)
        dataset_id = _required_string(entry_raw, "dataset_id", f"dataset_views[{index}]")
        if dataset_id in seen:
            raise C32ConfigError(f"duplicate dataset_id: {dataset_id}")
        seen.add(dataset_id)
        status = _required_string(entry_raw, "status", f"dataset_views[{index}]")
        default_action = _required_string(
            entry_raw, "default_action", f"dataset_views[{index}]"
        )
        _validate_allowed_value(
            status,
            _ALLOWED_DATASET_STATUSES,
            f"dataset_views[{index}].status",
        )
        _validate_allowed_value(
            default_action,
            _ALLOWED_DEFAULT_ACTIONS,
            f"dataset_views[{index}].default_action",
        )
        entries.append(
            C32DatasetView(
                dataset_id=dataset_id,
                display_name=_required_string(
                    entry_raw, "display_name", f"dataset_views[{index}]"
                ),
                status=status,
                source=_required_string(entry_raw, "source", f"dataset_views[{index}]"),
                local_path=_required_string_or_empty(
                    entry_raw, "local_path", f"dataset_views[{index}]"
                ),
                task_families=_required_string_list(
                    entry_raw, "task_families", f"dataset_views[{index}]"
                ),
                default_action=default_action,
                comparable_scope=_required_string(
                    entry_raw, "comparable_scope", f"dataset_views[{index}]"
                ),
            )
        )
    _validate_required_ids(seen, _REQUIRED_DATASET_IDS, "dataset_id")
    return tuple(entries)


def _load_task_contracts(
    raw: dict[str, Any],
    dataset_views: tuple[C32DatasetView, ...],
) -> tuple[C32TaskContract, ...]:
    items = _required_list(raw, "task_contracts")
    known_dataset_ids = {entry.dataset_id for entry in dataset_views}
    seen: set[str] = set()
    entries: list[C32TaskContract] = []
    for index, item in enumerate(items):
        entry_raw = _list_item_mapping(item, "task_contracts", index)
        task_id = _required_string(entry_raw, "task_id", f"task_contracts[{index}]")
        if task_id in seen:
            raise C32ConfigError(f"duplicate task_id: {task_id}")
        seen.add(task_id)
        compatible_dataset_views = _required_string_list(
            entry_raw, "compatible_dataset_views", f"task_contracts[{index}]"
        )
        for dataset_id in compatible_dataset_views:
            if dataset_id not in known_dataset_ids:
                raise C32ConfigError(
                    f"task_contracts[{index}] references unknown dataset: {dataset_id}"
                )
        status = _required_string(entry_raw, "status", f"task_contracts[{index}]")
        default_action = _required_string(
            entry_raw, "default_action", f"task_contracts[{index}]"
        )
        _validate_allowed_value(
            status,
            _ALLOWED_TASK_STATUSES,
            f"task_contracts[{index}].status",
        )
        _validate_allowed_value(
            default_action,
            _ALLOWED_DEFAULT_ACTIONS,
            f"task_contracts[{index}].default_action",
        )
        entries.append(
            C32TaskContract(
                task_id=task_id,
                status=status,
                compatible_dataset_views=compatible_dataset_views,
                required_metrics=_required_string_list(
                    entry_raw, "required_metrics", f"task_contracts[{index}]"
                ),
                default_action=default_action,
            )
        )
    _validate_required_ids(seen, _REQUIRED_TASK_IDS, "task_id")
    return tuple(entries)


def _load_model_candidates(
    raw: dict[str, Any],
    task_contracts: tuple[C32TaskContract, ...],
) -> tuple[C32ModelCandidate, ...]:
    items = _required_list(raw, "model_candidates")
    known_task_ids = {entry.task_id for entry in task_contracts}
    seen: set[str] = set()
    entries: list[C32ModelCandidate] = []
    for index, item in enumerate(items):
        entry_raw = _list_item_mapping(item, "model_candidates", index)
        model_id = _required_string(entry_raw, "model_id", f"model_candidates[{index}]")
        if model_id in seen:
            raise C32ConfigError(f"duplicate model_id: {model_id}")
        seen.add(model_id)
        task_ids = _required_string_list(
            entry_raw, "task_ids", f"model_candidates[{index}]"
        )
        for task_id in task_ids:
            if task_id not in known_task_ids:
                raise C32ConfigError(
                    f"model_candidates[{index}] references unknown task: {task_id}"
                )
        status = _required_string(entry_raw, "status", f"model_candidates[{index}]")
        default_action = _required_string(
            entry_raw, "default_action", f"model_candidates[{index}]"
        )
        _validate_allowed_value(
            status,
            _ALLOWED_MODEL_STATUSES,
            f"model_candidates[{index}].status",
        )
        _validate_allowed_value(
            default_action,
            _ALLOWED_DEFAULT_ACTIONS,
            f"model_candidates[{index}].default_action",
        )
        entries.append(
            C32ModelCandidate(
                model_id=model_id,
                role=_required_string(entry_raw, "role", f"model_candidates[{index}]"),
                status=status,
                task_ids=task_ids,
                default_action=default_action,
            )
        )
    _validate_required_ids(seen, _REQUIRED_MODEL_IDS, "model_id")
    return tuple(entries)


def _load_model_cache_policy(raw: dict[str, Any]) -> C32ModelCachePolicy:
    policy = _required_mapping(raw, "model_cache_policy")
    default_action = _required_string(
        policy, "default_action", "model_cache_policy"
    )
    _validate_allowed_value(
        default_action,
        _ALLOWED_DEFAULT_ACTIONS,
        "model_cache_policy.default_action",
    )
    return C32ModelCachePolicy(
        cache_dir=Path(_required_string(policy, "cache_dir", "model_cache_policy")),
        default_action=default_action,
    )


def _load_metric_contract(raw: dict[str, Any]) -> C32MetricContract:
    contract = _required_mapping(raw, "metric_contract")
    leaderboard_allowed = _required_bool(
        contract, "leaderboard_allowed", "metric_contract"
    )
    if leaderboard_allowed is not False:
        raise C32ConfigError("metric_contract.leaderboard_allowed must be false")
    return C32MetricContract(
        rul_metrics=_required_string_list(contract, "rul_metrics", "metric_contract"),
        forecasting_metrics=_required_string_list(
            contract, "forecasting_metrics", "metric_contract"
        ),
        representation_metrics=_required_string_list(
            contract, "representation_metrics", "metric_contract"
        ),
        cross_dataset_summary=_required_string(
            contract, "cross_dataset_summary", "metric_contract"
        ),
        leaderboard_allowed=leaderboard_allowed,
    )


def _load_outputs(raw: dict[str, Any]) -> C32Outputs:
    outputs = _required_mapping(raw, "outputs")
    return C32Outputs(report=Path(_required_string(outputs, "report", "outputs")))


def _validate_task_metrics(
    task_contracts: tuple[C32TaskContract, ...],
    metric_contract: C32MetricContract,
) -> None:
    known_metrics = set(metric_contract.rul_metrics)
    known_metrics.update(metric_contract.forecasting_metrics)
    known_metrics.update(metric_contract.representation_metrics)
    for task in task_contracts:
        for metric in task.required_metrics:
            if metric not in known_metrics:
                raise C32ConfigError(
                    f"task_contracts.{task.task_id} references unknown metric: {metric}"
                )


def _validate_required_ids(
    actual_ids: set[str],
    required_ids: set[str],
    field_name: str,
) -> None:
    missing = sorted(required_ids - actual_ids)
    extra = sorted(actual_ids - required_ids)
    if missing or extra:
        parts = []
        if missing:
            parts.append(f"missing required {field_name}: {', '.join(missing)}")
        if extra:
            parts.append(f"unknown {field_name}: {', '.join(extra)}")
        raise C32ConfigError("; ".join(parts))


def _validate_allowed_value(
    value: str,
    allowed_values: set[str],
    field_name: str,
) -> None:
    if value in allowed_values:
        return
    if _contains_forbidden_overclaim(value):
        raise C32ConfigError(f"{field_name} has overclaiming value {value}")
    else:
        allowed = ", ".join(sorted(allowed_values))
        raise C32ConfigError(f"{field_name} has invalid value {value}; allowed: {allowed}")


def _contains_forbidden_overclaim(value: str) -> bool:
    normalized = value.lower()
    return any(token in normalized for token in _FORBIDDEN_OVERCLAIMING_TOKENS)


def _required_mapping(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise C32ConfigError(f"{key} must be a mapping")
    return value


def _required_list(raw: dict[str, Any], key: str) -> list[Any]:
    value = raw.get(key)
    if not isinstance(value, list) or not value:
        raise C32ConfigError(f"{key} must be a non-empty list")
    return value


def _list_item_mapping(value: Any, section: str, index: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise C32ConfigError(f"{section}[{index}] must be a mapping")
    return value


def _required_string(
    raw: dict[str, Any],
    key: str,
    context: str = "config",
) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise C32ConfigError(f"{context}.{key} must be a non-empty string")
    return value


def _required_string_or_empty(raw: dict[str, Any], key: str, context: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str):
        raise C32ConfigError(f"{context}.{key} must be a string")
    return value


def _required_string_list(
    raw: dict[str, Any],
    key: str,
    context: str,
) -> tuple[str, ...]:
    value = raw.get(key)
    if not isinstance(value, list) or not value:
        raise C32ConfigError(f"{context}.{key} must be a non-empty list")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise C32ConfigError(f"{context}.{key} must contain non-empty strings")
    return tuple(value)


def _required_bool(raw: dict[str, Any], key: str, context: str) -> bool:
    value = raw.get(key)
    if not isinstance(value, bool):
        raise C32ConfigError(f"{context}.{key} must be a boolean")
    return value


def _required_int(raw: dict[str, Any], key: str, context: str) -> int:
    value = raw.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise C32ConfigError(f"{context}.{key} must be an integer")
    return value
