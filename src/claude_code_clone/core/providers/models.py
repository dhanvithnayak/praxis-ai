"""Model metadata, aliases, and provider mappings."""

MODEL_ALIASES: dict[str, str] = {
    # Anthropic
    "claude-3-7-sonnet": "anthropic/claude-3-7-sonnet-20250219",
    "claude-3-5-sonnet": "anthropic/claude-3-5-sonnet-20241022",
    "claude-3-5-haiku": "anthropic/claude-3-5-haiku-20241022",
    "sonnet": "anthropic/claude-3-7-sonnet-20250219",
    "haiku": "anthropic/claude-3-5-haiku-20241022",
    # OpenAI
    "gpt-4o": "openai/gpt-4o",
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "o3-mini": "openai/o3-mini",
    "o1": "openai/o1",
    # Google Gemini
    "gemini-flash": "gemini/gemini-2.5-flash",
    "gemini-pro": "gemini/gemini-2.0-pro-exp-02-05",
    "gemini-2.5-flash": "gemini/gemini-2.5-flash",
    "gemini-2.0-flash": "gemini/gemini-2.0-flash",
    # Local / Ollama
    "deepseek-r1": "ollama/deepseek-r1:14b",
    "deepseek-v3": "ollama/deepseek-v3",
    "qwen-coder": "ollama/qwen2.5-coder:14b",
    "llama3.3": "ollama/llama3.3",
    # Cloud & Gateways
    "groq-llama3": "groq/llama-3.3-70b-versatile",
    "mistral-large": "mistral/mistral-large-latest",
}


def resolve_model_name(model_name_or_alias: str) -> str:
    """Resolves shortcuts or aliases to the full LiteLLM provider model identifier."""
    cleaned = model_name_or_alias.strip().lower()
    return MODEL_ALIASES.get(cleaned, model_name_or_alias.strip())
