from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class AssistantConfig(BaseModel):
    workspace_root: Path = Field(default_factory=lambda: Path.cwd())
    scan_file_limit: int = 200
    scan_preview_bytes: int = 800
    command_timeout_seconds: int = 120

