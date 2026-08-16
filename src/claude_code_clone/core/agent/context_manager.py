"""Context management, token budget tracking, and history compaction."""

from claude_code_clone.core.agent.types import AgentMessage
from claude_code_clone.core.config.constants import DEFAULT_HISTORY_PRUNE_THRESHOLD
from claude_code_clone.core.config.settings import Settings
from claude_code_clone.utils.token_counter import estimate_tokens


class ContextManager:
    """Manages the conversation token budget and performs message compaction."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.max_tokens = settings.max_context_tokens
        self.threshold_tokens = int(self.max_tokens * DEFAULT_HISTORY_PRUNE_THRESHOLD)

    def estimate_history_tokens(self, messages: list[AgentMessage]) -> int:
        """Estimates total token usage for the given message list."""
        total = 0
        for msg in messages:
            if msg.content:
                total += estimate_tokens(msg.content)
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    total += estimate_tokens(str(tc.arguments)) + 20
        return total

    def prune_and_compact_if_needed(self, messages: list[AgentMessage]) -> list[AgentMessage]:
        """
        If message tokens exceed threshold, compacts older tool outputs and conversational turns
        while preserving the system prompt and the latest turns.
        """
        current_tokens = self.estimate_history_tokens(messages)
        if current_tokens <= self.threshold_tokens or len(messages) <= 4:
            return messages

        # Separate system prompt and conversation messages
        system_msgs = [m for m in messages if m.role == "system"]
        chat_msgs = [m for m in messages if m.role != "system"]

        # If we have many messages, preserve the last 6 messages and compact earlier ones
        keep_recent_count = min(6, len(chat_msgs))
        older_msgs = chat_msgs[:-keep_recent_count]
        recent_msgs = chat_msgs[-keep_recent_count:]

        # Truncate large tool outputs in older messages
        compacted_older: list[AgentMessage] = []
        for msg in older_msgs:
            if msg.role == "tool" and msg.content and len(msg.content) > 300:
                shortened = msg.content[:150] + "\n...[truncated past output for context efficiency]...\n" + msg.content[-150:]
                compacted_older.append(
                    AgentMessage(
                        role="tool",
                        content=shortened,
                        tool_call_id=msg.tool_call_id,
                        name=msg.name,
                    )
                )
            else:
                compacted_older.append(msg)

        compacted = system_msgs + compacted_older + recent_msgs
        return compacted

    def manual_compact(self, messages: list[AgentMessage], summary_text: str) -> list[AgentMessage]:
        """Replaces older history with a concise summary message."""
        system_msgs = [m for m in messages if m.role == "system"]
        keep_recent_count = min(4, len(messages))
        recent_msgs = messages[-keep_recent_count:]

        summary_msg = AgentMessage(
            role="user",
            content=f"[Summary of previous conversation context]\n{summary_text}",
        )

        return system_msgs + [summary_msg] + recent_msgs
