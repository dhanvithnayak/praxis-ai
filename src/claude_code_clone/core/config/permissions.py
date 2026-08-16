"""Permission guardrails and safety policy management for tool execution."""

from enum import Enum


class PermissionMode(str, Enum):
    STRICT = "strict"                  # Asks confirmation for ALL tools (read, write, bash)
    ACCEPT_READ_ONLY = "accept_read_only"  # Auto-executes read-only & RAG tools, asks for write & bash
    AUTONOMOUS = "autonomous"          # Auto-executes all tools except critically dangerous blocklist


CRITICAL_DANGEROUS_PATTERNS = [
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    ":(){ :|:& };:",
    "> /dev/sda",
    "dd if=",
    "chmod -R 777 /",
    "shutdown",
    "reboot",
]


class PermissionManager:
    """Evaluates whether a tool execution requires user confirmation."""

    def __init__(self, mode: PermissionMode = PermissionMode.ACCEPT_READ_ONLY):
        self.mode = mode

    def should_ask_confirmation(
        self,
        tool_name: str,
        is_destructive: bool,
        params: dict,
    ) -> tuple[bool, str | None]:
        """
        Determines if a confirmation is needed.
        Returns: (needs_confirmation: bool, reason: str | None)
        """
        # Autonomous mode check
        if self.mode == PermissionMode.AUTONOMOUS:
            # Check for critical dangerous bash commands
            if tool_name == "bash_executor":
                cmd = str(params.get("command", "")).strip()
                for pattern in CRITICAL_DANGEROUS_PATTERNS:
                    if pattern in cmd:
                        return True, f"Command contains potentially catastrophic pattern '{pattern}'"
            return False, None

        # Strict mode requires confirmation on any destructive or state-altering tool
        if self.mode == PermissionMode.STRICT:
            return True, f"Running tool '{tool_name}' in strict mode"

        # ACCEPT_READ_ONLY mode:
        if is_destructive:
            if tool_name == "bash_executor":
                cmd = str(params.get("command", "")).strip()
                return True, f"Execute bash command: `{cmd}`"
            elif tool_name in ("write_file", "edit_file"):
                path = params.get("path", "")
                return True, f"Modify file: `{path}`"
            return True, f"Execute destructive tool '{tool_name}'"

        return False, None
