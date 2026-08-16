"""Universal LLM Gateway powered by LiteLLM with async streaming and robust tool calling."""

import json
import logging
from collections.abc import Callable
from typing import Any

import litellm
from litellm import acompletion, token_counter

from claude_code_clone.core.agent.types import (
    AgentMessage,
    AgentResponse,
    StreamChunk,
    ToolCall,
)
from claude_code_clone.core.config.settings import Settings
from claude_code_clone.core.providers.base import BaseLLMProvider
from claude_code_clone.core.providers.models import resolve_model_name

# Suppress overly verbose LiteLLM logs
litellm.suppress_debug_info = True
litellm.set_verbose = False
logging.getLogger("LiteLLM").setLevel(logging.WARNING)


class LiteLLMGateway(BaseLLMProvider):
    """Unified multi-provider LLM gateway supporting Anthropic, OpenAI, Gemini, Ollama, Bedrock, etc."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.load()
        self._configure_environment()

    def _configure_environment(self) -> None:
        """Sets API keys and custom base URLs in litellm config if present in settings."""
        if self.settings.anthropic_api_key:
            litellm.anthropic_key = self.settings.anthropic_api_key
        if self.settings.openai_api_key:
            litellm.openai_key = self.settings.openai_api_key
        if self.settings.gemini_api_key:
            litellm.gemini_key = self.settings.gemini_api_key
        if self.settings.openrouter_api_key:
            litellm.openrouter_key = self.settings.openrouter_api_key
        if self.settings.groq_api_key:
            litellm.groq_key = self.settings.groq_api_key
        if self.settings.openai_base_url:
            litellm.api_base = self.settings.openai_base_url

    def _format_messages_for_provider(
        self, messages: list[AgentMessage]
    ) -> list[dict[str, Any]]:
        """Converts AgentMessage objects to standard provider message dictionaries."""
        formatted: list[dict[str, Any]] = []
        for msg in messages:
            item: dict[str, Any] = {"role": msg.role}
            if msg.content is not None:
                item["content"] = msg.content
            if msg.tool_calls:
                item["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                            if isinstance(tc.arguments, dict)
                            else str(tc.arguments),
                        },
                    }
                    for tc in msg.tool_calls
                ]
            if msg.tool_call_id:
                item["tool_call_id"] = msg.tool_call_id
            if msg.name:
                item["name"] = msg.name
            formatted.append(item)
        return formatted

    async def stream_chat(
        self,
        messages: list[AgentMessage],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        on_chunk: Callable[[StreamChunk], None] | None = None,
    ) -> AgentResponse:
        """Streams chat completion from the selected provider, accumulating text and tool calls."""
        active_model = resolve_model_name(model or self.settings.model)
        formatted_messages = self._format_messages_for_provider(messages)

        kwargs: dict[str, Any] = {
            "model": active_model,
            "messages": formatted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or self.settings.max_tokens,
            "stream": True,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        # Accumulators
        full_content_chunks: list[str] = []
        tool_call_accumulators: dict[int, dict[str, Any]] = {}
        finish_reason: str | None = None
        prompt_tokens = 0
        completion_tokens = 0

        try:
            response_stream = await acompletion(**kwargs)
            async for chunk in response_stream:
                choices = getattr(chunk, "choices", [])
                if not choices:
                    continue

                choice = choices[0]
                delta = getattr(choice, "delta", None)
                if getattr(choice, "finish_reason", None):
                    finish_reason = choice.finish_reason

                delta_text = getattr(delta, "content", None) if delta else None
                tool_calls_delta = getattr(delta, "tool_calls", None) if delta else None

                if delta_text:
                    full_content_chunks.append(delta_text)

                if tool_calls_delta:
                    for tc_chunk in tool_calls_delta:
                        idx = getattr(tc_chunk, "index", 0)
                        if idx not in tool_call_accumulators:
                            tool_call_accumulators[idx] = {
                                "id": getattr(tc_chunk, "id", "") or f"call_{idx}",
                                "name": "",
                                "arguments": "",
                            }

                        if getattr(tc_chunk, "id", None):
                            tool_call_accumulators[idx]["id"] = tc_chunk.id

                        fn = getattr(tc_chunk, "function", None)
                        if fn:
                            if getattr(fn, "name", None):
                                tool_call_accumulators[idx]["name"] += fn.name
                            if getattr(fn, "arguments", None):
                                tool_call_accumulators[idx]["arguments"] += fn.arguments

                # Callback for real-time UI streaming
                if on_chunk:
                    stream_chunk = StreamChunk(
                        delta_content=delta_text,
                        finish_reason=finish_reason,
                    )
                    on_chunk(stream_chunk)

        except Exception as e:
            # Re-raise with informative context
            raise RuntimeError(
                f"LLM Provider error with model '{active_model}': {e}"
            ) from e

        # Finalize parsed tool calls
        final_tool_calls: list[ToolCall] = []
        for idx in sorted(tool_call_accumulators.keys()):
            tc_data = tool_call_accumulators[idx]
            raw_args = tc_data["arguments"].strip()
            parsed_args: dict[str, Any] = {}

            if raw_args:
                try:
                    parsed_args = json.loads(raw_args)
                except json.JSONDecodeError:
                    # Basic fallback for truncated or loosely formatted JSON arguments
                    try:
                        import ast

                        parsed_args = ast.literal_eval(raw_args)
                    except Exception:
                        parsed_args = {"raw_arguments": raw_args}

            if tc_data["name"]:
                final_tool_calls.append(
                    ToolCall(
                        id=tc_data["id"] or f"call_{idx}",
                        name=tc_data["name"],
                        arguments=parsed_args,
                    )
                )

        full_content = "".join(full_content_chunks)

        return AgentResponse(
            content=full_content,
            tool_calls=final_tool_calls,
            finish_reason=finish_reason,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )

    async def count_tokens(
        self, text_or_messages: str | list[AgentMessage], model: str | None = None
    ) -> int:
        """Estimates token count using LiteLLM token counter."""
        active_model = resolve_model_name(model or self.settings.model)
        try:
            if isinstance(text_or_messages, str):
                return token_counter(model=active_model, text=text_or_messages)
            else:
                formatted = self._format_messages_for_provider(text_or_messages)
                return token_counter(model=active_model, messages=formatted)
        except Exception:
            # Safe fallback: approximate 4 chars per token
            if isinstance(text_or_messages, str):
                return max(1, len(text_or_messages) // 4)
            total_chars = sum(len(m.content or "") for m in text_or_messages)
            return max(1, total_chars // 4)
