from prompt_toolkit.document import Document

from code_assistant.session import SlashCommandCompleter


def test_slash_command_completion_lists_known_commands() -> None:
    completer = SlashCommandCompleter()

    completions = list(completer.get_completions(Document("/d", 2), None))

    assert any(item.text == "/diff" for item in completions)


def test_non_slash_input_does_not_offer_command_completion() -> None:
    completer = SlashCommandCompleter()

    completions = list(completer.get_completions(Document("hello", 5), None))

    assert completions == []
