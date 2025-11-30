"""Utility functions for EntropPy."""

from entroppy.utils.constants import Constants
from entroppy.utils.debug import (
    DebugTypoMatcher,
    is_debug_correction,
    is_debug_word,
    is_debug_typo,
    log_debug_correction,
    log_debug_typo,
    log_debug_word,
    log_if_debug_correction,
)
from entroppy.utils.helpers import compile_wildcard_regex, expand_file_path
from entroppy.utils.logging import setup_logger

__all__ = [
    "Constants",
    "DebugTypoMatcher",
    "is_debug_correction",
    "is_debug_word",
    "is_debug_typo",
    "log_debug_correction",
    "log_debug_typo",
    "log_debug_word",
    "log_if_debug_correction",
    "compile_wildcard_regex",
    "expand_file_path",
    "setup_logger",
]
