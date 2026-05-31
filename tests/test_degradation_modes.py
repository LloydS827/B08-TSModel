from b08_model_core.simulation.degradation_modes import inject_degradation


def test_degradation_labels_exist_before_failure_proxy(clean_signal_frame):
    degraded = inject_degradation(clean_signal_frame, modes=["vacuum_leak"], seed=4)
    assert "incipient_degradation" in set(degraded["degradation_label"])
    first_deg = degraded.query("degradation_label == 'incipient_degradation'")["timestamp"].min()
    first_proxy = degraded.query("failure_proxy == True")["timestamp"].min()
    assert first_deg < first_proxy
