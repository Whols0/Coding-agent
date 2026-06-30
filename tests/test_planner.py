from pathlib import Path

from code_assistant.planner import build_task_plan


def test_build_task_plan_returns_steps(tmp_path: Path) -> None:
    plan = build_task_plan("Add authentication", tmp_path)
    assert plan.task == "Add authentication"
    assert plan.steps
    assert plan.verification
