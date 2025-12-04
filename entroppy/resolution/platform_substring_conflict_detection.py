"""Platform substring conflict detection logic.

This module contains the core detection algorithms for finding cross-boundary
substring conflicts in platform-formatted typo strings.
"""

from collections import defaultdict
from typing import TYPE_CHECKING

from entroppy.core.boundaries import BoundaryType
from entroppy.core.types import MatchDirection

if TYPE_CHECKING:
    pass

# Boundary priority mapping: more restrictive boundaries have higher priority
# Used to determine which correction to keep when resolving conflicts
BOUNDARY_PRIORITY = {
    BoundaryType.NONE: 0,
    BoundaryType.LEFT: 1,
    BoundaryType.RIGHT: 1,
    BoundaryType.BOTH: 2,
}


def is_substring(shorter: str, longer: str) -> bool:
    """Check if shorter is a substring of longer.

    Optimized with fast paths for prefix and suffix checks, which are
    common cases (especially for QMK where boundaries create prefixes).

    Args:
        shorter: The shorter string
        longer: The longer string

    Returns:
        True if shorter is a substring of longer
    """
    if not shorter or not longer or shorter == longer:
        return False

    # Fast path: prefix check (common for QMK, e.g., "aemr" in ":aemr")
    if longer.startswith(shorter):
        return True

    # Fast path: suffix check
    if longer.endswith(shorter):
        return True

    # Fallback: middle substring (less common)
    return shorter in longer


def should_remove_shorter(
    match_direction: MatchDirection,
    shorter_word: str,
    longer_word: str,
    shorter_boundary: BoundaryType,
    longer_boundary: BoundaryType,
) -> bool:
    """Determine if the shorter formatted typo should be removed.

    Args:
        match_direction: Platform match direction
        shorter_word: Word for shorter typo
        longer_word: Word for longer typo
        shorter_boundary: Boundary type for shorter typo
        longer_boundary: Boundary type for longer typo

    Returns:
        True if shorter should be removed, False if longer should be removed
    """
    # If they map to the same word, prefer the more restrictive boundary
    # (keeps the one that's less likely to cause false triggers)
    if shorter_word == longer_word:
        shorter_priority = BOUNDARY_PRIORITY.get(shorter_boundary, 0)
        longer_priority = BOUNDARY_PRIORITY.get(longer_boundary, 0)

        if longer_priority > shorter_priority:
            return True  # Remove shorter (less restrictive)
        return False  # Remove longer (less restrictive)

    # For RTL (QMK): QMK's compiler rejects ANY substring relationship
    # We prefer to keep the more restrictive boundary
    # (longer formatted usually means more restrictive)
    if match_direction == MatchDirection.RIGHT_TO_LEFT:
        # Keep longer (more restrictive), remove shorter
        return True  # Remove shorter

    # For LTR (Espanso): shorter would match first, so longer never triggers
    # But boundaries are handled separately in YAML, so this is less critical
    # Still, prefer more restrictive boundary
    shorter_priority = BOUNDARY_PRIORITY.get(shorter_boundary, 0)
    longer_priority = BOUNDARY_PRIORITY.get(longer_boundary, 0)

    if longer_priority > shorter_priority:
        return True  # Remove shorter (less restrictive)
    return False  # Remove longer (less restrictive)


def build_length_buckets(
    formatted_to_corrections: dict[
        str, list[tuple[tuple[str, str, BoundaryType], str, BoundaryType]]
    ],
) -> dict[int, list[tuple[str, list[tuple[tuple[str, str, BoundaryType], str, BoundaryType]]]]]:
    """Group formatted typos by length into buckets.

    Args:
        formatted_to_corrections: Dict mapping formatted_typo ->
            list of (correction, typo, boundary)

    Returns:
        Dict mapping length -> list of (formatted_typo, corrections) tuples
    """
    length_buckets: dict[
        int, list[tuple[str, list[tuple[tuple[str, str, BoundaryType], str, BoundaryType]]]]
    ] = defaultdict(list)

    for formatted_typo, corrections in formatted_to_corrections.items():
        length_buckets[len(formatted_typo)].append((formatted_typo, corrections))

    return length_buckets


def process_conflict_pair(
    correction1: tuple[str, str, BoundaryType],
    correction2: tuple[str, str, BoundaryType],
    shorter_formatted_typo: str,
    formatted_typo: str,
    boundary1: BoundaryType,
    boundary2: BoundaryType,
    match_direction: MatchDirection,
    processed_pairs: set[frozenset[tuple[str, str, BoundaryType]]],
    corrections_to_remove_set: set[tuple[str, str, BoundaryType]],
) -> tuple[
    tuple[tuple[str, str, BoundaryType], str] | None,
    tuple[tuple[str, str, BoundaryType], tuple[str, str, BoundaryType]] | None,
]:
    """Process a single conflict pair and determine which correction to remove.

    Args:
        correction1: First correction (from shorter formatted typo)
        correction2: Second correction (from longer formatted typo)
        shorter_formatted_typo: The shorter formatted typo string
        formatted_typo: The longer formatted typo string
        boundary1: Boundary type for correction1
        boundary2: Boundary type for correction2
        match_direction: Platform match direction
        processed_pairs: Set of already processed correction pairs
        corrections_to_remove_set: Set of corrections already marked for removal

    Returns:
        Tuple of:
        - (correction_to_remove, reason) or None if pair already processed
        - (removed_correction, conflicting_correction) or None if pair already processed
    """
    # Skip if already marked for removal (early termination)
    if correction1 in corrections_to_remove_set or correction2 in corrections_to_remove_set:
        return None, None

    # Use frozenset to create unique pair identifier
    pair_id = frozenset([correction1, correction2])
    if pair_id in processed_pairs:
        return None, None
    processed_pairs.add(pair_id)

    # Determine which one to remove based on match direction
    _, word1, _ = correction1
    _, word2, _ = correction2

    if should_remove_shorter(
        match_direction,
        word1,
        word2,
        boundary1,
        boundary2,
    ):
        # Remove the shorter formatted one (formatted1)
        reason = (
            f"Cross-boundary substring conflict: "
            f"'{shorter_formatted_typo}' is substring of "
            f"'{formatted_typo}'"
        )
        return (correction1, reason), (correction1, correction2)
    else:
        # Remove the longer formatted one (formatted2)
        reason = (
            f"Cross-boundary substring conflict: "
            f"'{formatted_typo}' contains substring "
            f"'{shorter_formatted_typo}'"
        )
        return (correction2, reason), (correction2, correction1)


def check_bucket_conflicts(
    current_bucket: list[tuple[str, list[tuple[tuple[str, str, BoundaryType], str, BoundaryType]]]],
    candidates_by_char: dict[
        str,
        list[tuple[str, list[tuple[tuple[str, str, BoundaryType], str, BoundaryType]]]],
    ],
    match_direction: MatchDirection,
    processed_pairs: set[frozenset[tuple[str, str, BoundaryType]]],
    corrections_to_remove_set: set[tuple[str, str, BoundaryType]],
) -> tuple[
    list[tuple[tuple[str, str, BoundaryType], str]],
    dict[tuple[str, str, BoundaryType], tuple[str, str, BoundaryType]],
]:
    """Check conflicts for a bucket against accumulated shorter typos.

    Args:
        current_bucket: List of (formatted_typo, corrections) tuples for current length
        candidates_by_char: Character-based index of shorter typos from previous buckets
        match_direction: Platform match direction
        processed_pairs: Set of already processed correction pairs
        corrections_to_remove_set: Set of corrections already marked for removal

    Returns:
        Tuple of:
        - corrections_to_remove: List of (correction, reason) tuples
        - conflict_pairs: Dict mapping removed_correction -> conflicting_correction
    """
    corrections_to_remove = []
    conflict_pairs: dict[tuple[str, str, BoundaryType], tuple[str, str, BoundaryType]] = {}

    for formatted_typo, corrections_for_typo in current_bucket:
        # Get index key (first character for general substring conflicts)
        index_key = formatted_typo[0] if formatted_typo else ""

        # Only check against shorter typos with same first character
        if index_key in candidates_by_char:
            for shorter_formatted_typo, shorter_corrections in candidates_by_char[index_key]:
                # Check if shorter is a substring of current
                if is_substring(shorter_formatted_typo, formatted_typo):
                    # Check all combinations of corrections with early termination
                    for correction1, _, boundary1 in shorter_corrections:
                        # Skip if already marked for removal (early termination)
                        if correction1 in corrections_to_remove_set:
                            continue

                        for correction2, _, boundary2 in corrections_for_typo:
                            # Skip if already marked for removal (early termination)
                            if correction2 in corrections_to_remove_set:
                                continue

                            # Process conflict pair
                            result, conflict_pair = process_conflict_pair(
                                correction1,
                                correction2,
                                shorter_formatted_typo,
                                formatted_typo,
                                boundary1,
                                boundary2,
                                match_direction,
                                processed_pairs,
                                corrections_to_remove_set,
                            )

                            if result is not None:
                                correction_to_remove, reason = result
                                corrections_to_remove.append((correction_to_remove, reason))
                                if conflict_pair is not None:
                                    removed_correction, conflicting_correction = conflict_pair
                                    conflict_pairs[removed_correction] = conflicting_correction
                                    corrections_to_remove_set.add(removed_correction)

                            # Break early if all corrections for this formatted typo are marked
                            if all(
                                c in corrections_to_remove_set for c, _, _ in corrections_for_typo
                            ):
                                break

        # Add to index for future checks (only shorter typos are added since we
        # process in length order)
        candidates_by_char[index_key].append((formatted_typo, corrections_for_typo))

    return corrections_to_remove, conflict_pairs
