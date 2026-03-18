"""Interactive Terminal REPL powered by prompt_toolkit and the ReAct engine."""

import asyncio

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory

from praxis_ai.cli.ui.prompt import ask_user_confirmation
from praxis_ai.cli.ui.renderer import TerminalRenderer, console
from praxis_ai.core.agent.react_loop import ReActController, ReActEvents
from praxis_ai.core.config.constants import GLOBAL_CONFIG_DIR
from praxis_ai.core.config.permissions import PermissionMode
from praxis_ai.core.config.settings import Settings
from praxis_ai.core.providers.models import MODEL_ALIASES, resolve_model_name

SLASH_COMMANDS = [
    "/help",
    "/model",
    "/permission",
    "/rag",
    "/compact",
    "/clear",
    "/history",
    "/exit",
    "/quit",
]


class InteractiveREPL:
    """Manages the interactive terminal prompt session."""

    def __init__(self, controller: ReActController | None = None):
        self.settings = Settings.load()
        self.controller = controller or ReActController(settings=self.settings)
        self.renderer = TerminalRenderer(console)
        self.running = True

        # Setup prompt_toolkit history & auto-completer
        GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        history_file = GLOBAL_CONFIG_DIR / "history.txt"
        completer = WordCompleter(
            SLASH_COMMANDS + list(MODEL_ALIASES.keys()),
            ignore_case=True,
            sentence=True,
        )
        self.prompt_session: PromptSession = PromptSession(
            history=FileHistory(str(history_file)),
            completer=completer,
        )

    def _display_help(self) -> None:
        help_text = (
            "### Available Slash Commands:\n"
            "- **/model `[name]`**: View or switch active LLM (e.g. `/model claude-3-7-sonnet`, `/model gpt-4o`, `/model ollama/deepseek-r1:14b`)\n"
            "- **/permission `[mode]`**: Set permission guardrail (`strict`, `accept_read_only`, `autonomous`)\n"
            "- **/rag `[on|off]`**: Enable or disable RAG enterprise knowledge lookup\n"
            "- **/compact**: Compacts and summarizes past conversation turns to free token budget\n"
            "- **/clear**: Clears terminal and resets conversation history\n"
            "- **/history**: Shows the number of messages in active memory\n"
            "- **/exit** or **/quit**: Exit the session"
        )
        self.renderer.render_markdown(help_text)

    async def _handle_slash_command(self, cmd_line: str) -> bool:
        """Executes slash commands. Returns True if handled."""
        parts = cmd_line.strip().split()
        if not parts:
            return True

        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in ("/exit", "/quit"):
            self.running = False
            self.renderer.render_info("Goodbye! 👋")
            return True

        elif cmd == "/help":
            self._display_help()
            return True

        elif cmd == "/clear":
            self.controller.reset_history()
            console.clear()
            self.renderer.render_welcome_banner(
                model=self.controller.settings.model,
                workspace=str(self.controller.workspace_dir),
                rag_enabled=self.controller.settings.rag_enabled,
            )
            self.renderer.render_success("Conversation history cleared.")
            return True

        elif cmd == "/history":
            count = len(self.controller.history)
            self.renderer.render_info(
                f"Active conversation history contains {count} message(s)."
            )
            return True

        elif cmd == "/model":
            if not args:
                self.renderer.render_info(
                    f"Current active model: [bold green]{self.controller.settings.model}[/bold green]"
                )
                self.renderer.render_info(
                    f"Available shortcuts: {', '.join(list(MODEL_ALIASES.keys())[:8])}..."
                )
            else:
                new_model = resolve_model_name(args[0])
                self.controller.settings.model = new_model
                self.renderer.render_success(
                    f"Switched active model to: [bold green]{new_model}[/bold green]"
                )
            return True

        elif cmd == "/permission":
            if not args:
                self.renderer.render_info(
                    f"Current permission mode: [bold yellow]{self.controller.permission_manager.mode.value}[/bold yellow]"
                )
            else:
                try:
                    new_mode = PermissionMode(args[0].lower())
                    self.controller.permission_manager.mode = new_mode
                    self.controller.settings.permission_mode = new_mode.value
                    self.renderer.render_success(
                        f"Permission mode set to: [bold yellow]{new_mode.value}[/bold yellow]"
                    )
                except ValueError:
                    self.renderer.render_error(
                        "Valid modes: strict, accept_read_only, autonomous"
                    )
            return True

        elif cmd == "/rag":
            if not args:
                status = (
                    "enabled" if self.controller.settings.rag_enabled else "disabled"
                )
                self.renderer.render_info(
                    f"Enterprise RAG is currently [yellow]{status}[/yellow]."
                )
            else:
                val = args[0].lower() in ("on", "true", "1", "enable", "yes")
                self.controller.settings.rag_enabled = val
                self.renderer.render_success(
                    f"Enterprise RAG {'enabled' if val else 'disabled'}."
                )
            return True

        elif cmd == "/compact":
            self.controller.history = (
                self.controller.context_manager.prune_and_compact_if_needed(
                    self.controller.history
                )
            )
            self.renderer.render_success("Conversation context compacted.")
            return True

        return False

    async def start(self) -> None:
        """Starts the interactive REPL loop."""
        self.renderer.render_welcome_banner(
            model=self.controller.settings.model,
            workspace=str(self.controller.workspace_dir),
            rag_enabled=self.controller.settings.rag_enabled,
        )

        while self.running:
            try:
                # Prompt user input asynchronously
                user_input = await self.prompt_session.prompt_async(
                    HTML("\n╭─ <ansicyan><b>You</b></ansicyan>\n╰─&gt; ")
                )
                user_input = user_input.strip()

                if not user_input:
                    continue

                if user_input.startswith("/"):
                    handled = await self._handle_slash_command(user_input)
                    if handled:
                        continue

                # Prepare ReAct UI event hooks
                events = ReActEvents()
                events.on_token = self.renderer.stream_token
                events.on_tool_call_start = self.renderer.render_tool_start
                events.on_tool_call_result = self.renderer.render_tool_result

                async def _confirm_tool(reason: str, params: dict) -> bool:
                    return await ask_user_confirmation(console, reason)

                events.on_tool_call_confirm = _confirm_tool

                # Run ReAct loop
                console.print("\n╭─ [bold magenta]Assistant[/bold magenta]")
                try:
                    await self.controller.execute_turn(user_input, events=events)
                finally:
                    self.renderer.end_stream_line()

            except (KeyboardInterrupt, asyncio.CancelledError):
                self.renderer.render_warning("\nTurn interrupted by user.")
                continue
            except EOFError:
                self.running = False
                self.renderer.render_info("Exiting.")
                break
            except Exception as e:
                self.renderer.render_error(str(e))
