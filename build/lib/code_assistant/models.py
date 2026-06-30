from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class FileSummary(BaseModel):
    path: str
    size_bytes: int


class RepoSummary(BaseModel):
    root: Path
    file_count: int
    top_level_entries: list[str] = Field(default_factory=list)
    language_counts: dict[str, int] = Field(default_factory=dict)
    sample_files: list[FileSummary] = Field(default_factory=list)


class TaskPlan(BaseModel):
    task: str
    assumptions: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    verification: list[str] = Field(default_factory=list)


class CommandResult(BaseModel):
    command: str
    exit_code: int
    stdout: str
    stderr: str

