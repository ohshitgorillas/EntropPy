"""Helper functions for batch pattern validation."""

from typing import TYPE_CHECKING, Any

from loguru import logger

from entroppy.core.boundaries import BoundaryIndex, BoundaryType
from entroppy.core.patterns.logging import is_debug_pattern, process_rejected_pattern
from entroppy.core.patterns.validation.conflicts import check_pattern_redundant_with_other_patterns
from entroppy.core.types import Correction, MatchDirection
from entroppy.rust_ext import batch_check_patterns  # pylint: disable=no-name-in-module
from entroppy.utils.debug import is_debug_correction

if TYPE_CHECKING:
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
        )
        return True
    return False


def _remove_redundant_patterns_post_process(
    patterns: list[Correction],
    pattern_replacements: dict[Correction, list[Correction]],
    corrections_to_remove: set[Correction],
    rejected_patterns: list[tuple[str, str, BoundaryType, str]],
    debug_words: set[str],
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

    Returns:
        Tuple of (non_redundant_patterns, corrections_to_remove,
        non_redundant_replacements, rejected_patterns)
    """
    # Sort patterns by length (shorter first) to ensure we check shorter patterns first
    patterns_sorted = sorted(patterns, key=lambda p: len(p[0]))
    non_redundant_patterns: list[Correction] = []
    non_redundant_replacements: dict[Correction, list[Correction]] = {}
    debug_typo_matcher = None  # Not available in parallel mode, but needed for logging

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
        matches = suffix_index.find_substring_conflicts(pattern)
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


def _process_validation_results(
    results_iter: Any,
    patterns: list[Correction],
    pattern_replacements: dict[Correction, list[Correction]],
    corrections_to_remove: set[Correction],
    rejected_patterns: list[tuple[str, str, BoundaryType, str]],
) -> None:
    """Process validation results from parallel workers.

    Args:
        results_iter: Iterator over validation results
        patterns: List to append accepted patterns to
        pattern_replacements: Dict to store pattern replacements
        corrections_to_remove: Set to add corrections to remove to
        rejected_patterns: List to append rejected patterns to
    """
    for result in results_iter:
        (
            is_accepted,
            pattern_result,
            pattern_corrections_to_remove,
            rejected_pattern,
        ) = result

        if is_accepted and pattern_result:
            patterns.append(pattern_result)
            pattern_replacements[pattern_result] = pattern_corrections_to_remove
            for correction in pattern_corrections_to_remove:
                corrections_to_remove.add(correction)
        elif rejected_pattern:
            rejected_patterns.append(rejected_pattern)
