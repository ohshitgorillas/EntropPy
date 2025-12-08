"""Filtering functions for pattern extraction."""

from collections import defaultdict
from typing import TYPE_CHECKING

from loguru import logger

from entroppy.core.boundaries import BoundaryType
from entroppy.core.patterns.data_collection import record_pattern_extraction
from entroppy.core.types import Correction

if TYPE_CHECKING:
    from entroppy.resolution.state import DictionaryState

# Minimum length for the non-pattern part when extracting patterns
# This prevents extracting nonsensical patterns that are too short
_MIN_OTHER_PART_LENGTH = 2


def _filter_corrections_by_boundary(
    corrections: list[Correction],
    boundary_type: BoundaryType,
) -> list[Correction]:
    """Filter corrections by boundary type.

    For suffix patterns (RIGHT), include RIGHT, BOTH, and NONE boundaries.
    BOTH is included because it includes RIGHT (matches at word end).
    For prefix patterns (LEFT), include LEFT, BOTH, and NONE boundaries.
    BOTH is included because it includes LEFT (matches at word start).

    Args:
        corrections: List of corrections to filter
        boundary_type: Boundary type to filter by

    Returns:
        Filtered list of corrections
    """
    if boundary_type == BoundaryType.RIGHT:
        # For suffix patterns, include RIGHT, BOTH (includes RIGHT), and NONE
        allowed: tuple[BoundaryType, ...] = (
            BoundaryType.RIGHT,
            BoundaryType.BOTH,
            BoundaryType.NONE,
        )
    elif boundary_type == BoundaryType.LEFT:
        # For prefix patterns, include LEFT, BOTH (includes LEFT), and NONE
        allowed = (BoundaryType.LEFT, BoundaryType.BOTH, BoundaryType.NONE)
    else:
        # Fallback to original behavior for other boundary types
        allowed = (boundary_type, BoundaryType.NONE)

    return [(typo, word, boundary) for typo, word, boundary in corrections if boundary in allowed]


def _check_exact_and_wildcard_patterns(
    typo_lower: str,
    exact_patterns: set[str],
    wildcard_patterns: set[str],
) -> bool:
    """Check if typo matches exact or wildcard patterns."""
    # Check exact patterns (exact match)
    if any(typo_lower == pattern.lower() for pattern in exact_patterns):
        return True
    # Check wildcard patterns (substring match)
    if any(pattern.lower() in typo_lower for pattern in wildcard_patterns):
        return True
    return False


def _setup_debug_tracking_new_params(
    filtered_corrections: list[Correction],
    exact_patterns: set[str],
    wildcard_patterns: set[str],
) -> dict[tuple[str, str, BoundaryType], list[tuple[int, str, str, str]]]:
    """Setup debug tracking using new exact/wildcard pattern parameters."""
    debug_corrections: dict[tuple[str, str, BoundaryType], list[tuple[int, str, str, str]]] = {}

    for typo, word, boundary in filtered_corrections:
        typo_lower = typo.lower()
        if _check_exact_and_wildcard_patterns(typo_lower, exact_patterns, wildcard_patterns):
            debug_corrections[(typo, word, boundary)] = []

    return debug_corrections


def _setup_debug_tracking_legacy(
    filtered_corrections: list[Correction],
    debug_typos: set[str],
) -> dict[tuple[str, str, BoundaryType], list[tuple[int, str, str, str]]]:
    """Setup debug tracking using legacy substring matching."""
    debug_corrections: dict[tuple[str, str, BoundaryType], list[tuple[int, str, str, str]]] = {}

    for typo, word, boundary in filtered_corrections:
        if any(debug_typo.lower() in typo.lower() for debug_typo in debug_typos):
            debug_corrections[(typo, word, boundary)] = []

    return debug_corrections


def _setup_debug_tracking(
    filtered_corrections: list[Correction],
    debug_typos: set[str] | None,
    debug_typos_exact: set[str] | None = None,
    debug_typos_wildcard: set[str] | None = None,
) -> dict[tuple[str, str, BoundaryType], list[tuple[int, str, str, str]]]:
    """Setup debug tracking for specific typos.

    Args:
        filtered_corrections: List of corrections to track
        debug_typos: Optional set of typo strings to debug (backward compatibility)
        debug_typos_exact: Optional set of exact debug typo patterns
            (for exact matching)
        debug_typos_wildcard: Optional set of wildcard debug typo pattern cores
            (for substring matching)

    Returns:
        Dict mapping (typo, word, boundary) to list of debug info
    """
    # Use new parameters if provided, otherwise fall back to old behavior for backward compatibility
    if debug_typos_exact is not None or debug_typos_wildcard is not None:
        exact_patterns = debug_typos_exact or set()
        wildcard_patterns = debug_typos_wildcard or set()
        return _setup_debug_tracking_new_params(
            filtered_corrections, exact_patterns, wildcard_patterns
        )

    if debug_typos is not None and len(debug_typos) > 0:
        return _setup_debug_tracking_legacy(filtered_corrections, debug_typos)

    return {}


def _check_exact_pattern_match(
    typo_pattern_lower: str,
    unique_matches: list[tuple[str, str, BoundaryType]],
    exact_patterns: set[str],
) -> bool:
    """Check if typo pattern or matches match exact patterns."""
    return any(
        typo_pattern_lower == pattern.lower()
        or any(pattern.lower() == m[0].lower() for m in unique_matches)
        for pattern in exact_patterns
    )


def _check_wildcard_pattern_match(
    typo_pattern_lower: str,
    unique_matches: list[tuple[str, str, BoundaryType]],
    wildcard_patterns: set[str],
) -> bool:
    """Check if typo pattern or matches match wildcard patterns."""
    return any(
        pattern.lower() in typo_pattern_lower
        or any(pattern.lower() in m[0].lower() for m in unique_matches)
        for pattern in wildcard_patterns
    )


def _check_legacy_pattern_match(
    typo_pattern_lower: str,
    unique_matches: list[tuple[str, str, BoundaryType]],
    debug_typos: set[str],
) -> bool:
    """Check if typo pattern or matches match legacy debug typos."""
    return any(
        debug_typo.lower() in typo_pattern_lower
        or any(debug_typo.lower() in m[0].lower() for m in unique_matches)
        for debug_typo in debug_typos
    )


def _should_log_pattern(
    typo_pattern: str,
    unique_matches: list[tuple[str, str, BoundaryType]],
    debug_typos: set[str] | None,
    debug_typos_exact: set[str] | None,
    debug_typos_wildcard: set[str] | None,
) -> bool:
    """Determine if a pattern should be logged for debugging.

    Args:
        typo_pattern: The typo pattern
        unique_matches: List of unique matches for this pattern
        debug_typos: Optional set of typo strings to debug (backward compatibility)
        debug_typos_exact: Optional set of exact debug typo patterns
        debug_typos_wildcard: Optional set of wildcard debug typo pattern cores

    Returns:
        True if pattern should be logged
    """
    # Use new parameters if provided
    if debug_typos_exact is not None or debug_typos_wildcard is not None:
        exact_patterns = debug_typos_exact or set()
        wildcard_patterns = debug_typos_wildcard or set()
        typo_pattern_lower = typo_pattern.lower()

        if _check_exact_pattern_match(typo_pattern_lower, unique_matches, exact_patterns):
            return True
        if _check_wildcard_pattern_match(typo_pattern_lower, unique_matches, wildcard_patterns):
            return True
        return False

    # Backward compatibility: use substring matching for all patterns
    if debug_typos is not None:
        typo_pattern_lower = typo_pattern.lower()
        return _check_legacy_pattern_match(typo_pattern_lower, unique_matches, debug_typos)

    return False


def _log_pattern_found(
    typo_pattern: str,
    word_pattern: str,
    boundary: BoundaryType,
    unique_matches: list[tuple[str, str, BoundaryType]],
) -> None:
    """Log a found pattern for debugging.

    Args:
        typo_pattern: The typo pattern
        word_pattern: The word pattern
        boundary: The boundary type
        unique_matches: List of unique matches for this pattern
    """
    # Generate log message
    logger.debug(
        f"[PATTERN EXTRACTION] ✓ PATTERN FOUND: "
        f"'{typo_pattern}' → '{word_pattern}' "
        f"(boundary={boundary.value}, {len(unique_matches)} occurrences)"
    )
    for typo, word, orig_boundary in unique_matches:
        logger.debug(f"  - '{typo}' → '{word}' (boundary={orig_boundary.value})")


def _find_common_patterns(
    pattern_candidates: dict[tuple[str, str, BoundaryType], list[tuple[str, str, BoundaryType]]],
    debug_typos: set[str] | None,
    debug_enabled: bool,
    debug_typos_exact: set[str] | None = None,
    debug_typos_wildcard: set[str] | None = None,
    state: "DictionaryState | None" = None,
) -> dict[tuple[str, str, BoundaryType], list[tuple[str, str, BoundaryType]]]:
    """Find patterns that have 2+ occurrences.

    Args:
        pattern_candidates: Dict of pattern candidates with their matches
        debug_typos: Optional set of typo strings to debug (backward compatibility)
        debug_enabled: Whether debug logging is enabled
        debug_typos_exact: Optional set of exact debug typo patterns
            (for exact matching)
        debug_typos_wildcard: Optional set of wildcard debug typo pattern cores
            (for substring matching)
        state: Optional dictionary state for storing structured debug data

    Returns:
        Dict mapping (typo_pattern, word_pattern, boundary) to list of
        (full_typo, full_word, original_boundary) tuples
    """
    patterns: dict[tuple[str, str, BoundaryType], list[tuple[str, str, BoundaryType]]] = (
        defaultdict(list)
    )

    # Add all patterns that have 2+ occurrences
    # Deduplicate matches since same correction might match pattern at different lengths
    for pattern_key, matches in pattern_candidates.items():
        if len(matches) >= 2:
            # Deduplicate: convert to set and back to list to remove duplicates
            unique_matches = list(dict.fromkeys(matches))  # Preserves order, removes duplicates
            if len(unique_matches) >= 2:
                patterns[pattern_key].extend(unique_matches)
                typo_pattern, word_pattern, boundary = pattern_key
                if debug_enabled:
                    if _should_log_pattern(
                        typo_pattern,
                        unique_matches,
                        debug_typos,
                        debug_typos_exact,
                        debug_typos_wildcard,
                    ):
                        _log_pattern_found(typo_pattern, word_pattern, boundary, unique_matches)
                        # Record structured data separately from logging
                        record_pattern_extraction(
                            typo_pattern, word_pattern, boundary, unique_matches, state
                        )

    return patterns
