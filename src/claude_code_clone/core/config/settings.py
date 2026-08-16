"""Configuration management using Pydantic Settings."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from claude_code_clone.core.config.constants import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_MAX_CONTEXT_TOKENS,
    DEFAULT_MODEL,
    GLOBAL_CONFIG_FILE,
    LOCAL_CONFIG_FILE,
)


class Settings(BaseSettings):
    """Global and workspace settings for Claude Code Clone."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="",
    )

    # Active LLM Model & Provider
    model: str = Field(
        default=DEFAULT_MODEL,
        description="Active LLM model (e.g. anthropic/claude-3-7-sonnet-20250219, openai/gpt-4o, gemini/gemini-2.5-flash, ollama/deepseek-r1:14b)",
    )
    temperature: float = Field(default=0.0, description="Sampling temperature")
    max_tokens: int = Field(default=8192, description="Max generation tokens")
    max_context_tokens: int = Field(
        default=DEFAULT_MAX_CONTEXT_TOKENS, description="Max total context token budget"
    )

    # API Keys & Custom Base URLs
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    mistral_api_key: str | None = Field(default=None, alias="MISTRAL_API_KEY")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    ollama_base_url: str = Field(
        default="http://localhost:11434", alias="OLLAMA_BASE_URL"
    )

    # Permission level: 'strict', 'accept_read_only', 'autonomous'
    permission_mode: str = Field(
        default="accept_read_only", description="Safety permission mode"
    )

    # RAG Settings
    rag_enabled: bool = Field(
        default=True, description="Whether RAG tool is available to the agent"
    )
    rag_embedding_model: str = Field(
        default=DEFAULT_EMBEDDING_MODEL,
        description="FastEmbed or OpenAI embedding model",
    )
    rag_storage_path: str | None = Field(
        default=None, description="Custom path for LanceDB vector storage"
    )
    rag_top_k: int = Field(
        default=5, description="Number of context chunks to retrieve"
    )

    # Workspace
    workspace_dir: str = Field(
        default_factory=lambda: str(Path.cwd()),
        description="Active root directory of the workspace",
    )

    @classmethod
    def load(cls) -> "Settings":
        """Loads configuration merging defaults, global YAML, local YAML, and environment variables."""
        config_data: dict[str, Any] = {}

        # 1. Load global config (~/.claude-code-clone/config.yaml)
        if GLOBAL_CONFIG_FILE.exists():
            try:
                with open(GLOBAL_CONFIG_FILE, encoding="utf-8") as f:
                    content = yaml.safe_load(f)
                    if isinstance(content, dict):
                        config_data.update(content)
            except Exception:
                pass

        # 2. Load workspace config (.agent/config.yaml)
        if LOCAL_CONFIG_FILE.exists():
            try:
                with open(LOCAL_CONFIG_FILE, encoding="utf-8") as f:
                    content = yaml.safe_load(f)
                    if isinstance(content, dict):
                        config_data.update(content)
            except Exception:
                pass

        # 3. Instantiate settings (env vars take highest priority via pydantic_settings)
        return cls(**config_data)

    def save_global(self) -> None:
        """Saves current settings to the global user configuration file."""
        GLOBAL_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        dump_data = self.model_dump(
            exclude={
                "anthropic_api_key",
                "openai_api_key",
                "gemini_api_key",
                "openrouter_api_key",
            }
        )
        with open(GLOBAL_CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.safe_dump(dump_data, f)
