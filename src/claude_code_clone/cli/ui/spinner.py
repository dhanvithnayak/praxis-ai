"""Rich status spinner for tool executions and LLM generation."""

from collections.abc import Generator
from contextlib import contextmanager

from rich.console import Console


@contextmanager
def status_spinner(
    console: Console, text: str = "Thinking..."
) -> Generator[None, None, None]:
    """Context manager wrapping long operations with a smooth terminal spinner."""
    with console.status(f"[bold cyan]{text}[/bold cyan]", spinner="dots"):
        yield
