from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.application.current import get_app
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion, PathCompleter
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import CompleteStyle
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from code_assistant.config import AssistantConfig
from code_assistant.planner import build_task_plan
from code_assistant.tools.fs_tools import summarize_repo
from code_assistant.tools.git_tools import git_diff
from code_assistant.tools.patch_tools import apply_patch_file
from code_assistant.tools.shell_tools import run_command


@dataclass(frozen=True)
class SlashCommandSpec:
    name: str
    usage: str
    description: str


SLASH_COMMANDS: tuple[SlashCommandSpec, ...] = (
    SlashCommandSpec("/help", "/help", "Show available commands"),
    SlashCommandSpec("/pwd", "/pwd", "Show the current workspace"),
    SlashCommandSpec("/cd", "/cd <path>", "Change the current workspace"),
    SlashCommandSpec("/scan", "/scan [path]", "Summarize the current workspace"),
    SlashCommandSpec("/ask", "/ask <task>", "Generate an implementation plan"),
    SlashCommandSpec("/diff", "/diff", "Show git diff for the current workspace"),
    SlashCommandSpec("/run", "/run <command>", "Run a local command in the workspace"),
    SlashCommandSpec("/apply", "/apply <patch_file>", "Apply a patch file"),
    SlashCommandSpec("/clear", "/clear", "Clear the terminal"),
    SlashCommandSpec("/exit", "/exit", "Exit the assistant"),
)


def build_help_text() -> str:
    lines = ["Slash commands:"]
    for command in SLASH_COMMANDS:
        lines.append(f"{command.usage:<22} {command.description}")
    lines.append("")
    lines.append('Anything that does not start with "/" is treated like a coding request and routed to /ask.')
    return "\n".join(lines)


HELP_TEXT = build_help_text()


class SlashCommandCompleter(Completer):
    def __init__(self) -> None:
        self.command_map = {command.name: command for command in SLASH_COMMANDS}
        self.path_command_completer = PathCompleter(expanduser=True)

    def get_completions(self, document: Document, complete_event):  # type: ignore[override]
        text = document.text_before_cursor
        stripped = text.lstrip()
        if not stripped.startswith("/"):
            return

        try:
            parts = shlex.split(stripped)
        except ValueError:
            parts = stripped.split()

        ends_with_space = text.endswith(" ")

        if len(parts) <= 1 and not ends_with_space:
            for command in SLASH_COMMANDS:
                if command.name.startswith(stripped):
                    yield Completion(
                        command.name,
                        start_position=-len(stripped),
                        display=command.name,
                        display_meta=command.description,
                    )
            return

        if not parts:
            return

        command_name = parts[0]
        if command_name not in {"/cd", "/scan", "/apply"}:
            return

        if ends_with_space:
            path_prefix = ""
        else:
            path_prefix = parts[-1]

        path_document = Document(path_prefix, cursor_position=len(path_prefix))
        for completion in self.path_command_completer.get_completions(path_document, complete_event):
            yield completion


class ChatSession:
    def __init__(self, console: Console, root: Path) -> None:
        self.console = console
        self.root = root.resolve()
        self.prompt_session = self._build_prompt_session()

    def _build_prompt_session(self) -> PromptSession[str]:
        history_path = self.root / ".code-assistant-history"
        return PromptSession(
            completer=SlashCommandCompleter(),
            complete_while_typing=True,
            complete_style=CompleteStyle.MULTI_COLUMN,
            reserve_space_for_menu=8,
            auto_suggest=AutoSuggestFromHistory(),
            history=FileHistory(str(history_path)),
            key_bindings=self._build_key_bindings(),
        )

    def _build_key_bindings(self) -> KeyBindings:
        bindings = KeyBindings()

        @bindings.add("c-space")
        def _(event) -> None:
            buffer = event.current_buffer
            buffer.start_completion(select_first=False)

        @bindings.add("tab")
        def _(event) -> None:
            buffer = event.current_buffer
            if buffer.complete_state:
                buffer.complete_next()
                return
            buffer.start_completion(select_first=True)

        @bindings.add("s-tab")
        def _(event) -> None:
            buffer = event.current_buffer
            if buffer.complete_state:
                buffer.complete_previous()

        return bindings

    def _prompt_message(self) -> HTML:
        return HTML("<ansibrightblack>code-assistant</ansibrightblack> <ansigreen>></ansigreen> ")

    def _bottom_toolbar(self) -> HTML:
        return HTML(
            " <b>/</b> commands  <b>Tab</b> complete  <b>Ctrl-Space</b> menu  "
            f"<b>workspace</b> {self.root} "
        )

    def print_welcome(self) -> None:
        self.console.print(
            Panel(
                "\n".join(
                    [
                        "Interactive Code Assistant",
                        "",
                        f"Workspace: {self.root}",
                        'Type a request directly, or use "/" commands like /scan or /run.',
                        'Type "/" then press Tab to browse tools. Use "/help" to see all commands.',
                    ]
                ),
                title="Code Assistant",
            )
        )

    def run(self) -> None:
        self.print_welcome()
        while True:
            try:
                raw = self.prompt_session.prompt(
                    self._prompt_message(),
                    bottom_toolbar=self._bottom_toolbar,
                ).strip()
            except EOFError:
                self.console.print("\nSession closed.")
                break
            except KeyboardInterrupt:
                self.console.print("\nUse /exit to leave the assistant.")
                continue

            if not raw:
                continue

            try:
                should_exit = self.handle_input(raw)
            except Exception as exc:  # pragma: no cover - defensive CLI handling
                self.console.print(Panel(str(exc), title="Error"))
                should_exit = False

            if should_exit:
                break

    def handle_input(self, raw: str) -> bool:
        if raw.startswith("/"):
            return self._handle_slash_command(raw)

        self._render_plan(raw)
        return False

    def _handle_slash_command(self, raw: str) -> bool:
        parts = shlex.split(raw)
        command = parts[0]
        args = parts[1:]

        if command == "/help":
            self.console.print(Panel(HELP_TEXT, title="Commands"))
            return False
        if command == "/pwd":
            self.console.print(str(self.root))
            return False
        if command == "/cd":
            if not args:
                raise ValueError("Usage: /cd <path>")
            new_root = Path(args[0]).expanduser().resolve()
            if not new_root.exists() or not new_root.is_dir():
                raise ValueError(f"Directory not found: {new_root}")
            self.root = new_root
            self.prompt_session = self._build_prompt_session()
            self.console.print(f"Workspace changed to: {self.root}")
            return False
        if command == "/scan":
            target = self.root if not args else Path(args[0]).expanduser().resolve()
            self._render_scan(target)
            return False
        if command == "/ask":
            if not args:
                raise ValueError("Usage: /ask <task>")
            self._render_plan(" ".join(args))
            return False
        if command == "/diff":
            output = git_diff(self.root)
            self.console.print(output or "No diff.")
            return False
        if command == "/run":
            if not args:
                raise ValueError("Usage: /run <command>")
            config = AssistantConfig(workspace_root=self.root)
            result = run_command(" ".join(args), config.workspace_root, config.command_timeout_seconds)
            self.console.print(Panel(result.stdout or "(no stdout)", title=f"stdout | exit={result.exit_code}"))
            if result.stderr:
                self.console.print(Panel(result.stderr, title="stderr"))
            return False
        if command == "/apply":
            if not args:
                raise ValueError("Usage: /apply <patch_file>")
            message = apply_patch_file(self.root, Path(args[0]))
            self.console.print(message)
            return False
        if command == "/clear":
            self.console.clear()
            return False
        if command == "/exit":
            self.console.print("Bye.")
            return True

        raise ValueError(f"Unknown command: {command}. Use /help.")

    def _render_scan(self, target: Path) -> None:
        summary = summarize_repo(target)

        table = Table(title=f"Workspace Summary: {summary.root}")
        table.add_column("Metric")
        table.add_column("Value")
        table.add_row("Files", str(summary.file_count))
        table.add_row("Top Level", ", ".join(summary.top_level_entries[:10]) or "(empty)")
        langs = ", ".join(f"{k}: {v}" for k, v in summary.language_counts.items()) or "None detected"
        table.add_row("Languages", langs)
        self.console.print(table)

        sample = Table(title="Sample Files")
        sample.add_column("Path")
        sample.add_column("Size")
        for item in summary.sample_files[:15]:
            sample.add_row(item.path, str(item.size_bytes))
        self.console.print(sample)

    def _render_plan(self, task: str) -> None:
        plan = build_task_plan(task, self.root)
        body = "\n".join(
            [
                "Assumptions:",
                *[f"- {item}" for item in plan.assumptions],
                "",
                "Steps:",
                *[f"- {item}" for item in plan.steps],
                "",
                "Verification:",
                *[f"- {item}" for item in plan.verification],
            ]
        )
        self.console.print(Panel(body, title=f"Task Plan: {plan.task}"))
