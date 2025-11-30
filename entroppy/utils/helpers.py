"""Shared utility functions for the autocorrect generator."""

import os
import re
from pathlib import Path
from re import Pattern


def compile_wildcard_regex(pattern: str) -> Pattern:
    """Converts a simple wildcard pattern (* syntax) to a compiled regex object.

    e.g., 'in*' -> '^in.*$', '*in' -> '^.*in$', '*teh*' -> '^.*teh.*$'
    """
    parts = [re.escape(part) for part in pattern.split("*")]
    regex_str = ".*".join(parts)
    return re.compile(f"^{regex_str}$")


def expand_file_path(filepath: str | None) -> str | None:
    """Expand user home directory in file path.

    This reduces code duplication by centralizing the os.path.expanduser() call.

    Args:
        filepath: File path (may contain ~)

    Returns:
        Expanded file path string, or None if filepath is None
    """
    if not filepath:
        return None
    return os.path.expanduser(filepath)
