"""Interactive user confirmation and permission prompts."""

from rich.console import Console
from rich.prompt import Confirm


async def ask_user_confirmation(
    console: Console,
    action_description: str,
    default: bool = True,
) -> bool:
    """Prompts the user to approve or deny a destructive tool execution."""
    console.print(
        f"\n[bold yellow]⚠️ Permission Required:[/bold yellow] {action_description}"
    )
    return Confirm.ask(
        "Do you want to execute this action?", default=default, console=console
    )
