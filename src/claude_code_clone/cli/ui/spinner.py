"""Rich status spinner for tool executions and LLM generation."""

from contextlib import contextmanager
from typing import Generator
from rich.console import Console


@contextmanager
def status_spinner(console: Console, text: str = "Thinking...") -> Generator[None, None, None]:
    """Context manager wrapping long operations with a smooth terminal spinner."""
    with console.status(f"[bold cyan]{text}[/bold cyan]", spinner="dots") as status:
        yield
