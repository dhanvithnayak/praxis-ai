"""Diff computation and fuzzy block replacement utilities."""

import difflib


def compute_unified_diff(
    original: str,
    modified: str,
    from_file: str = "original",
    to_file: str = "modified",
) -> str:
    """Generates a standard unified diff string between original and modified text."""
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)
    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=from_file,
        tofile=to_file,
        lineterm="",
    )
    return "".join(diff)


def apply_block_replacement(
    content: str,
    target_content: str,
    replacement_content: str,
    allow_multiple: bool = False,
) -> tuple[str, int]:
    """
    Replaces target_content with replacement_content in content.
    Returns (new_content, replacement_count).
    Supports exact match first, then whitespace-tolerant fallback.
    """
    if not target_content:
        raise ValueError("Target content to replace cannot be empty.")

    # 1. Exact match
    count = content.count(target_content)
    if count > 0:
        if count > 1 and not allow_multiple:
            raise ValueError(
                f"Found {count} occurrences of target content. Set allow_multiple=True or provide a more specific unique block."
            )
        new_content = content.replace(target_content, replacement_content)
        return new_content, count

    # 2. Line-ending normalized match (\r\n vs \n)
    normalized_content = content.replace("\r\n", "\n")
    normalized_target = target_content.replace("\r\n", "\n")
    normalized_replacement = replacement_content.replace("\r\n", "\n")

    count = normalized_content.count(normalized_target)
    if count > 0:
        if count > 1 and not allow_multiple:
            raise ValueError(
                f"Found {count} occurrences of target content (normalized line endings). Provide a more specific unique block."
            )
        new_content = normalized_content.replace(
            normalized_target, normalized_replacement
        )
        return new_content, count

    # 3. Strip trailing whitespace per line match
    content_lines = normalized_content.splitlines()
    target_lines = normalized_target.splitlines()
    target_len = len(target_lines)

    if target_len <= len(content_lines):
        # Sliding window search comparing stripped lines
        matches = []
        target_stripped = [l.rstrip() for l in target_lines]
        for i in range(len(content_lines) - target_len + 1):
            window = [l.rstrip() for l in content_lines[i : i + target_len]]
            if window == target_stripped:
                matches.append(i)

        if len(matches) == 1 or (len(matches) > 1 and allow_multiple):
            new_lines = list(content_lines)
            rep_lines = normalized_replacement.splitlines()
            offset = 0
            for start_idx in matches:
                adjusted_idx = start_idx + offset
                new_lines[adjusted_idx : adjusted_idx + target_len] = rep_lines
                offset += len(rep_lines) - target_len
            return "\n".join(new_lines), len(matches)
        elif len(matches) > 1 and not allow_multiple:
            raise ValueError(
                f"Found {len(matches)} whitespace-tolerant occurrences of target content. Provide a more specific unique block."
            )

    raise ValueError(
        "Target content was not found in the file. Ensure the target block matches the exact existing code."
    )
