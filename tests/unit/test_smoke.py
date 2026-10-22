from src.pipeline import main


def test_pipeline_skeleton_runs():
    assert main() == "pipeline ok"
