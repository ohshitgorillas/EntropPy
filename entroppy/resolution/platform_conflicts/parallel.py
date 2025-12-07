"""Parallelization helpers for platform substring conflict detection.

This module contains worker functions and utilities for parallelizing
the conflict detection phase while maintaining correctness.
"""

from typing import TYPE_CHECKING

from entroppy.core.boundaries import BoundaryIndex, BoundaryType
from entroppy.core.types import MatchDirection
from entroppy.resolution.platform_conflicts import utils
from entroppy.resolution.platform_conflicts.utils import (
    build_index_keys_to_check,
    is_substring as _is_substring,
    process_conflict_combinations,
)

if TYPE_CHECKING:
    from entroppy.utils.debug import DebugTypoMatcher

# Type alias for conflict tuples
_ConflictTuple = tuple[
    str,  # formatted_typo
    list[tuple[tuple[str, str, BoundaryType], str, BoundaryType]],  # corrections_for_typo
    str,  # shorter_formatted_typo
    list[tuple[tuple[str, str, BoundaryType], str, BoundaryType]],  # shorter_corrections
]


def detect_conflicts_for_chunk(
    typos_chunk: list[tuple[str, list[tuple[tuple[str, str, BoundaryType], str, BoundaryType]]]],
    candidates_by_char: dict[
        str,
        list[tuple[str, list[tuple[tuple[str, str, BoundaryType], str, BoundaryType]]]],
    ],
) -> list[_ConflictTuple]:
    """Worker function to detect conflicts without modifying state (read-only).

    This function finds all substring conflicts in a chunk of typos by checking
    against the candidates_by_char index. It does not resolve conflicts or modify
    any shared state, making it safe for parallel execution.

    Args:
        typos_chunk: Chunk of (formatted_typo, corrections) tuples to check
        candidates_by_char: Character-based index of shorter typos (read-only)

    Returns:
        List of conflict tuples: (formatted_typo, corrections_for_typo,
        shorter_formatted_typo, shorter_corrections)
    """
    conflicts: list[_ConflictTuple] = []

    for formatted_typo, corrections_for_typo in typos_chunk:
        # Build index keys to check
        index_keys_to_check = build_index_keys_to_check(formatted_typo)

        # Find all substring conflicts using shared helper
        substring_conflicts = utils.find_substring_conflicts_in_index(
            formatted_typo,
            index_keys_to_check,
            candidates_by_char,
            _is_substring,
        )

        for shorter_formatted_typo, shorter_corrections in substring_conflicts:
            conflicts.append(
                (
                    formatted_typo,
                    corrections_for_typo,
                    shorter_formatted_typo,
                    shorter_corrections,
                )
            )

    return conflicts


def resolve_conflicts_sequential(
    all_conflicts: list[_ConflictTuple],
    match_direction: MatchDirection,
    processed_pairs: set[frozenset[tuple[str, str, BoundaryType]]],
    corrections_to_remove_set: set[tuple[str, str, BoundaryType]],
    validation_index: BoundaryIndex | None,
    source_index: BoundaryIndex | None,
    debug_words: set[str] | None,
    debug_typo_matcher: "DebugTypoMatcher | None",
) -> tuple[
    list[tuple[tuple[str, str, BoundaryType], str]],
    dict[tuple[str, str, BoundaryType], tuple[str, str, BoundaryType]],
]:
    """Resolve conflicts sequentially using deterministic rules.

    This function applies the same decision logic as the original algorithm,
    but processes all detected conflicts in a deterministic order to ensure
    consistent results.

    Args:
        all_conflicts: List of detected conflicts from parallel phase
        match_direction: Platform match direction
        processed_pairs: Set of already processed correction pairs (modified in-place)
        corrections_to_remove_set: Set of corrections already marked for removal (modified in-place)
        validation_index: Optional boundary index for validation set
        source_index: Optional boundary index for source words
        debug_words: Optional set of words to debug
        debug_typo_matcher: Optional matcher for debug typos

    Returns:
        Tuple of (corrections_to_remove, conflict_pairs)
    """
    corrections_to_remove: list[tuple[tuple[str, str, BoundaryType], str]] = []
    conflict_pairs: dict[tuple[str, str, BoundaryType], tuple[str, str, BoundaryType]] = {}

    # Sort conflicts deterministically to ensure consistent resolution order
    # Sort by formatted_typo, then shorter_formatted_typo for reproducibility
    sorted_conflicts = sorted(
        all_conflicts,
        key=lambda x: (x[0], x[2]),  # (formatted_typo, shorter_formatted_typo)
    )

    for (
        formatted_typo,
        corrections_for_typo,
        shorter_formatted_typo,
        shorter_corrections,
    ) in sorted_conflicts:
        # Process all combinations of corrections for this conflict
        # pylint: disable=duplicate-code
        # False positive: This is a call to the shared process_conflict_combinations
        # function. The similar code in detection.py is the same function call,
        # which is expected and not actual duplicate code.
        all_marked = process_conflict_combinations(
            shorter_corrections,
            corrections_for_typo,
            shorter_formatted_typo,
            formatted_typo,
            match_direction,
            processed_pairs,
            corrections_to_remove_set,
            corrections_to_remove,
            conflict_pairs,
            validation_index,
            source_index,
            debug_words,
            debug_typo_matcher,
        )
        if all_marked:
            continue

    return corrections_to_remove, conflict_pairs


def divide_into_chunks(
    items: list[tuple[str, list[tuple[tuple[str, str, BoundaryType], str, BoundaryType]]]],
    num_chunks: int,
) -> list[list[tuple[str, list[tuple[tuple[str, str, BoundaryType], str, BoundaryType]]]]]:
    """Divide a list into approximately equal chunks.

    Args:
        items: List of items to divide
        num_chunks: Number of chunks to create

    Returns:
        List of chunks
    """
    if num_chunks <= 1:
        return [items]

    chunk_size = max(1, len(items) // num_chunks)
    chunks = []
    for i in range(0, len(items), chunk_size):
        chunks.append(items[i : i + chunk_size])
    return chunks
