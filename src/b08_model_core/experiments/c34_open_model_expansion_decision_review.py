from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class C34ConfigError(ValueError):
    """Raised when the C3.4 decision review config is invalid."""


@dataclass(frozen=True)
class C34SafetyPolicy:
    allow_network: bool
    allow_download: bool
    allow_model_cache: bool
    allow_local_execution: bool
    allow_training: bool
    allow_write_processed: bool


@dataclass(frozen=True)
class C34Prerequisites:
    c33_design_doc: Path
    c33_default_status: str
    c32_local_status: str
    c22_watchlist_source: Path


@dataclass(frozen=True)
class C34C33Evidence:
    source: str
    status: str
    candidate: str
    task: str
    adapter_evidence: str


@dataclass(frozen=True)
class C34DecisionPolicy:
    require_ttm_status: str
    required_adapter_fields: tuple[str, ...]
    leaderboard_allowed: bool
    rul_open_model_allowed: bool
    second_candidate_execution_allowed: bool


@dataclass(frozen=True)
class C34CandidateReview:
    candidate_id: str
    display_name: str
    c22_source: str
    readiness_status: str
    promotion_blocker: str
    next_design_requirement: str


@dataclass(frozen=True)
class C34Outputs:
    report: Path


@dataclass(frozen=True)
class C34Config:
    stage: str
    safety_policy: C34SafetyPolicy
    prerequisites: C34Prerequisites
    c33_evidence: C34C33Evidence
    decision_policy: C34DecisionPolicy
    candidate_review: tuple[C34CandidateReview, ...]
    outputs: C34Outputs


@dataclass(frozen=True)
class C34RunResult:
    config_path: Path
    stage: str
    status: str
    safety_policy: C34SafetyPolicy
    prerequisites: C34Prerequisites
    c33_evidence: C34C33Evidence
    decision_policy: C34DecisionPolicy
    candidate_review: tuple[C34CandidateReview, ...]
    invalid_claims: tuple[str, ...]


_EXPECTED_STAGE = "C3_4_open_model_expansion_decision_review"
_CONTRACT_READY_STATUS = "contract_ready_single_candidate_local_execution_blocked"
_SUPPORTED_C33_STATUSES = (_CONTRACT_READY_STATUS,)
_DEFAULT_CONTRACT_SOURCE = "default_contract"
_DEFAULT_CONTRACT_CANDIDATE = "ttm"
_DEFAULT_CONTRACT_TASK = "fu13_like_forecasting"
_DEFAULT_ADAPTER_EVIDENCE = "not_applicable_default_contract"
_REQUIRED_TTM_STATUS = "local_execution_ttm_forecasting_ready"
_HOLD_STATUS = "hold_candidate_expansion_pending_ttm_local_evidence"
_EXPECTED_REQUIRED_ADAPTER_FIELDS = (
    "dependency_status",
    "weight_status",
    "adapter_status",
    "runtime_seconds",
    "input_shape",
    "output_shape",
    "actual_network_used",
    "download_allowed_not_verified",
)
_EXPECTED_CANDIDATE_IDS = (
    "chronos_bolt_route",
    "timesfm_2_5_route",
    "moirai_uni2ts_route",
)
_SAFETY_FLAGS = (
    "allow_network",
    "allow_download",
    "allow_model_cache",
    "allow_local_execution",
    "allow_training",
    "allow_write_processed",
)
_DECISION_ALLOW_FLAGS = (
    "leaderboard_allowed",
    "rul_open_model_allowed",
    "second_candidate_execution_allowed",
)
_INVALID_CLAIMS = (
    "No leaderboard",
    "No RUL open-model readiness claim",
    "No second-candidate execution approval",
    "No production maintenance recommendation",
)


def load_c34_config(path: str | Path) -> C34Config:
    config_path = Path(path)
    raw = _load_yaml_mapping(config_path)
    stage = _required_string(raw, "stage")
    if stage != _EXPECTED_STAGE:
        raise C34ConfigError(f"stage must be {_EXPECTED_STAGE}")

    return C34Config(
        stage=stage,
        safety_policy=_load_safety_policy(raw),
        prerequisites=_load_prerequisites(raw),
        c33_evidence=_load_c33_evidence(raw),
        decision_policy=_load_decision_policy(raw),
        candidate_review=_load_candidate_review(raw),
        outputs=_load_outputs(raw),
    )


def run_c34_open_model_expansion_decision_review(
    config: C34Config,
    config_path: str | Path,
) -> C34RunResult:
    if config.c33_evidence.status != _CONTRACT_READY_STATUS:
        raise C34ConfigError(
            "C3.4 default runner only supports contract-ready C3.3 evidence"
        )
    return C34RunResult(
        config_path=Path(config_path),
        stage=config.stage,
        status=_HOLD_STATUS,
        safety_policy=config.safety_policy,
        prerequisites=config.prerequisites,
        c33_evidence=config.c33_evidence,
        decision_policy=config.decision_policy,
        candidate_review=config.candidate_review,
        invalid_claims=_INVALID_CLAIMS,
    )


def render_c34_report(result: C34RunResult) -> str:
    lines = [
        "# C3.4 Open Model Expansion Decision Review",
        "",
        "## Summary",
        "",
        f"- Stage: {result.stage}",
        f"- Config: {result.config_path}",
        f"- Status: {result.status}",
        "- Default path is review-only and holds candidate expansion until TTM local evidence exists.",
        "",
        "## Safety Policy",
        "",
    ]
    for flag in _SAFETY_FLAGS:
        lines.append(f"- {flag}: {getattr(result.safety_policy, flag)}")
    lines.extend(
        [
            "",
            "## C3.3 Evidence Gate",
            "",
            f"- Source: {result.c33_evidence.source}",
            f"- Status: {result.c33_evidence.status}",
            f"- Candidate: {result.c33_evidence.candidate}",
            f"- Task: {result.c33_evidence.task}",
            f"- Adapter evidence: {result.c33_evidence.adapter_evidence}",
            "- Candidate expansion stays blocked until local TTM forecasting evidence reaches the required status.",
            "",
            "## Decision Policy",
            "",
            f"- Required TTM status: {result.decision_policy.require_ttm_status}",
            "- Required adapter fields: "
            + ", ".join(result.decision_policy.required_adapter_fields),
            f"- Leaderboard allowed: {result.decision_policy.leaderboard_allowed}",
            f"- RUL open model allowed: {result.decision_policy.rul_open_model_allowed}",
            "- Second candidate execution allowed: "
            f"{result.decision_policy.second_candidate_execution_allowed}",
            "",
            "## Candidate Expansion Review",
            "",
        ]
    )
    for item in result.candidate_review:
        lines.extend(
            [
                f"### {item.display_name}",
                "",
                f"- Candidate ID: {item.candidate_id}",
                f"- C2.2 source: {item.c22_source}",
                f"- Readiness: {item.readiness_status}",
                f"- Promotion blocker: {item.promotion_blocker}",
                f"- Next design requirement: {item.next_design_requirement}",
                "",
            ]
        )
    lines.extend(
        [
            "## Metric Separation",
            "",
            "- C3.4 does not compare open-model forecasting scores.",
            "- No leaderboard may be inferred from review-only candidates.",
            "- RUL claims remain separate from FU13-like forecasting adapter evidence.",
            "",
            "## Go / No-Go",
            "",
            "- Go: write a follow-up design only after C3.3 records local TTM evidence.",
            "- No-Go: execute Chronos, TimesFM, Moirai, or any second candidate from this default review.",
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
            "- Complete explicit local C3.3 TTM forecasting evidence before promoting any candidate expansion path.",
            "",
        ]
    )
    return "\n".join(lines)


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise C34ConfigError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise C34ConfigError(f"{path} must contain a mapping")
    return loaded


def _load_safety_policy(raw: dict[str, Any]) -> C34SafetyPolicy:
    policy = _required_mapping(raw, "safety_policy")
    values = {
        flag: _required_bool(policy, flag, "safety_policy")
        for flag in _SAFETY_FLAGS
    }
    for flag, value in values.items():
        if value is not False:
            raise C34ConfigError(f"safety_policy.{flag} must be false")
    return C34SafetyPolicy(**values)


def _load_prerequisites(raw: dict[str, Any]) -> C34Prerequisites:
    prerequisites = _required_mapping(raw, "prerequisites")
    return C34Prerequisites(
        c33_design_doc=Path(
            _required_string(prerequisites, "c33_design_doc", "prerequisites")
        ),
        c33_default_status=_required_string(
            prerequisites, "c33_default_status", "prerequisites"
        ),
        c32_local_status=_required_string(
            prerequisites, "c32_local_status", "prerequisites"
        ),
        c22_watchlist_source=Path(
            _required_string(prerequisites, "c22_watchlist_source", "prerequisites")
        ),
    )


def _load_c33_evidence(raw: dict[str, Any]) -> C34C33Evidence:
    evidence = _required_mapping(raw, "c33_evidence")
    result = C34C33Evidence(
        source=_required_string(evidence, "source", "c33_evidence"),
        status=_required_string(evidence, "status", "c33_evidence"),
        candidate=_required_string(evidence, "candidate", "c33_evidence"),
        task=_required_string(evidence, "task", "c33_evidence"),
        adapter_evidence=_required_string(
            evidence, "adapter_evidence", "c33_evidence"
        ),
    )
    if result.status not in _SUPPORTED_C33_STATUSES:
        raise C34ConfigError(
            "c33_evidence.status must be one of "
            f"{list(_SUPPORTED_C33_STATUSES)}"
        )
    if (
        result.status == _CONTRACT_READY_STATUS
        and result.source != _DEFAULT_CONTRACT_SOURCE
    ):
        raise C34ConfigError(
            "c33_evidence.source must be "
            f"{_DEFAULT_CONTRACT_SOURCE} for {result.status}"
        )
    if (
        result.status == _CONTRACT_READY_STATUS
        and result.candidate != _DEFAULT_CONTRACT_CANDIDATE
    ):
        raise C34ConfigError(
            "c33_evidence.candidate must be "
            f"{_DEFAULT_CONTRACT_CANDIDATE} for {result.status}"
        )
    if (
        result.status == _CONTRACT_READY_STATUS
        and result.task != _DEFAULT_CONTRACT_TASK
    ):
        raise C34ConfigError(
            "c33_evidence.task must be "
            f"{_DEFAULT_CONTRACT_TASK} for {result.status}"
        )
    if (
        result.status == _CONTRACT_READY_STATUS
        and result.adapter_evidence != _DEFAULT_ADAPTER_EVIDENCE
    ):
        raise C34ConfigError(
            "c33_evidence.adapter_evidence must be "
            f"{_DEFAULT_ADAPTER_EVIDENCE} for {result.status}"
        )
    return result


def _load_decision_policy(raw: dict[str, Any]) -> C34DecisionPolicy:
    policy = _required_mapping(raw, "decision_policy")
    fields = _required_string_list(
        policy,
        "required_adapter_fields",
        "decision_policy",
    )
    if fields != _EXPECTED_REQUIRED_ADAPTER_FIELDS:
        raise C34ConfigError(
            "decision_policy.required_adapter_fields must be "
            f"{list(_EXPECTED_REQUIRED_ADAPTER_FIELDS)}"
        )
    values = {
        flag: _required_bool(policy, flag, "decision_policy")
        for flag in _DECISION_ALLOW_FLAGS
    }
    for flag, value in values.items():
        if value is not False:
            raise C34ConfigError(f"decision_policy.{flag} must be false")
    require_ttm_status = _required_string(
        policy,
        "require_ttm_status",
        "decision_policy",
    )
    if require_ttm_status != _REQUIRED_TTM_STATUS:
        raise C34ConfigError(
            "decision_policy.require_ttm_status must be "
            f"{_REQUIRED_TTM_STATUS}"
        )
    return C34DecisionPolicy(
        require_ttm_status=require_ttm_status,
        required_adapter_fields=fields,
        leaderboard_allowed=values["leaderboard_allowed"],
        rul_open_model_allowed=values["rul_open_model_allowed"],
        second_candidate_execution_allowed=values[
            "second_candidate_execution_allowed"
        ],
    )


def _load_candidate_review(raw: dict[str, Any]) -> tuple[C34CandidateReview, ...]:
    value = raw.get("candidate_review")
    if not isinstance(value, list) or not value:
        raise C34ConfigError("candidate_review must be a non-empty list")

    candidates: list[C34CandidateReview] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise C34ConfigError(f"candidate_review[{index}] must be a mapping")
        candidate = C34CandidateReview(
            candidate_id=_required_string(
                item, "candidate_id", f"candidate_review[{index}]"
            ),
            display_name=_required_string(
                item, "display_name", f"candidate_review[{index}]"
            ),
            c22_source=_required_string(
                item, "c22_source", f"candidate_review[{index}]"
            ),
            readiness_status=_required_string(
                item, "readiness_status", f"candidate_review[{index}]"
            ),
            promotion_blocker=_required_string(
                item, "promotion_blocker", f"candidate_review[{index}]"
            ),
            next_design_requirement=_required_string(
                item, "next_design_requirement", f"candidate_review[{index}]"
            ),
        )
        if candidate.readiness_status != "review_only_not_promoted":
            raise C34ConfigError(
                "candidate_review readiness_status must be "
                "review_only_not_promoted"
            )
        candidates.append(candidate)

    candidate_ids = tuple(item.candidate_id for item in candidates)
    if candidate_ids != _EXPECTED_CANDIDATE_IDS:
        raise C34ConfigError(
            "candidate_review candidate_id values must be "
            f"{list(_EXPECTED_CANDIDATE_IDS)}"
        )
    return tuple(candidates)


def _load_outputs(raw: dict[str, Any]) -> C34Outputs:
    outputs = _required_mapping(raw, "outputs")
    return C34Outputs(
        report=Path(_required_string(outputs, "report", "outputs")),
    )


def _required_mapping(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise C34ConfigError(f"{key} must be a mapping")
    return value


def _required_string(
    raw: dict[str, Any],
    key: str,
    context: str = "config",
) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise C34ConfigError(f"{context}.{key} must be a non-empty string")
    return value


def _required_string_list(
    raw: dict[str, Any],
    key: str,
    context: str,
) -> tuple[str, ...]:
    value = raw.get(key)
    if not isinstance(value, list) or not value:
        raise C34ConfigError(f"{context}.{key} must be a non-empty list")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise C34ConfigError(f"{context}.{key} must contain non-empty strings")
    return tuple(value)


def _required_bool(raw: dict[str, Any], key: str, context: str) -> bool:
    value = raw.get(key)
    if not isinstance(value, bool):
        raise C34ConfigError(f"{context}.{key} must be a boolean")
    return value
