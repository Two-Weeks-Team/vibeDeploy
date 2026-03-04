from agent.state import VibeDeployState


def test_vibedeploystate_is_typeddict():
    annotations = VibeDeployState.__annotations__
    assert "raw_input" in annotations
    assert "input_type" in annotations
    assert "phase" in annotations
    assert "scoring" in annotations
    assert "deploy_result" in annotations
