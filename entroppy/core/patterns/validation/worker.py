"""Worker functions for parallel pattern validation."""

from dataclasses import dataclass
import threading

from entroppy.core.boundaries import BoundaryType
from entroppy.core.patterns.indexes import CorrectionIndex
from entroppy.core.patterns.validation.conflicts import (
    check_pattern_would_incorrectly_match_other_corrections,
)
from entroppy.core.patterns.validation.validator import (
    _check_target_word_corruption,
    _check_validation_word_conflicts,
    _find_example_word_with_substring,
    _format_error_with_example,
    validate_pattern_for_all_occurrences,
)
from entroppy.core.types import Correction, MatchDirection, PatternType


def _determine_pattern_type(typo_pattern: str, occurrences: list[Correction]) -> PatternType | None:
    """Determine if pattern is prefix, suffix, or substring from occurrences.

    Args:
        typo_pattern: The typo pattern
        occurrences: List of corrections that match this pattern

    Returns:
        PatternType.PREFIX if pattern appears at start of all typos,
        PatternType.SUFFIX if pattern appears at end of all typos,
        PatternType.SUBSTRING if pattern appears in middle (true substring),
        None if inconsistent
    """
    if not occurrences:
        return None

    all_start = True
    all_end = True

    for typo, _, _ in occurrences:
        starts_with = typo.startswith(typo_pattern)
        ends_with = typo.endswith(typo_pattern)

        if not starts_with:
            all_start = False
        if not ends_with:
            all_end = False

        # If pattern is in middle (not start and not end), it's a substring
        if not starts_with and not ends_with:
            return PatternType.SUBSTRING

    if all_start:
        return PatternType.PREFIX
    if all_end:
        return PatternType.SUFFIX
    return PatternType.SUBSTRING  # Mixed or inconsistent


def _get_pattern_boundary_order(
    natural_boundary: BoundaryType, pattern_type: PatternType | None
) -> list[BoundaryType]:
    """Get the order of boundaries to try for a pattern.

    Prefix patterns can only have LEFT boundaries.
    Suffix patterns can only have RIGHT boundaries.
    Patterns should NEVER have BOTH boundaries.
    If NONE fails for a true substring, reject it.

    Args:
        natural_boundary: The naturally determined boundary (should be NONE)
        pattern_type: PatternType indicating if pattern is prefix, suffix, or substring

    Returns:
        List of boundaries to try in order
    """
    # Always start with NONE
    if natural_boundary != BoundaryType.NONE:
        # Shouldn't happen, but handle it
        return [natural_boundary]

    if pattern_type == PatternType.PREFIX:
        # Prefix patterns: try NONE, then LEFT
        return [BoundaryType.NONE, BoundaryType.LEFT]
    if pattern_type == PatternType.SUFFIX:
        # Suffix patterns: try NONE, then RIGHT
        return [BoundaryType.NONE, BoundaryType.RIGHT]
    if pattern_type == PatternType.SUBSTRING:
        # True substring: only try NONE, reject if it fails
        return [BoundaryType.NONE]

    # Unknown pattern type: only try NONE
    return [BoundaryType.NONE]


# Thread-local storage for pattern validation worker context
_pattern_worker_context = threading.local()
_pattern_worker_indexes = threading.local()


@dataclass(frozen=True)
class PatternValidationContext:
    """Immutable context for pattern validation workers.

    Attributes:
        validation_set: Set of validation words
        source_words: Set of source words
        match_direction: Platform match direction
        min_typo_length: Minimum typo length
        debug_words: Set of words to debug
        corrections: All corrections for conflict checking
        would_corrupt_patterns: Pre-calculated set of patterns that would corrupt source words
        validation_checks: Pre-calculated validation checks dict: pattern -> {start, end, substring}
            Avoids passing expensive BoundaryIndex to workers
        correction_index: Pre-built correction index (lightweight - just stores list)
    """

    validation_set: frozenset[str]
    source_words: frozenset[str]
    match_direction: str  # MatchDirection enum value as string
    min_typo_length: int
    debug_words: frozenset[str]
    corrections: tuple[Correction, ...]  # Tuple for immutability
    would_corrupt_patterns: frozenset[str]  # Pre-calculated patterns that would corrupt
    validation_checks: dict[
        str, dict[str, bool]
    ]  # Pre-calculated validation checks: pattern -> {start, end, substring}
    correction_index: CorrectionIndex  # Pre-built in main process (lightweight - just a list)


def init_pattern_validation_worker(context: PatternValidationContext) -> None:
    """Initialize worker process with context (thin worker architecture).

    Thin worker: No expensive index building in workers.
    All expensive operations are pre-calculated in main process.

    Args:
        context: PatternValidationContext to store in thread-local storage
    """
    _pattern_worker_context.value = context

    # Thin worker: No expensive index building here
    # All validation checks are pre-calculated and passed in context.validation_checks
    _pattern_worker_indexes.correction_index = context.correction_index
    # BoundaryIndex not needed - we use pre-calculated validation_checks dict
    # Source word index not needed - we use pre-calculated would_corrupt_patterns set


def _check_basic_pattern_requirements(
    typo_pattern: str,
    occurrences: list[Correction],
    min_typo_length: int,
) -> tuple[bool, str | None]:
    """Check basic requirements for pattern acceptance.

    Args:
        typo_pattern: The typo pattern
        occurrences: List of occurrences
        min_typo_length: Minimum typo length

    Returns:
        Tuple of (is_valid, error_reason)
    """
    if len(occurrences) < 2:
        return False, None

    if len(typo_pattern) < min_typo_length:
        return False, f"Too short (< {min_typo_length})"

    return True, None


def _check_pattern_validation_and_conflicts(
    typo_pattern: str,
    word_pattern: str,
    boundary: BoundaryType,
    occurrences: list[Correction],
    context: PatternValidationContext,
    target_words: set[str],
) -> tuple[bool, str | None]:
    """Check pattern validation and conflicts.

    Args:
        typo_pattern: The typo pattern
        word_pattern: The word pattern
        boundary: The boundary type
        occurrences: List of occurrences
        context: Pattern validation context
        target_words: Set of target words

    Returns:
        Tuple of (is_safe, error_message)
    """
    # Validate that pattern works correctly for all occurrences
    is_valid, validation_error = validate_pattern_for_all_occurrences(
        typo_pattern, word_pattern, occurrences, boundary
    )
    if not is_valid:
        return False, validation_error or "Validation failed"

    # Check if pattern would corrupt source words (using pre-calculated set)
    if typo_pattern in context.would_corrupt_patterns:
        return False, "Would corrupt source words"

    # Use pre-calculated validation checks instead of passing BoundaryIndex
    # This avoids expensive pickle/unpickle of large BoundaryIndex objects
    validation_checks = context.validation_checks.get(typo_pattern, {})
    match_direction = MatchDirection(context.match_direction)

    is_safe, conflict_error = _check_pattern_conflicts_with_precalc(
        typo_pattern,
        set(context.validation_set),
        match_direction,
        boundary,
        target_words=target_words,
        validation_checks=validation_checks,
    )
    if not is_safe:
        return False, conflict_error or "Conflict detected"

    return True, None


def _validate_single_pattern_worker(
    pattern_data: tuple[
        tuple[str, str, BoundaryType], list[Correction]
    ],  # (pattern_key, occurrences)
) -> tuple[
    bool,  # is_accepted
    Correction | None,  # pattern if accepted, None if rejected
    list[Correction],  # corrections_to_remove
    tuple[str, str, BoundaryType, str] | None,  # rejected_pattern tuple if rejected
]:
    """Worker function to validate a single pattern.

    Args:
        pattern_data: Tuple of (pattern_key, occurrences) where pattern_key is
            (typo_pattern, word_pattern, boundary)

    Returns:
        Tuple of (is_accepted, pattern, corrections_to_remove, rejected_pattern)
    """
    (typo_pattern, word_pattern, boundary), occurrences = pattern_data
    context = _pattern_worker_context.value
    correction_index = _pattern_worker_indexes.correction_index

    # Empty list for corrections to remove (used when pattern is rejected)
    empty_corrections: list[Correction] = []

    # Check basic requirements
    is_valid, error_reason = _check_basic_pattern_requirements(
        typo_pattern, occurrences, context.min_typo_length
    )
    if not is_valid:
        # When error_reason is None (too few occurrences), return None for rejected_pattern
        # Otherwise, return tuple with error reason
        if error_reason:
            rejected_pattern: tuple[str, str, BoundaryType, str] | None = (
                typo_pattern,
                word_pattern,
                boundary,
                error_reason,
            )
        else:
            rejected_pattern = None
        return False, None, empty_corrections, rejected_pattern

    # Extract target words from occurrences
    target_words = {word for _, word, _ in occurrences}

    # Determine pattern type (prefix, suffix, or substring)
    pattern_type = _determine_pattern_type(typo_pattern, occurrences)

    # Try different boundaries based on pattern type
    # Prefix patterns can only have LEFT, suffix patterns can only have RIGHT
    # Patterns should NEVER have BOTH boundaries
    boundaries_to_try = _get_pattern_boundary_order(boundary, pattern_type)
    last_error_message: str | None = None

    for boundary_to_try in boundaries_to_try:
        # Check validation and conflicts with this boundary
        is_safe, error_message = _check_pattern_validation_and_conflicts(
            typo_pattern,
            word_pattern,
            boundary_to_try,
            occurrences,
            context,
            target_words,
        )
        if not is_safe:
            last_error_message = error_message or "Validation failed"
            continue  # Try next boundary

        # Check if pattern would incorrectly match other corrections
        is_safe, incorrect_match_error = check_pattern_would_incorrectly_match_other_corrections(
            typo_pattern,
            word_pattern,
            list(context.corrections),
            occurrences,
            correction_index=correction_index,
        )
        if not is_safe:
            last_error_message = incorrect_match_error or "Incorrect match"
            continue  # Try next boundary

        # Pattern passed all checks with this boundary - accept it
        pattern = (typo_pattern, word_pattern, boundary_to_try)
        corrections_to_remove = list(occurrences)
        return True, pattern, corrections_to_remove, None

    # All boundaries failed - reject pattern
    rejected_pattern_conflict: tuple[str, str, BoundaryType, str] = (
        typo_pattern,
        word_pattern,
        boundary,  # Return original boundary for reporting
        last_error_message or "Validation failed",
    )
    return (
        False,
        None,
        empty_corrections,
        rejected_pattern_conflict,
    )


def _check_end_boundary_conflict(
    typo_pattern: str,
    validation_set: set[str],
    boundary: BoundaryType,
    validation_checks: dict[str, bool],
) -> tuple[bool, str | None]:
    """Check if pattern would trigger at end of validation words.

    Args:
        typo_pattern: The typo pattern to check
        validation_set: Set of valid words
        boundary: The boundary type
        validation_checks: Pre-calculated dict with 'end' key

    Returns:
        Tuple of (is_safe, error_message)
    """
    if boundary in (BoundaryType.LEFT, BoundaryType.BOTH):
        return True, None

    would_trigger_end = validation_checks.get("end", False)
    if not would_trigger_end:
        return True, None

    # Find example word for error message
    example_word = None
    for word in validation_set:
        if word.endswith(typo_pattern) and word != typo_pattern:
            example_word = word
            break
    return _format_error_with_example(
        example_word,
        "Would trigger at end of validation words (e.g., '{example_word}')",
        "Would trigger at end of validation words",
    )


def _check_start_boundary_conflict(
    typo_pattern: str,
    validation_set: set[str],
    boundary: BoundaryType,
    validation_checks: dict[str, bool],
) -> tuple[bool, str | None]:
    """Check if pattern would trigger at start of validation words.

    Args:
        typo_pattern: The typo pattern to check
        validation_set: Set of valid words
        boundary: The boundary type
        validation_checks: Pre-calculated dict with 'start' key

    Returns:
        Tuple of (is_safe, error_message)
    """
    if boundary in (BoundaryType.RIGHT, BoundaryType.BOTH):
        return True, None

    would_trigger_start = validation_checks.get("start", False)
    if not would_trigger_start:
        return True, None

    # Find example word for error message
    example_word = None
    for word in validation_set:
        if word.startswith(typo_pattern) and word != typo_pattern:
            example_word = word
            break
    return _format_error_with_example(
        example_word,
        "Would trigger at start of validation words (e.g., '{example_word}')",
        "Would trigger at start of validation words",
    )


def _check_substring_conflict(
    typo_pattern: str,
    validation_set: set[str],
    boundary: BoundaryType,
    validation_checks: dict[str, bool],
) -> tuple[bool, str | None]:
    """Check if pattern appears as substring in validation words.

    Args:
        typo_pattern: The typo pattern to check
        validation_set: Set of valid words
        boundary: The boundary type
        validation_checks: Pre-calculated dict with 'substring' key

    Returns:
        Tuple of (is_safe, error_message)
    """
    if boundary != BoundaryType.NONE:
        return True, None

    is_substring = validation_checks.get("substring", False)
    if not is_substring:
        return True, None

    # Find example word for error message
    example_word = _find_example_word_with_substring(typo_pattern, validation_set)
    # pylint: disable=duplicate-code
    # Acceptable pattern: This is a function call to _format_error_with_example
    # with standard parameters. The similar code in validator.py calls the same
    # function with the same parameters. This is expected when both places need
    # to format the same error message.
    return _format_error_with_example(
        example_word,
        "Would falsely trigger on correctly spelled word '{example_word}'",
        "Would falsely trigger on correctly spelled words",
    )


def _check_pattern_conflicts_with_precalc(
    typo_pattern: str,
    validation_set: set[str],
    match_direction: MatchDirection,
    boundary: BoundaryType,
    target_words: set[str] | None,
    validation_checks: dict[str, bool],
) -> tuple[bool, str | None]:
    """Check pattern conflicts using pre-calculated validation checks.

    This avoids needing to pass the expensive BoundaryIndex to workers.

    Args:
        typo_pattern: The typo pattern to check
        validation_set: Set of valid words
        match_direction: The match direction
        boundary: The boundary type
        target_words: Optional set of target words
        validation_checks: Pre-calculated dict with keys: 'start', 'end', 'substring'

    Returns:
        Tuple of (is_safe, error_message)
    """
    # pylint: disable=duplicate-code
    # Acceptable pattern: Early-return validation pattern is common and intentional.
    # This function and check_pattern_conflicts in validator.py share the same validation
    # flow (check conflicts, check target words) but use different implementations
    # (pre-calculated checks vs BoundaryIndex). The early-return pattern is the standard
    # approach for validation functions and should not be refactored.

    # Check if pattern conflicts with validation words
    is_safe, error = _check_validation_word_conflicts(typo_pattern, validation_set)
    if not is_safe:
        return is_safe, error

    # Check boundary-specific conflicts
    is_safe, error = _check_end_boundary_conflict(
        typo_pattern, validation_set, boundary, validation_checks
    )
    if not is_safe:
        return is_safe, error

    is_safe, error = _check_start_boundary_conflict(
        typo_pattern, validation_set, boundary, validation_checks
    )
    if not is_safe:
        return is_safe, error

    is_safe, error = _check_substring_conflict(
        typo_pattern, validation_set, boundary, validation_checks
    )
    if not is_safe:
        return is_safe, error

    # Check if pattern would corrupt target words
    is_safe, error = _check_target_word_corruption(typo_pattern, target_words, match_direction)
    if not is_safe:
        return is_safe, error

    return True, None
