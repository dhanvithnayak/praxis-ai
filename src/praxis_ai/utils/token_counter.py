"""Token counting utilities."""

import tiktoken


def estimate_tokens(text: str, model: str = "gpt-4o") -> int:
    """Estimates token count using tiktoken with fallback."""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        return max(1, len(text) // 4)
