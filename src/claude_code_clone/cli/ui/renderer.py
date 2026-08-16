"""Rich Terminal UI renderer for streaming tokens, markdown, diffs, and tool blocks."""

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.theme import Theme
from claude_code_clone.core.agent.types import ToolCall, ToolResult

custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "tool_name": "bold magenta",
    "highlight": "bold blue",
})

console = Console(theme=custom_theme)


class TerminalRenderer:
    """Handles formatted terminal outputs and real-time streaming."""

    def __init__(self, c: Console | None = None):
        self.console = c or console

    def render_welcome_banner(self, model: str, workspace: str, rag_enabled: bool) -> None:
        """Displays the CLI startup banner."""
        banner = (
            f"[bold cyan]🤖 Claude Code Clone[/bold cyan] [dim](Multi-Provider & Enterprise RAG)[/dim]\n"
            f"[dim]• Model:[/dim] [bold green]{model}[/bold green]\n"
            f"[dim]• Workspace:[/dim] [dim]{workspace}[/dim]\n"
            f"[dim]• Enterprise RAG:[/dim] [yellow]{'Enabled' if rag_enabled else 'Disabled'}[/yellow]\n"
            f"[dim]Type your request or [bold cyan]/help[/bold cyan] for slash commands. Press [bold]Ctrl+C[/bold] to cancel a turn.[/dim]"
        )
        self.console.print(Panel(banner, border_style="cyan", padding=(1, 2)))

    def stream_token(self, token: str) -> None:
        """Prints a single token to stdout immediately."""
        self.console.print(token, end="", highlight=False)

    def end_stream_line(self) -> None:
        """Adds a trailing newline after a stream finishes."""
        self.console.print()

    def render_markdown(self, text: str) -> None:
        """Renders GitHub-flavored markdown with syntax highlighting."""
        md = Markdown(text, code_theme="monokai")
        self.console.print(md)

    def render_tool_start(self, tool_call: ToolCall) -> None:
        """Displays tool execution start banner."""
        args_str = ", ".join(f"{k}={v!r}" for k, v in list(tool_call.arguments.items())[:3])
        if len(tool_call.arguments) > 3:
            args_str += ", ..."
        self.console.print(f"\n[dim]⚡ Executing tool[/dim] [tool_name]{tool_call.name}[/tool_name][dim]({args_str})[/dim]")

    def render_tool_result(self, result: ToolResult) -> None:
        """Displays tool execution output."""
        if result.is_error:
            self.console.print(Panel(
                result.output,
                title=f"[error]Tool Error: {result.tool_name}[/error]",
                border_style="red",
                padding=(0, 1),
            ))
        else:
            # Check if output contains a diff block
            if "```diff" in result.output:
                self.console.print(Markdown(result.output, code_theme="monokai"))
            else:
                lines = result.output.strip().splitlines()
                preview = "\n".join(lines[:15])
                if len(lines) > 15:
                    preview += f"\n[dim]...({len(lines) - 15} more lines hidden)[/dim]"
                self.console.print(Panel(
                    preview,
                    title=f"[dim]Result: {result.tool_name}[/dim]",
                    border_style="dim",
                    padding=(0, 1),
                ))

    def render_error(self, message: str) -> None:
        """Displays an error alert."""
        self.console.print(f"[error]✖ Error:[/error] {message}")

    def render_info(self, message: str) -> None:
        """Displays an informational message."""
        self.console.print(f"[info]ℹ[/info] {message}")

    def render_success(self, message: str) -> None:
        """Displays a success message."""
        self.console.print(f"[success]✔[/success] {message}")
