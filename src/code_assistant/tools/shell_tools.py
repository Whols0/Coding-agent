from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from code_assistant.models import CommandResult


def run_command(command: str, root: Path, timeout_seconds: int) -> CommandResult:
    result = subprocess.run(
        shlex.split(command),
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_seconds,
    )
    return CommandResult(
        command=command,
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )
