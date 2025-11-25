"""Shared utility functions for the autocorrect generator."""

import re
from re import Pattern


def compile_wildcard_regex(pattern: str) -> Pattern:
    """Converts a simple wildcard pattern (* syntax) to a compiled regex object.

    e.g., 'in*' -> '^in.*$', '*in' -> '^.*in$', '*teh*' -> '^.*teh.*$'
    """
    parts = [re.escape(part) for part in pattern.split("*")]
    regex_str = ".*".join(parts)
    return re.compile(f"^{regex_str}$")
