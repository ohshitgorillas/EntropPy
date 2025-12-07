"""Helper functions for candidate selection."""

from collections import defaultdict

from entroppy.core import BoundaryType


def group_words_by_boundary(
    unique_words: list[str],
    boundary: BoundaryType,
) -> dict[BoundaryType, list[str]]:
    """Group words by boundary type.

    This helper function extracts the common pattern of creating a word_boundary_map
    and grouping words by boundary type.

    Args:
        unique_words: List of unique words
        boundary: The boundary type for all words (in candidate selection, all words
            for the same typo have the same boundary)

    Returns:
        Dictionary mapping boundary type to list of words with that boundary
    """
    # All words for the same typo will have the same boundary
    word_boundary_map = {word: boundary for word in unique_words}

    # Group words by boundary type
    by_boundary = defaultdict(list)
    for word, word_boundary in word_boundary_map.items():
        by_boundary[word_boundary].append(word)

    return by_boundary


def _get_boundary_order(natural_boundary: BoundaryType) -> list[BoundaryType]:
    """Get the order of boundaries to try, starting with the natural one.

    This implements self-healing: if a less strict boundary fails,
    we automatically try stricter ones in subsequent iterations.

    Args:
        natural_boundary: The naturally determined boundary

    Returns:
        List of boundaries to try in order
    """
    # Order: try natural first, then stricter alternatives
    if natural_boundary == BoundaryType.NONE:
        # NONE is least strict - try all others if it fails
        return [
            BoundaryType.NONE,
            BoundaryType.LEFT,
            BoundaryType.RIGHT,
            BoundaryType.BOTH,
        ]
    if natural_boundary == BoundaryType.LEFT:
        return [BoundaryType.LEFT, BoundaryType.BOTH]
    if natural_boundary == BoundaryType.RIGHT:
        return [BoundaryType.RIGHT, BoundaryType.BOTH]
    # BOTH is most strict - only try it
    return [BoundaryType.BOTH]
