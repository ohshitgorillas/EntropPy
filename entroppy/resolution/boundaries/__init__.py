"""Boundary selection and utilities for resolution."""

from entroppy.resolution.boundaries.logging import (
    _log_boundary_order_selection,
    _log_boundary_rejection,
    _log_fallback_boundary,
    _log_left_boundary_rejection,
    _log_none_boundary_rejection,
    _log_right_boundary_rejection,
)
from entroppy.resolution.boundaries.selection import choose_boundary_for_typo
from entroppy.resolution.boundaries.utils import (
    _check_typo_in_target_word,
    _format_incorrect_transformation,
    _get_example_words_with_prefix,
    _get_example_words_with_substring,
    _get_example_words_with_suffix,
    _should_skip_short_typo,
    apply_user_word_boundary_override,
    choose_strictest_boundary,
)

__all__ = [
    "_check_typo_in_target_word",
    "_format_incorrect_transformation",
    "_get_example_words_with_prefix",
    "_get_example_words_with_substring",
    "_get_example_words_with_suffix",
    "_log_boundary_order_selection",
    "_log_boundary_rejection",
    "_log_fallback_boundary",
    "_log_left_boundary_rejection",
    "_log_none_boundary_rejection",
    "_log_right_boundary_rejection",
    "_should_skip_short_typo",
    "apply_user_word_boundary_override",
    "choose_boundary_for_typo",
    "choose_strictest_boundary",
]
