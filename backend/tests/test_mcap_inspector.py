from backend.app.integrations.mcap.inspector import MCAPInspector


def test_mcap_inspector():
    inspector = MCAPInspector()
    evidence = inspector.extract_evidence_summary()
    assert evidence["tf_analysis"]["drift_detected"] is True
    assert evidence["tf_analysis"]["error_norm_m"] > 0.02
    assert evidence["navigation_analysis"]["oscillation_detected"] is True
    assert evidence["camera_analysis"]["frame_drop_detected"] is True
