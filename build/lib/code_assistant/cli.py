from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from code_assistant.session import ChatSession

app = typer.Typer(help="A clean-room CLI MVP for a code assistant.")
console = Console()


def resolve_root(path: str | None) -> Path:
    return Path(path).resolve() if path else Path.cwd().resolve()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    path: str = typer.Option(".", "--path", help="Workspace path."),
) -> None:
    """Start the interactive assistant when no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        ChatSession(console=console, root=resolve_root(path)).run()


if __name__ == "__main__":
    app()
