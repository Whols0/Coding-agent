from __future__ import annotations

import subprocess
from pathlib import Path


def apply_patch_file(root: Path, patch_file: Path) -> str:
    result = subprocess.run(
        ["patch", "-p0", "-i", str(patch_file.resolve())],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "patch failed")
    return result.stdout.strip() or "Patch applied successfully."
