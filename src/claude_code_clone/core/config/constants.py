"""System constants and defaults for Claude Code Clone."""

from pathlib import Path

DEFAULT_MODEL = "anthropic/claude-3-7-sonnet-20250219"
FALLBACK_MODELS = [
    "anthropic/claude-3-5-sonnet-20241022",
    "openai/gpt-4o",
    "gemini/gemini-2.5-flash",
    "ollama/deepseek-r1:14b",
]

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_RAG_COLLECTION = "enterprise-docs"

# Context and token budget defaults
DEFAULT_MAX_CONTEXT_TOKENS = 128_000
DEFAULT_MAX_OUTPUT_TOKENS = 8_192
DEFAULT_HISTORY_PRUNE_THRESHOLD = 0.8  # Prune when 80% of max context is reached

# Local storage paths
GLOBAL_CONFIG_DIR = Path.home() / ".claude-code-clone"
GLOBAL_CONFIG_FILE = GLOBAL_CONFIG_DIR / "config.yaml"
LOCAL_AGENT_DIR = Path(".agent")
LOCAL_CONFIG_FILE = LOCAL_AGENT_DIR / "config.yaml"
LOCAL_RAG_DIR = LOCAL_AGENT_DIR / "rag_data"
GLOBAL_RAG_DIR = GLOBAL_CONFIG_DIR / "rag_data"
