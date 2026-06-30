from pathlib import Path

from rich.console import Console

from code_assistant.session import ChatSession


def test_plain_text_routes_to_plan(tmp_path: Path) -> None:
    console = Console(record=True)
    session = ChatSession(console=console, root=tmp_path)

    should_exit = session.handle_input("Add authentication")

    assert should_exit is False
    assert "Task Plan: Add authentication" in console.export_text()


def test_exit_command_ends_session(tmp_path: Path) -> None:
    console = Console(record=True)
    session = ChatSession(console=console, root=tmp_path)

    should_exit = session.handle_input("/exit")

    assert should_exit is True
    assert "Bye." in console.export_text()
