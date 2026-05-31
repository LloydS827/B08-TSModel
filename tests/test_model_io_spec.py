from b08_model_core.model_io.io_spec import ModelInputSpec, OutputHeadRegistry


def test_model_io_spec_matches_b08_requirements():
    spec = ModelInputSpec.default()
    assert spec.has_input("X", shape="B,L,C")
    assert spec.has_input("stage_token", shape="B,L")
    assert spec.has_input("sensor_token", shape="C")
    assert spec.has_input("domain_token", shape="C")
    assert OutputHeadRegistry.default().names == {
        "forecasting",
        "imputation",
        "reconstruction",
        "representation",
        "degradation",
        "adaptation",
    }
