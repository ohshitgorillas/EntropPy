"""Filtering functions for candidate selection."""

from entroppy.core import BoundaryType
from entroppy.matching import ExclusionMatcher


def _check_length_constraints(typo: str, word: str, min_typo_length: int) -> bool:
    """Check if typo/word meet length constraints.

    Args:
        typo: The typo string
        word: The correct word
        min_typo_length: Minimum typo length

    Returns:
        True if constraints are met
    """
    # If word is shorter than min_typo_length, typo must be at least min_typo_length
    # (This prevents very short typos for common words)
    if len(word) <= min_typo_length:
        return len(typo) >= min_typo_length
    return True


def _is_excluded(
    typo: str,
    word: str,
    boundary: BoundaryType,
    exclusion_matcher: ExclusionMatcher | None,
) -> bool:
    """Check if a correction is excluded by patterns.

    Args:
        typo: The typo string
        word: The correct word
        boundary: The boundary type
        exclusion_matcher: Optional exclusion matcher

    Returns:
        True if excluded
    """
    if not exclusion_matcher:
        return False

    correction = (typo, word, boundary)
    return exclusion_matcher.should_exclude(correction)
