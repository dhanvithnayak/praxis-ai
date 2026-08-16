"""Universal LLM Gateway powered by LiteLLM with async streaming and robust tool calling."""

import json
import logging
import re
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

        # Route Ollama models to ollama_chat for native chat & tool support in LiteLLM
        litellm_model = active_model
        if litellm_model.startswith("ollama/") and not litellm_model.startswith("ollama_chat/"):
            litellm_model = litellm_model.replace("ollama/", "ollama_chat/", 1)

        formatted_messages = self._format_messages_for_provider(messages)

        kwargs: dict[str, Any] = {
            "model": litellm_model,
            "messages": formatted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or self.settings.max_tokens,
            "stream": True,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        if (
            litellm_model.startswith("ollama/")
            or litellm_model.startswith("ollama_chat/")
        ) and self.settings.ollama_base_url:
            kwargs["api_base"] = self.settings.ollama_base_url

        # Accumulators
        full_content_chunks: list[str] = []
        tool_call_accumulators: dict[int, dict[str, Any]] = {}
        finish_reason: str | None = None
        prompt_tokens = 0
        completion_tokens = 0

        # Stream filter to suppress raw tool call streaming
        class _StreamFilter:
            def __init__(self, callback: Callable[[StreamChunk], None] | None):
                self.callback = callback
                self.normal_buffer: list[str] = []
                self.tool_buffer: list[str] = []
                self.in_potential_tool = False

            def feed(self, delta: str | None, fr: str | None) -> None:
                if not self.callback or not delta:
                    return

                if self.in_potential_tool:
                    self.tool_buffer.append(delta)
                    return

                self.normal_buffer.append(delta)
                current = "".join(self.normal_buffer)

                triggers = (
                    "```json",
                    "```",
                    "<tool_call>",
                    "<tool",
                    '{"name":',
                    '{"tool":',
                    '{"action":',
                    '{"function":',
                )
                for trigger in triggers:
                    if trigger in current:
                        idx = current.index(trigger)
                        pre = current[:idx]
                        tool_part = current[idx:]
                        if pre:
                            self.callback(
                                StreamChunk(delta_content=pre, finish_reason=None)
                            )
                        self.normal_buffer.clear()
                        self.tool_buffer = [tool_part]
                        self.in_potential_tool = True
                        return

                if len(current) > 30 and not any(
                    trigger.startswith(current[-15:]) for trigger in triggers
                ):
                    self.callback(
                        StreamChunk(delta_content=current, finish_reason=None)
                    )
                    self.normal_buffer.clear()

            def finalize(
                self,
                had_tool_calls: bool,
                final_text: str = "",
                finish_reason: str | None = None,
            ) -> None:
                if not self.callback:
                    return
                if self.normal_buffer:
                    self.callback(
                        StreamChunk(
                            delta_content="".join(self.normal_buffer),
                            finish_reason=finish_reason if not had_tool_calls else None,
                        )
                    )
                    self.normal_buffer.clear()

                if self.tool_buffer:
                    if not had_tool_calls:
                        to_flush = final_text if final_text else "".join(self.tool_buffer)
                        self.callback(
                            StreamChunk(
                                delta_content=to_flush,
                                finish_reason=finish_reason,
                            )
                        )
                    self.tool_buffer.clear()

        stream_filter = _StreamFilter(on_chunk)

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
                    stream_filter.feed(delta_text, finish_reason)

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

        # Fallback tool call extraction from text content (e.g. for Ollama models or text-formatted JSON tool calls)
        if not final_tool_calls and full_content.strip():
            valid_tool_names = None
            if tools:
                valid_tool_names = {
                    t.get("function", {}).get("name")
                    for t in tools
                    if isinstance(t, dict) and "function" in t
                }
            fallback_calls, cleaned_content = self._extract_fallback_tool_calls(
                full_content, valid_tool_names=valid_tool_names
            )
            if fallback_calls:
                final_tool_calls = fallback_calls
                full_content = cleaned_content
                if not finish_reason or finish_reason == "stop":
                    finish_reason = "tool_calls"
            else:
                # Unwrap conversational JSON containers (e.g. {"response": "..."})
                full_content = self._unwrap_json_response(full_content)

        # Finalize stream callback (suppress tool call JSON or flush clean text)
        stream_filter.finalize(
            had_tool_calls=bool(final_tool_calls),
            final_text=full_content,
            finish_reason=finish_reason,
        )

        return AgentResponse(
            content=full_content,
            tool_calls=final_tool_calls,
            finish_reason=finish_reason,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )

    @staticmethod
    def _unwrap_json_response(content: str) -> str:
        """
        Unwraps conversational text if the model returned its final answer inside a
        JSON container like `{"response": "..."}`, `{"answer": "..."}`, `{"message": "..."}`.
        """
        trimmed = content.strip()
        if not trimmed:
            return content

        code_block = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", trimmed)
        raw = code_block.group(1).strip() if code_block else trimmed

        if raw.startswith("{") and raw.endswith("}"):
            try:
                data = json.loads(raw)
                if isinstance(data, dict):
                    for key in (
                        "response",
                        "answer",
                        "message",
                        "content",
                        "text",
                        "output",
                        "final_answer",
                    ):
                        if (
                            key in data
                            and isinstance(data[key], str)
                            and data[key].strip()
                        ):
                            return data[key].strip()
            except Exception:
                pass
        return content

    @staticmethod
    def _extract_fallback_tool_calls(
        content: str, valid_tool_names: set[str] | None = None
    ) -> tuple[list[ToolCall], str]:
        """
        Parses tool calls from raw text content for local or non-compliant models
        that output JSON, markdown code blocks, or XML tags instead of delta tool_calls.
        """
        if not content or not content.strip():
            return [], content

        tool_calls: list[ToolCall] = []

        def _normalize_tool_dict(d: Any, idx: Any) -> ToolCall | None:
            if not isinstance(d, dict):
                return None
            name = (
                d.get("name")
                or d.get("tool")
                or d.get("tool_name")
                or d.get("action")
                or d.get("function")
            )
            if not name or not isinstance(name, str):
                return None
            name = name.strip()
            if valid_tool_names and name not in valid_tool_names:
                return None
            raw_args = (
                d.get("arguments")
                if "arguments" in d
                else (
                    d.get("parameters")
                    if "parameters" in d
                    else (
                        d.get("input")
                        if "input" in d
                        else (
                            d.get("action_input")
                            if "action_input" in d
                            else d.get("args", {})
                        )
                    )
                )
            )
            if isinstance(raw_args, str):
                try:
                    raw_args = json.loads(raw_args)
                except Exception:
                    try:
                        import ast

                        raw_args = ast.literal_eval(raw_args)
                    except Exception:
                        raw_args = {"raw_arguments": raw_args}
            elif not isinstance(raw_args, dict):
                raw_args = {}
            call_id = d.get("id") or f"call_text_{idx}"
            return ToolCall(id=str(call_id), name=name, arguments=raw_args)

        # 1. XML-style: <tool_call>...</tool_call>
        xml_matches = re.findall(r"<tool_call>(.*?)</tool_call>", content, re.DOTALL)
        if xml_matches:
            for idx, m in enumerate(xml_matches):
                try:
                    data = json.loads(m.strip())
                    tc = _normalize_tool_dict(data, idx)
                    if tc:
                        tool_calls.append(tc)
                except Exception:
                    pass
            if tool_calls:
                cleaned = re.sub(
                    r"<tool_call>.*?</tool_call>", "", content, flags=re.DOTALL
                ).strip()
                return tool_calls, cleaned

        # 2. Markdown code fences: ```json\n{...}\n```
        code_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if code_blocks:
            for idx, block in enumerate(code_blocks):
                try:
                    data = json.loads(block.strip())
                    if isinstance(data, list):
                        for j, item in enumerate(data):
                            tc = _normalize_tool_dict(item, f"{idx}_{j}")
                            if tc:
                                tool_calls.append(tc)
                    elif isinstance(data, dict):
                        tc = _normalize_tool_dict(data, idx)
                        if tc:
                            tool_calls.append(tc)
                except Exception:
                    pass
            if tool_calls:
                cleaned = re.sub(r"```(?:json)?\s*[\s\S]*?\s*```", "", content).strip()
                return tool_calls, cleaned

        # 3. Entire content is a JSON object or JSON list
        trimmed = content.strip()
        try:
            data = json.loads(trimmed)
            if isinstance(data, dict):
                tc = _normalize_tool_dict(data, 0)
                if tc:
                    return [tc], ""
            elif isinstance(data, list):
                for idx, item in enumerate(data):
                    tc = _normalize_tool_dict(item, idx)
                    if tc:
                        tool_calls.append(tc)
                if tool_calls:
                    return tool_calls, ""
        except Exception:
            pass

        # 4. Inline JSON substring search
        for idx, match in enumerate(
            re.finditer(r"(\{(?:[^{}]|(?:\{[^{}]*\}))*\})", content)
        ):
            try:
                data = json.loads(match.group(1))
                tc = _normalize_tool_dict(data, idx)
                if tc:
                    tool_calls.append(tc)
            except Exception:
                pass

        if tool_calls:
            cleaned = content
            for tc in tool_calls:
                cleaned = re.sub(
                    rf'\{{[^{{}}]*"{tc.name}"[^{{}}]*\}}', "", cleaned
                ).strip()
            return tool_calls, cleaned

        return [], content

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
