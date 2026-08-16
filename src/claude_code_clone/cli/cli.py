"""Typer CLI entrypoint and command definitions."""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from claude_code_clone.cli.repl import InteractiveREPL
from claude_code_clone.cli.ui.renderer import TerminalRenderer
from claude_code_clone.core.agent.react_loop import ReActController, ReActEvents
from claude_code_clone.core.config.settings import Settings
from claude_code_clone.core.providers.models import resolve_model_name

app = typer.Typer(
    name="claude-code-clone",
    help="Modular Multi-Provider Claude Code Clone with Enterprise RAG",
    add_completion=True,
    no_args_is_help=False,
)

console = Console()
renderer = TerminalRenderer(console)


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context) -> None:
    """Default action: if no subcommand is passed, start the interactive REPL."""
    if ctx.invoked_subcommand is None:
        start_interactive_session()


def start_interactive_session(
    model: str | None = None,
    permission: str | None = None,
    workspace: str | None = None,
) -> None:
    """Launches the interactive terminal session."""
    settings = Settings.load()
    if model:
        settings.model = resolve_model_name(model)
    if permission:
        settings.permission_mode = permission
    if workspace:
        settings.workspace_dir = str(Path(workspace).resolve())

    controller = ReActController(settings=settings)
    repl = InteractiveREPL(controller=controller)
    asyncio.run(repl.start())


@app.command(name="start")
def start_cmd(
    model: str | None = typer.Option(
        None, "--model", "-m", help="LLM model (e.g. gpt-4o, claude-3-7-sonnet)"
    ),
    permission: str | None = typer.Option(
        None,
        "--permission",
        "-p",
        help="Permission mode: strict, accept_read_only, autonomous",
    ),
    workspace: str | None = typer.Option(
        None, "--workspace", "-w", help="Target workspace path"
    ),
) -> None:
    """Start an interactive coding assistant REPL."""
    start_interactive_session(model=model, permission=permission, workspace=workspace)


@app.command(name="run")
def run_cmd(
    prompt: str = typer.Argument(..., help="The instruction or coding task to execute"),
    model: str | None = typer.Option(None, "--model", "-m", help="LLM model to use"),
    permission: str = typer.Option(
        "autonomous", "--permission", "-p", help="Permission mode for single run"
    ),
    workspace: str | None = typer.Option(
        None, "--workspace", "-w", help="Workspace path"
    ),
) -> None:
    """Execute a single coding task or prompt non-interactively."""
    settings = Settings.load()
    if model:
        settings.model = resolve_model_name(model)
    settings.permission_mode = permission
    if workspace:
        settings.workspace_dir = str(Path(workspace).resolve())

    controller = ReActController(settings=settings)
    events = ReActEvents()
    events.on_token = renderer.stream_token
    events.on_tool_call_start = renderer.render_tool_start
    events.on_tool_call_result = renderer.render_tool_result

    console.print(
        f"[dim]Running task with model:[/dim] [bold green]{settings.model}[/bold green]\n"
    )
    try:
        asyncio.run(controller.execute_turn(prompt, events=events))
    finally:
        renderer.end_stream_line()


@app.command(name="config")
def config_cmd() -> None:
    """Inspect current active configuration."""
    settings = Settings.load()
    table = Table(title="Claude Code Clone Configuration", border_style="cyan")
    table.add_column("Setting", style="bold")
    table.add_column("Value", style="green")

    table.add_row("Model", settings.model)
    table.add_row("Permission Mode", settings.permission_mode)
    table.add_row("Workspace", settings.workspace_dir)
    table.add_row("Max Context Tokens", str(settings.max_context_tokens))
    table.add_row("RAG Enabled", str(settings.rag_enabled))
    table.add_row("RAG Embedding Model", settings.rag_embedding_model)
    table.add_row(
        "Anthropic Key",
        "Configured" if settings.anthropic_api_key else "[dim]Not set[/dim]",
    )
    table.add_row(
        "OpenAI Key", "Configured" if settings.openai_api_key else "[dim]Not set[/dim]"
    )
    table.add_row(
        "Gemini Key", "Configured" if settings.gemini_api_key else "[dim]Not set[/dim]"
    )
    table.add_row(
        "OpenRouter Key",
        "Configured" if settings.openrouter_api_key else "[dim]Not set[/dim]",
    )

    console.print(table)


@app.command(name="rag-ingest")
def rag_ingest_cmd(
    path: str = typer.Argument(
        ..., help="Path to file or directory of documents/code to ingest"
    ),
    collection: str = typer.Option(
        "enterprise-docs", "--collection", "-c", help="Target collection name"
    ),
) -> None:
    """Ingest enterprise documents or codebases into the local RAG vector store."""
    from claude_code_clone.core.rag.engine import RAGEngine

    engine = RAGEngine()
    console.print(
        f"[bold cyan]Ingesting '{path}' into RAG collection '{collection}'...[/bold cyan]"
    )
    count = asyncio.run(engine.ingest_path(path, collection=collection))
    renderer.render_success(
        f"Successfully ingested {count} chunks into collection '{collection}'."
    )


@app.command(name="rag-query")
def rag_query_cmd(
    query: str = typer.Argument(..., help="Search query"),
    collection: str = typer.Option(
        "enterprise-docs", "--collection", "-c", help="Collection to query"
    ),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of results"),
) -> None:
    """Perform a direct semantic & keyword search against the RAG knowledge base."""
    from claude_code_clone.core.rag.engine import RAGEngine

    engine = RAGEngine()
    results = asyncio.run(engine.search(query, collection=collection, top_k=top_k))
    if not results:
        renderer.render_info(f"No results found for query '{query}'.")
        return

    console.print(f"[bold cyan]Found {len(results)} relevant items:[/bold cyan]\n")
    for i, res in enumerate(results, 1):
        console.print(
            f"[bold yellow]Result {i}[/bold yellow] [dim](Score: {res.score:.3f} | Source: {res.source})[/dim]"
        )
        console.print(res.content)
        console.print("[dim]─" * 40 + "[/dim]")
