from pathlib import Path

import pytest

from b08_model_core.experiments.c3_public_dataset_registry import (
    C3DatasetRole,
    C3RegistryConfigError,
    load_c3_registry_config,
)


def test_c3_default_registry_config_has_initial_dataset_set():
    config = load_c3_registry_config("configs/c_stage_c3_public_dataset_registry.yaml")

    assert config.stage == "C3_public_dataset_registry"
    assert config.outputs.report == Path("reports/c_stage_c3_public_dataset_registry.md")
    assert tuple(item.dataset_id for item in config.datasets) == (
        "fu13_internal",
        "nasa_cmapss",
        "ims_bearing",
        "pronostia_femto",
        "tennessee_eastman_process",
    )
    assert config.datasets[0].dataset_role == C3DatasetRole.INTERNAL_ANCHOR
    assert all(item.invalid_claims for item in config.datasets)


def test_c3_registry_rejects_missing_required_dataset_field(tmp_path):
    broken = tmp_path / "broken.yaml"
    broken.write_text(
        """
stage: C3_public_dataset_registry
latest_source_calibration:
  enabled: true
  policy: watchlist_only
outputs:
  report: reports/c_stage_c3_public_dataset_registry.md
datasets:
  - dataset_id: missing_display_name
""",
        encoding="utf-8",
    )

    with pytest.raises(C3RegistryConfigError, match="display_name"):
        load_c3_registry_config(broken)
