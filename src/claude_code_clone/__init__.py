"""Claude Code Clone package entrypoint."""

from claude_code_clone.cli.cli import app


def main() -> None:
    """CLI script entrypoint."""
    app()


if __name__ == "__main__":
    main()
