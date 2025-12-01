"""Shared utility functions for the autocorrect generator."""

import functools
import os
import re
from re import Pattern

from wordfreq import word_frequency as _word_frequency


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


@functools.lru_cache(maxsize=None)
def cached_word_frequency(word: str, lang: str = "en") -> float:
    """Cached wrapper for word_frequency to avoid repeated lookups.

    This function caches word frequency lookups to improve performance when
    the same words are looked up multiple times across different stages of
    the pipeline (e.g., collision resolution, typo filtering, QMK ranking).

    Args:
        word: The word to look up
        lang: Language code (default: "en")

    Returns:
        Word frequency as a float

    Note:
        The cache persists across the entire pipeline execution, providing
        significant performance improvements for large datasets with many
        repeated word lookups.
    """
    return _word_frequency(word, lang)
