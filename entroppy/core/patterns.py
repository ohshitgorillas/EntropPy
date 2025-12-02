"""Pattern generalization for typo corrections."""

from typing import TYPE_CHECKING

from entroppy.core.pattern_validation_runner import (
    _build_validation_indexes,
    _extract_and_merge_patterns,
    _extract_debug_typos,
    _run_parallel_validation,
    _run_single_threaded_validation,
)
from entroppy.core.types import Correction
from entroppy.platforms.base import MatchDirection

if TYPE_CHECKING:
    from entroppy.utils.debug import DebugTypoMatcher


def generalize_patterns(
    corrections: list[Correction],
    validation_set: set[str],
    source_words: set[str],
    min_typo_length: int,
    match_direction: MatchDirection,
    verbose: bool = False,
    debug_words: set[str] | None = None,
    debug_typo_matcher: "DebugTypoMatcher | None" = None,
    jobs: int = 1,
) -> tuple[
    list[Correction],
    set[Correction],
    dict[Correction, list[Correction]],
    list[tuple[str, str, str]],
]:
    """Find repeated patterns, create generalized rules, and return corrections to be removed.

    Args:
        corrections: List of corrections to analyze
        validation_set: Set of valid words
        source_words: Set of source words
        min_typo_length: Minimum typo length
        match_direction: Platform match direction
        verbose: Whether to print verbose output
        debug_words: Set of words to debug (exact matches)
        debug_typo_matcher: Matcher for debug typos (with wildcards/boundaries)
        jobs: Number of parallel workers to use (1 = sequential)

    Returns:
        Tuple of (patterns, corrections_to_remove, pattern_replacements, rejected_patterns)
    """
    if debug_words is None:
        debug_words = set()

    # Build validation indexes
    indexes = _build_validation_indexes(validation_set, source_words, match_direction, corrections)

    # Extract debug typos for pattern extraction logging
    debug_typos_set = _extract_debug_typos(debug_typo_matcher)

    # Extract and merge prefix/suffix patterns
    found_patterns = _extract_and_merge_patterns(corrections, debug_typos_set, verbose)

    # Filter out patterns with only one occurrence before validation
    patterns_to_validate = {k: v for k, v in found_patterns.items() if len(v) >= 2}

    # Choose parallel or single-threaded validation
    if jobs > 1 and len(patterns_to_validate) > 10:
        return _run_parallel_validation(
            patterns_to_validate,
            validation_set,
            source_words,
            match_direction,
            min_typo_length,
            debug_words,
            corrections,
            jobs,
            verbose,
        )
    # pylint: disable=duplicate-code
    # False positive: Similar parameter lists are expected when calling the same function
    # from different contexts (orchestration vs validation runner). This is not duplicate
    # code that should be refactored - it's the same function call with the same parameters.
    return _run_single_threaded_validation(
        patterns_to_validate,
        min_typo_length,
        validation_set,
        source_words,
        match_direction,
        corrections,
        indexes,
        debug_words,
        debug_typo_matcher,
        verbose,
    )
