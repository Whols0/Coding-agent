from __future__ import annotations

from pathlib import Path

from code_assistant.models import RepoSummary, TaskPlan
from code_assistant.tools.fs_tools import summarize_repo


def build_task_plan(task: str, root: Path) -> TaskPlan:
    summary: RepoSummary = summarize_repo(root)
    assumptions = [
        "This MVP uses deterministic planning instead of a live LLM call.",
        "The repository summary is based on visible local files only.",
    ]
    steps = [
        f"Inspect the workspace at {summary.root} and identify the files related to: {task}.",
        "Locate the likely entrypoints, configuration files, tests, and affected modules.",
        "Propose the smallest code change that satisfies the task with minimal regression risk.",
        "Implement the change behind clear boundaries so it can be reviewed as a focused diff.",
        "Run targeted verification commands such as tests, lint, or a narrow smoke check.",
    ]

    if summary.language_counts:
        dominant = ", ".join(
            f"{name} ({count})" for name, count in list(summary.language_counts.items())[:4]
        )
        assumptions.append(f"Primary languages detected: {dominant}.")
    else:
        assumptions.append("No known source language was detected yet.")

    verification = [
        "Review the final diff for unintended edits.",
        "Run the most relevant automated checks for the touched area.",
        "Document follow-up work if the change should later be upgraded into a multi-step agent workflow.",
    ]
    return TaskPlan(task=task, assumptions=assumptions, steps=steps, verification=verification)
