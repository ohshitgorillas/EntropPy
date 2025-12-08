"""Helper functions for batch pattern validation."""

from typing import TYPE_CHECKING, Any

from loguru import logger

from entroppy.core.boundaries import BoundaryIndex, BoundaryType
from entroppy.core.patterns.data_collection import record_pattern_validation_accepted
from entroppy.core.patterns.logging import (
    is_debug_pattern,
    log_pattern_acceptance,
    log_pattern_replacements,
    process_rejected_pattern,
)
from entroppy.core.patterns.validation.conflicts import check_pattern_redundant_with_other_patterns
from entroppy.core.types import Correction, MatchDirection
from entroppy.rust_ext import batch_check_patterns  # pylint: disable=no-name-in-module
from entroppy.utils.debug import is_debug_correction

if TYPE_CHECKING:
    from entroppy.resolution.state import DictionaryState
    from entroppy.utils.debug import DebugTypoMatcher


def _handle_pattern_rejection(
    typo_pattern: str,
    word_pattern: str,
    boundary: BoundaryType,
    occurrences: list[Correction],
    error_message: str | None,
    is_debug_pattern_flag: bool,
    has_debug_occurrence: bool,
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
    rejected_patterns: list[tuple[str, str, BoundaryType, str]],
    state: "DictionaryState | None" = None,
) -> bool:
    """Handle pattern rejection.

    Args:
        typo_pattern: The typo pattern
        word_pattern: The word pattern
        boundary: The boundary type
        occurrences: List of occurrences
        error_message: Error message for rejection
        is_debug_pattern_flag: Whether this is a debug pattern
        has_debug_occurrence: Whether any occurrence is being debugged
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
        rejected_patterns: List to append rejected patterns to
        state: Optional dictionary state for storing structured debug data

    Returns:
        True if pattern should be skipped (rejected), False otherwise
    """
    reason = error_message or "Unknown error"
    if error_message == "Too few occurrences":
        return True  # Skip silently if already filtered
    process_rejected_pattern(
        typo_pattern,
        word_pattern,
        boundary,
        reason,
        occurrences,
        is_debug_pattern_flag,
        has_debug_occurrence,
        debug_words,
        debug_typo_matcher,
        rejected_patterns,
        state,
    )
    return True


def _handle_redundant_pattern(
    typo_pattern: str,
    word_pattern: str,
    boundary: BoundaryType,
    occurrences: list[Correction],
    patterns: list[Correction],
    is_debug_pattern_flag: bool,
    has_debug_occurrence: bool,
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
    rejected_patterns: list[tuple[str, str, BoundaryType, str]],
    state: "DictionaryState | None" = None,
) -> bool:
    """Check and handle redundant pattern.

    Args:
        typo_pattern: The typo pattern
        word_pattern: The word pattern
        boundary: The boundary type
        occurrences: List of occurrences
        patterns: List of already-accepted patterns
        is_debug_pattern_flag: Whether this is a debug pattern
        has_debug_occurrence: Whether any occurrence is being debugged
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
        rejected_patterns: List to append rejected patterns to
        state: Optional dictionary state for storing structured debug data

    Returns:
        True if pattern is redundant (should be skipped), False otherwise
    """
    is_redundant, redundancy_error, blocking_pattern = check_pattern_redundant_with_other_patterns(
        typo_pattern,
        word_pattern,
        boundary,
        patterns,
    )
    if is_redundant:
        reason = redundancy_error or "Redundant with shorter pattern"
        # Enhanced debug logging for redundancy rejection
        if is_debug_pattern_flag and blocking_pattern:
            blocking_typo, blocking_word, _ = blocking_pattern
            logger.debug(
                f"[PATTERN GENERALIZATION] Pattern '{typo_pattern}' → '{word_pattern}' "
                f"rejected as redundant: shorter pattern '{blocking_typo}' → '{blocking_word}' "
                f"already handles this case"
            )
        process_rejected_pattern(
            typo_pattern,
            word_pattern,
            boundary,
            reason,
            occurrences,
            is_debug_pattern_flag,
            has_debug_occurrence,
            debug_words,
            debug_typo_matcher,
            rejected_patterns,
            state,
        )
        return True
    return False


def _remove_redundant_patterns_post_process(
    patterns: list[Correction],
    pattern_replacements: dict[Correction, list[Correction]],
    corrections_to_remove: set[Correction],
    rejected_patterns: list[tuple[str, str, BoundaryType, str]],
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None" = None,
) -> tuple[
    list[Correction],
    set[Correction],
    dict[Correction, list[Correction]],
    list[tuple[str, str, BoundaryType, str]],
]:
    """Post-process parallel validation results to remove redundant patterns.

    Args:
        patterns: List of accepted patterns from parallel validation
        pattern_replacements: Dict mapping patterns to their replacement corrections
        corrections_to_remove: Set of corrections to remove
        rejected_patterns: List of rejected patterns
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos

    Returns:
        Tuple of (non_redundant_patterns, corrections_to_remove,
        non_redundant_replacements, rejected_patterns)
    """
    # Sort patterns by length (shorter first) to ensure we check shorter patterns first
    patterns_sorted = sorted(patterns, key=lambda p: len(p[0]))
    non_redundant_patterns: list[Correction] = []
    non_redundant_replacements: dict[Correction, list[Correction]] = {}

    for pattern in patterns_sorted:
        typo_pattern, word_pattern, boundary = pattern
        occurrences = pattern_replacements.get(pattern, [])
        has_debug_occurrence = any(
            is_debug_correction(occ, debug_words, debug_typo_matcher) for occ in occurrences
        )
        is_debug_pattern_flag = is_debug_pattern(typo_pattern, occurrences, debug_typo_matcher)

        # Check if this pattern is redundant with already-accepted patterns
        is_redundant, redundancy_error, blocking_pattern = (
            check_pattern_redundant_with_other_patterns(
                typo_pattern,
                word_pattern,
                boundary,
                non_redundant_patterns,
            )
        )
        if is_redundant:
            reason = redundancy_error or "Redundant with shorter pattern"
            # Enhanced debug logging for redundancy rejection
            if is_debug_pattern_flag and blocking_pattern:
                blocking_typo, blocking_word, _ = blocking_pattern
                logger.debug(
                    f"[PATTERN GENERALIZATION] Pattern '{typo_pattern}' → '{word_pattern}' "
                    f"rejected as redundant: shorter pattern '{blocking_typo}' → '{blocking_word}' "
                    f"already handles this case"
                )
            process_rejected_pattern(
                typo_pattern,
                word_pattern,
                boundary,
                reason,
                occurrences,
                is_debug_pattern_flag,
                has_debug_occurrence,
                debug_words,
                debug_typo_matcher,
                rejected_patterns,
            )
            # Remove corrections that would have been replaced by this redundant pattern
            for correction in occurrences:
                corrections_to_remove.discard(correction)
        else:
            non_redundant_patterns.append(pattern)
            non_redundant_replacements[pattern] = occurrences

    return (
        non_redundant_patterns,
        corrections_to_remove,
        non_redundant_replacements,
        rejected_patterns,
    )


def _precalculate_would_corrupt_patterns(
    all_patterns: list[str],
    source_words: set[str],
    match_direction: MatchDirection,
    verbose: bool,
) -> frozenset[str]:
    """Pre-calculate patterns that would corrupt source words.

    Args:
        all_patterns: List of all unique typo patterns
        source_words: Set of source words
        match_direction: Platform match direction
        verbose: Whether to print verbose output

    Returns:
        Frozen set of patterns that would corrupt source words
    """
    if verbose:
        logger.info("  Pre-calculating pattern corruption checks...")

    # Use Rust batch_check_patterns
    would_corrupt_results = batch_check_patterns(
        all_patterns,
        list(source_words),
        match_direction.value,
    )
    # Build set of patterns that would corrupt
    return frozenset(
        pattern
        for pattern, would_corrupt in zip(all_patterns, would_corrupt_results)
        if would_corrupt
    )


def _precalculate_validation_checks(
    all_patterns: list[str],
    validation_index: BoundaryIndex,
    verbose: bool,
) -> dict[str, dict[str, bool]]:
    """Pre-calculate validation checks for all patterns.

    Args:
        all_patterns: List of all unique typo patterns
        validation_index: Boundary index for validation set
        verbose: Whether to print verbose output

    Returns:
        Dictionary mapping pattern to validation checks dict with keys: 'start', 'end', 'substring'
    """
    if verbose:
        logger.info("  Pre-calculating validation checks...")

    # Batch check all patterns at once (much faster than individual calls)
    start_results = validation_index.batch_check_start(all_patterns)
    end_results = validation_index.batch_check_end(all_patterns)

    # Get substring checks using suffix array (O(log N) per query)
    suffix_index = validation_index.get_suffix_array_index()
    substring_results = {}
    for pattern in all_patterns:
        matches = suffix_index.find_conflicts(pattern)
        substring_results[pattern] = len(matches) > 0

    # Build validation_checks dict from batch results
    validation_checks: dict[str, dict[str, bool]] = {}
    for pattern in all_patterns:
        validation_checks[pattern] = {
            "start": start_results[pattern],
            "end": end_results[pattern],
            "substring": substring_results[pattern],
        }

    return validation_checks


def _log_accepted_pattern_debug(
    pattern_result: Correction,
    occurrences: list[Correction],
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
    state: "DictionaryState | None" = None,
) -> None:
    """Log debug information for an accepted pattern.

    Args:
        pattern_result: The accepted pattern (typo, word, boundary)
        occurrences: List of corrections being replaced by this pattern
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
        state: Optional dictionary state for storing structured debug data
    """
    typo_pattern, word_pattern, boundary = pattern_result
    has_debug_occurrence = any(
        is_debug_correction(occ, debug_words, debug_typo_matcher) for occ in occurrences
    )
    # Always call log_pattern_acceptance - it will check if pattern itself is debug item
    # pylint: disable=duplicate-code
    # This call pattern is intentionally similar to process_accepted_pattern in logging.py
    # Both functions need to log pattern acceptance with the same parameters.
    log_pattern_acceptance(
        typo_pattern,
        word_pattern,
        boundary,
        occurrences,
        has_debug_occurrence,
        debug_words,
        debug_typo_matcher,
    )
    # Log individual replacements for debug items
    log_pattern_replacements(
        typo_pattern, word_pattern, occurrences, debug_words, debug_typo_matcher
    )
    record_pattern_validation_accepted(typo_pattern, word_pattern, boundary, occurrences, state)


def _log_rejected_pattern_debug(
    rejected_pattern: tuple[str, str, BoundaryType, str],
    patterns_to_validate: dict[tuple[str, str, BoundaryType], list[Correction]],
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
    state: "DictionaryState | None" = None,
) -> None:
    """Log debug information for a rejected pattern.

    Args:
        rejected_pattern: The rejected pattern tuple (typo, word, boundary, reason)
        patterns_to_validate: Original patterns dict for looking up occurrences
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
        state: Optional dictionary state for storing structured debug data
    """
    typo_pattern, word_pattern, boundary, reason = rejected_pattern
    pattern_key = (typo_pattern, word_pattern, boundary)
    occurrences = patterns_to_validate.get(pattern_key, [])
    if occurrences:
        has_debug_occurrence = any(
            is_debug_correction(occ, debug_words, debug_typo_matcher) for occ in occurrences
        )
        is_debug_pattern_flag = is_debug_pattern(typo_pattern, occurrences, debug_typo_matcher)
        if is_debug_pattern_flag or has_debug_occurrence:
            process_rejected_pattern(
                typo_pattern,
                word_pattern,
                boundary,
                reason,
                occurrences,
                is_debug_pattern_flag,
                has_debug_occurrence,
                debug_words,
                debug_typo_matcher,
                [],  # Already added to rejected_patterns above
                state,
            )


def _handle_accepted_pattern(
    pattern_result: Correction,
    pattern_corrections_to_remove: list[Correction],
    patterns: list[Correction],
    pattern_replacements: dict[Correction, list[Correction]],
    corrections_to_remove: set[Correction],
    debug_words: set[str] | None,
    debug_typo_matcher: "DebugTypoMatcher | None",
    state: "DictionaryState | None" = None,
) -> None:
    """Handle an accepted pattern result.

    Args:
        pattern_result: The accepted pattern
        pattern_corrections_to_remove: Corrections to be replaced
        patterns: List to append accepted patterns to
        pattern_replacements: Dict to store pattern replacements
        corrections_to_remove: Set to add corrections to remove to
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
        state: Optional dictionary state for storing structured debug data
    """
    patterns.append(pattern_result)
    pattern_replacements[pattern_result] = pattern_corrections_to_remove
    for correction in pattern_corrections_to_remove:
        corrections_to_remove.add(correction)
    # Log accepted pattern if we have debug info
    # (always call - logging function will check if it's a debug item)
    if debug_words or debug_typo_matcher:
        _log_accepted_pattern_debug(
            pattern_result,
            pattern_corrections_to_remove,
            debug_words or set(),
            debug_typo_matcher,
            state,
        )


def _handle_rejected_pattern(
    rejected_pattern: tuple[str, str, BoundaryType, str],
    rejected_patterns: list[tuple[str, str, BoundaryType, str]],
    patterns_to_validate: dict[tuple[str, str, BoundaryType], list[Correction]] | None,
    debug_words: set[str] | None,
    debug_typo_matcher: "DebugTypoMatcher | None",
    state: "DictionaryState | None" = None,
) -> None:
    """Handle a rejected pattern result.

    Args:
        rejected_pattern: The rejected pattern tuple
        rejected_patterns: List to append rejected patterns to
        patterns_to_validate: Original patterns dict for debug logging
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
        state: Optional dictionary state for storing structured debug data
    """
    rejected_patterns.append(rejected_pattern)
    # Log rejected pattern if it matches debug criteria
    if patterns_to_validate and debug_typo_matcher:
        _log_rejected_pattern_debug(
            rejected_pattern,
            patterns_to_validate,
            debug_words or set(),
            debug_typo_matcher,
            state,
        )


def _process_validation_results(
    results_iter: Any,
    patterns: list[Correction],
    pattern_replacements: dict[Correction, list[Correction]],
    corrections_to_remove: set[Correction],
    rejected_patterns: list[tuple[str, str, BoundaryType, str]],
    patterns_to_validate: dict[tuple[str, str, BoundaryType], list[Correction]] | None = None,
    debug_words: set[str] | None = None,
    debug_typo_matcher: "DebugTypoMatcher | None" = None,
    state: "DictionaryState | None" = None,
) -> None:
    """Process validation results from parallel workers.

    Args:
        results_iter: Iterator over validation results
        patterns: List to append accepted patterns to
        pattern_replacements: Dict to store pattern replacements
        corrections_to_remove: Set to add corrections to remove to
        rejected_patterns: List to append rejected patterns to
        patterns_to_validate: Original patterns dict (for looking up occurrences
            of rejected patterns)
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
        state: Optional dictionary state for storing structured debug data
    """
    for result in results_iter:
        (
            is_accepted,
            pattern_result,
            pattern_corrections_to_remove,
            rejected_pattern,
        ) = result

        if is_accepted and pattern_result:
            _handle_accepted_pattern(
                pattern_result,
                pattern_corrections_to_remove,
                patterns,
                pattern_replacements,
                corrections_to_remove,
                debug_words,
                debug_typo_matcher,
                state,
            )
        elif rejected_pattern:
            _handle_rejected_pattern(
                rejected_pattern,
                rejected_patterns,
                patterns_to_validate,
                debug_words,
                debug_typo_matcher,
                state,
            )
