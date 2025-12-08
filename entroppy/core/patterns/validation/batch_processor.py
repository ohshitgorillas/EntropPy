"""Batch processing for pattern validation."""

from multiprocessing import Pool
from typing import TYPE_CHECKING, Any

from loguru import logger
from tqdm import tqdm

from entroppy.core.boundaries import BoundaryIndex, BoundaryType
from entroppy.core.patterns.indexes import CorrectionIndex, ValidationIndexes
from entroppy.core.patterns.logging import (
    is_debug_pattern,
    log_pattern_candidate,
    process_accepted_pattern,
)
from entroppy.core.patterns.validation.batch_processor_helpers import (
    _handle_pattern_rejection,
    _handle_redundant_pattern,
    _precalculate_validation_checks,
    _precalculate_would_corrupt_patterns,
    _process_validation_results,
    _remove_redundant_patterns_post_process,
)
from entroppy.core.patterns.validation.conflicts import (
    check_pattern_would_incorrectly_match_other_corrections,
)
from entroppy.core.patterns.validation.validator import (
    check_pattern_conflicts,
    validate_pattern_for_all_occurrences,
)
from entroppy.core.patterns.validation.worker import (
    PatternValidationContext,
    _validate_single_pattern_worker,
    init_pattern_validation_worker,
)
from entroppy.core.types import Correction, MatchDirection
from entroppy.utils.debug import is_debug_correction

if TYPE_CHECKING:
    from entroppy.resolution.state import DictionaryState
    from entroppy.utils.debug import DebugTypoMatcher


def _check_pattern_occurrence_count(
    typo_pattern: str,
    word_pattern: str,
    occurrences: list[Correction],
    debug_typo_matcher: "DebugTypoMatcher | None",
    verbose: bool,
) -> tuple[bool, str | None]:
    """Check if pattern has sufficient occurrences."""
    if len(occurrences) < 2:
        if verbose and debug_typo_matcher:
            if is_debug_pattern(typo_pattern, occurrences, debug_typo_matcher):
                logger.debug(
                    f"[PATTERN GENERALIZATION] Skipping pattern "
                    f"'{typo_pattern}' → '{word_pattern}': "
                    f"only {len(occurrences)} occurrence (need 2+)"
                )
        return False, "Too few occurrences"
    return True, None


def _check_pattern_length(typo_pattern: str, min_typo_length: int) -> tuple[bool, str | None]:
    """Check if pattern meets minimum length requirement."""
    if len(typo_pattern) < min_typo_length:
        return False, f"Too short (< {min_typo_length})"
    return True, None


def _validate_single_pattern_single_threaded(
    typo_pattern: str,
    word_pattern: str,
    boundary: BoundaryType,
    occurrences: list[Correction],
    min_typo_length: int,
    validation_set: set[str],
    source_words: set[str],
    match_direction: MatchDirection,
    corrections: list[Correction],
    indexes: ValidationIndexes,
    debug_typo_matcher: "DebugTypoMatcher | None",
    verbose: bool,
) -> tuple[bool, str | None]:
    """Validate a single pattern in single-threaded mode.

    Args:
        typo_pattern: The typo pattern to validate
        word_pattern: The word pattern
        boundary: The boundary type
        occurrences: List of occurrences for this pattern
        min_typo_length: Minimum typo length
        validation_set: Set of valid words
        source_words: Set of source words
        match_direction: Platform match direction
        corrections: All corrections to check against
        indexes: Validation indexes
        debug_typo_matcher: Matcher for debug typos
        verbose: Whether to print verbose output
        state: Optional dictionary state for storing structured debug data

    Returns:
        Tuple of (is_valid, error_message). is_valid is True if pattern passes,
        False otherwise. error_message is None if valid, otherwise contains reason.
    """
    # Skip patterns with only one occurrence (already filtered, but keep for safety)
    is_valid, error = _check_pattern_occurrence_count(
        typo_pattern, word_pattern, occurrences, debug_typo_matcher, verbose
    )
    if not is_valid:
        return is_valid, error

    # Reject patterns that are too short
    is_valid, error = _check_pattern_length(typo_pattern, min_typo_length)
    if not is_valid:
        return is_valid, error

    # Validate that pattern works correctly for all occurrences
    is_valid, validation_error = validate_pattern_for_all_occurrences(
        typo_pattern, word_pattern, occurrences, boundary
    )
    if not is_valid:
        return False, validation_error or "Validation failed"

    # Extract target words from occurrences (prevents predictive corrections)
    target_words = {word for _, word, _ in occurrences}

    # Check for conflicts with validation words or source/target words
    is_safe, conflict_error = check_pattern_conflicts(
        typo_pattern,
        validation_set,
        source_words,
        match_direction,
        indexes.validation_index,
        boundary,
        indexes.source_word_index,
        target_words=target_words,
    )
    if not is_safe:
        return False, conflict_error or "Conflict detected"

    # Check if pattern would incorrectly match other corrections
    is_safe, incorrect_match_error = check_pattern_would_incorrectly_match_other_corrections(
        typo_pattern,
        word_pattern,
        corrections,
        occurrences,
        correction_index=indexes.correction_index,
    )
    if not is_safe:
        return False, incorrect_match_error or "Incorrect match"

    return True, None


def run_single_threaded_validation(
    patterns_to_validate: dict[tuple[str, str, BoundaryType], list[Correction]],
    min_typo_length: int,
    validation_set: set[str],
    source_words: set[str],
    match_direction: MatchDirection,
    corrections: list[Correction],
    indexes: ValidationIndexes,
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
    verbose: bool,
    state: "DictionaryState | None" = None,
) -> tuple[
    list[Correction],
    set[Correction],
    dict[Correction, list[Correction]],
    list[tuple[str, str, BoundaryType, str]],
]:
    """Run pattern validation in single-threaded mode.

    Args:
        patterns_to_validate: Dictionary of patterns to validate
        min_typo_length: Minimum typo length
        validation_set: Set of valid words
        source_words: Set of source words
        match_direction: Platform match direction
        corrections: All corrections to check against
        indexes: Validation indexes
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
        verbose: Whether to print verbose output
        state: Optional dictionary state for storing structured debug data

    Returns:
        Tuple of (patterns, corrections_to_remove, pattern_replacements, rejected_patterns)
    """
    patterns: list[Correction] = []
    corrections_to_remove: set[Correction] = set()
    pattern_replacements: dict[Correction, list[Correction]] = {}
    rejected_patterns: list[tuple[str, str, BoundaryType, str]] = []

    if verbose:
        patterns_iter: list[tuple[tuple[str, str, BoundaryType], list[Correction]]] = list(
            tqdm(
                patterns_to_validate.items(),
                desc="    Validating patterns",
                unit="pattern",
                leave=False,
            )
        )
    else:
        patterns_iter = list(patterns_to_validate.items())

    _process_patterns_single_threaded(
        patterns_iter,
        min_typo_length,
        validation_set,
        source_words,
        match_direction,
        corrections,
        indexes,
        debug_words,
        debug_typo_matcher,
        patterns,
        pattern_replacements,
        corrections_to_remove,
        rejected_patterns,
        state,
    )

    return patterns, corrections_to_remove, pattern_replacements, rejected_patterns


def _process_patterns_single_threaded(
    patterns_iter: list[tuple[tuple[str, str, BoundaryType], list[Correction]]],
    min_typo_length: int,
    validation_set: set[str],
    source_words: set[str],
    match_direction: MatchDirection,
    corrections: list[Correction],
    indexes: ValidationIndexes,
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
    patterns: list[Correction],
    pattern_replacements: dict[Correction, list[Correction]],
    corrections_to_remove: set[Correction],
    rejected_patterns: list[tuple[str, str, BoundaryType, str]],
    state: "DictionaryState | None" = None,
) -> None:
    """Process patterns in single-threaded validation loop.

    Args:
        patterns_iter: Iterator over patterns to validate
        min_typo_length: Minimum typo length
        validation_set: Set of valid words
        source_words: Set of source words
        match_direction: Platform match direction
        corrections: All corrections to check against
        indexes: Validation indexes
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
        patterns: List to append accepted patterns to
        pattern_replacements: Dict to store pattern replacements
        corrections_to_remove: Set to add corrections to remove to
        rejected_patterns: List to append rejected patterns to
        state: Optional dictionary state for storing structured debug data
    """
    for (typo_pattern, word_pattern, boundary), occurrences in patterns_iter:
        # Check if any of the occurrences involve debug items (for logging)
        has_debug_occurrence = any(
            is_debug_correction(occ, debug_words, debug_typo_matcher) for occ in occurrences
        )

        # Debug logging for pattern candidates
        is_debug_pattern_flag = is_debug_pattern(typo_pattern, occurrences, debug_typo_matcher)
        # Only log if this pattern wasn't already filtered by graveyard check
        # (patterns_to_validate should already be filtered, but log anyway for debugging)
        log_pattern_candidate(typo_pattern, word_pattern, occurrences, debug_typo_matcher)

        # Validate the pattern
        # pylint: disable=duplicate-code
        # False positive: Similar parameter lists are expected when calling the same function
        # from different contexts (orchestration vs validation runner). This is not duplicate
        # code that should be refactored - it's the same function call with the same parameters.
        is_valid, error_message = _validate_single_pattern_single_threaded(
            typo_pattern,
            word_pattern,
            boundary,
            occurrences,
            min_typo_length,
            validation_set,
            source_words,
            match_direction,
            corrections,
            indexes,
            debug_typo_matcher,
            False,  # verbose not needed in loop
        )

        if not is_valid:
            if _handle_pattern_rejection(
                typo_pattern,
                word_pattern,
                boundary,
                occurrences,
                error_message,
                is_debug_pattern_flag,
                has_debug_occurrence,
                debug_words,
                debug_typo_matcher,
                rejected_patterns,
                state,
            ):
                continue

        # Check if pattern is redundant with already-accepted patterns
        if _handle_redundant_pattern(
            typo_pattern,
            word_pattern,
            boundary,
            occurrences,
            patterns,
            is_debug_pattern_flag,
            has_debug_occurrence,
            debug_words,
            debug_typo_matcher,
            rejected_patterns,
            state,
        ):
            continue

        # Pattern passed all checks - accept it
        # pylint: disable=duplicate-code
        # False positive: Similar parameter lists are intentional - we pass parameters
        # from processing code to logging functions, which is the correct design pattern
        # for separating processing logic from debug logging.
        process_accepted_pattern(
            typo_pattern,
            word_pattern,
            boundary,
            occurrences,
            has_debug_occurrence,
            debug_words,
            debug_typo_matcher,
            patterns,
            pattern_replacements,
            corrections_to_remove,
            state,
        )


def run_parallel_validation(
    patterns_to_validate: dict[tuple[str, str, BoundaryType], list[Correction]],
    validation_set: set[str],
    source_words: set[str],
    match_direction: MatchDirection,
    min_typo_length: int,
    debug_words: set[str],
    corrections: list[Correction],
    jobs: int,
    verbose: bool,
    debug_typo_matcher: "DebugTypoMatcher | None" = None,
    state: "DictionaryState | None" = None,
) -> tuple[
    list[Correction],
    set[Correction],
    dict[Correction, list[Correction]],
    list[tuple[str, str, BoundaryType, str]],
]:
    """Run pattern validation in parallel mode.

    Args:
        patterns_to_validate: Dictionary of patterns to validate
        validation_set: Set of valid words
        source_words: Set of source words
        match_direction: Platform match direction
        min_typo_length: Minimum typo length
        debug_words: Set of words to debug
        corrections: All corrections to check against
        jobs: Number of parallel workers
        verbose: Whether to print verbose output
        debug_typo_matcher: Optional matcher for debug typos
        state: Optional dictionary state for storing structured debug data

    Returns:
        Tuple of (patterns, corrections_to_remove, pattern_replacements, rejected_patterns)
    """
    patterns: list[Correction] = []
    corrections_to_remove: set[Correction] = set()
    pattern_replacements: dict[Correction, list[Correction]] = {}
    rejected_patterns: list[tuple[str, str, BoundaryType, str]] = []

    if verbose:
        logger.info(f"  Using {jobs} parallel workers for pattern validation")

    # Pre-build indexes once in main process (not in workers)
    if verbose:
        logger.info("  Pre-building validation indexes...")
    validation_index = BoundaryIndex(validation_set)
    correction_index = CorrectionIndex(corrections)  # Lightweight - just stores list

    # Extract all unique typo patterns
    all_patterns = list({typo_pattern for (typo_pattern, _, _) in patterns_to_validate.keys()})

    # Pre-calculate would_corrupt checks using Rust batch function (releases GIL, parallelized)
    would_corrupt_patterns = _precalculate_would_corrupt_patterns(
        all_patterns, source_words, match_direction, verbose
    )

    # Pre-calculate validation checks to avoid passing expensive BoundaryIndex to workers
    validation_checks = _precalculate_validation_checks(all_patterns, validation_index, verbose)

    # Create context for workers with pre-calculated data
    # NOTE: We do NOT pass validation_index to avoid expensive pickle/unpickle
    context = PatternValidationContext(
        validation_set=frozenset(validation_set),
        source_words=frozenset(source_words),
        match_direction=match_direction.value,
        min_typo_length=min_typo_length,
        debug_words=frozenset(debug_words),
        corrections=tuple(corrections),
        would_corrupt_patterns=would_corrupt_patterns,
        validation_checks=validation_checks,
        correction_index=correction_index,
    )

    if verbose:
        logger.info("  Initializing workers (thin worker architecture - no index building)...")

    with Pool(
        processes=jobs,
        initializer=init_pattern_validation_worker,
        initargs=(context,),
    ) as pool:
        pattern_items = list(patterns_to_validate.items())
        results_iter = pool.imap_unordered(_validate_single_pattern_worker, pattern_items)

        # Wrap with progress bar if verbose
        if verbose:
            results_wrapped: Any = tqdm(
                results_iter,
                total=len(pattern_items),
                desc="    Validating patterns",
                unit="pattern",
                leave=False,
            )
        else:
            results_wrapped = results_iter

        _process_validation_results(
            results_wrapped,
            patterns=patterns,
            pattern_replacements=pattern_replacements,
            corrections_to_remove=corrections_to_remove,
            rejected_patterns=rejected_patterns,
            patterns_to_validate=patterns_to_validate,
            debug_words=debug_words,
            debug_typo_matcher=debug_typo_matcher,
            state=state,
        )

    # Post-process to remove redundant patterns (parallel validation can't check during validation)
    result = _remove_redundant_patterns_post_process(
        patterns,
        pattern_replacements,
        corrections_to_remove,
        rejected_patterns,
        debug_words,
        debug_typo_matcher,
    )
    return result[0], result[1], result[2], result[3]
