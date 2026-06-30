from __future__ import annotations

from pathlib import Path

from code_assistant.models import FileSummary, RepoSummary

EXCLUDED_DIRS = {
    ".conda",
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
}

LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".md": "Markdown",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".sh": "Shell",
}


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        files.append(path)
    return files


def summarize_repo(root: Path, file_limit: int = 200) -> RepoSummary:
    root = root.resolve()
    files = iter_files(root)
    language_counts: dict[str, int] = {}

    for file_path in files:
        language = LANGUAGE_MAP.get(file_path.suffix.lower())
        if language:
            language_counts[language] = language_counts.get(language, 0) + 1

    sample_files = [
        FileSummary(
            path=str(file_path.relative_to(root)),
            size_bytes=file_path.stat().st_size,
        )
        for file_path in files[:file_limit]
    ]

    top_level_entries = sorted(
        [entry.name for entry in root.iterdir() if not entry.name.startswith(".")]
    )

    return RepoSummary(
        root=root,
        file_count=len(files),
        top_level_entries=top_level_entries,
        language_counts=dict(sorted(language_counts.items())),
        sample_files=sample_files,
    )
