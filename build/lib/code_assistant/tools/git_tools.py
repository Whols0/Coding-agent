from __future__ import annotations

import subprocess
from pathlib import Path


def git_diff(root: Path) -> str:
    result = subprocess.run(
        ["git", "diff", "--", "."],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git diff failed")
    return result.stdout

