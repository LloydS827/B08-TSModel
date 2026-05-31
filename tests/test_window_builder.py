from b08_model_core.tasks.window_builder import build_model_windows


def test_windows_include_stage_sensor_domain_and_masks(simulated_frame):
    windows = build_model_windows(simulated_frame, context_length=128, prediction_length=32)
    first = windows[0]
    assert first.X.shape[-1] >= 15
    assert first.mask.shape == first.X.shape
    assert first.stage_token.shape[0] == first.X.shape[0]
    assert len(first.sensor_token) == first.X.shape[-1]
    assert first.y.shape[0] == 32
