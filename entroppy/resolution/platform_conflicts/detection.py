"""Platform substring conflict detection logic.

This module contains the core detection algorithms for finding cross-boundary
substring conflicts in platform-formatted typo strings.
"""

from collections import defaultdict
from multiprocessing import Pool
from typing import TYPE_CHECKING

from entroppy.core.boundaries import BoundaryIndex, BoundaryType
from entroppy.core.types import MatchDirection
from entroppy.resolution.platform_conflicts import parallel, utils
from entroppy.resolution.platform_conflicts.utils import (
    build_index_keys_to_check,
    is_substring,
    process_conflict_combinations,
)

if TYPE_CHECKING:
    from tqdm import tqdm

    from entroppy.utils.debug import DebugTypoMatcher


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
        int,
        list[tuple[str, list[tuple[tuple[str, str, BoundaryType], str, BoundaryType]]]],
    ] = defaultdict(list)

    for formatted_typo, corrections in formatted_to_corrections.items():
        length_buckets[len(formatted_typo)].append((formatted_typo, corrections))

    return length_buckets


def _process_typo_conflicts(
    formatted_typo: str,
    corrections_for_typo: list[tuple[tuple[str, str, BoundaryType], str, BoundaryType]],
    index_keys_to_check: list[str],
    candidates_by_char: dict[
        str,
        list[tuple[str, list[tuple[tuple[str, str, BoundaryType], str, BoundaryType]]]],
    ],
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
    """Process conflicts for a single formatted typo.

    Args:
        formatted_typo: The formatted typo string
        corrections_for_typo: List of corrections for this typo
        index_keys_to_check: List of index keys to check
        candidates_by_char: Character-based index of shorter typos
        match_direction: Platform match direction
        processed_pairs: Set of already processed correction pairs
        corrections_to_remove_set: Set of corrections already marked for removal
        validation_index: Optional boundary index for validation set
        source_index: Optional boundary index for source words
        debug_words: Optional set of words to debug
        debug_typo_matcher: Optional matcher for debug typos

    Returns:
        Tuple of (corrections_to_remove, conflict_pairs)
    """
    corrections_to_remove: list[tuple[tuple[str, str, BoundaryType], str]] = []
    conflict_pairs: dict[tuple[str, str, BoundaryType], tuple[str, str, BoundaryType]] = {}

    # Find all substring conflicts using shared helper
    substring_conflicts = utils.find_substring_conflicts_in_index(
        formatted_typo,
        index_keys_to_check,
        candidates_by_char,
        is_substring,
    )

    for shorter_formatted_typo, shorter_corrections in substring_conflicts:
        # pylint: disable=duplicate-code
        # False positive: This is a call to the shared process_conflict_combinations
        # function. The similar code in parallel.py is the same function call,
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
            break

    return corrections_to_remove, conflict_pairs


def check_bucket_conflicts(
    current_bucket: list[tuple[str, list[tuple[tuple[str, str, BoundaryType], str, BoundaryType]]]],
    candidates_by_char: dict[
        str,
        list[tuple[str, list[tuple[tuple[str, str, BoundaryType], str, BoundaryType]]]],
    ],
    match_direction: MatchDirection,
    processed_pairs: set[frozenset[tuple[str, str, BoundaryType]]],
    corrections_to_remove_set: set[tuple[str, str, BoundaryType]],
    progress_bar: "tqdm | None" = None,
    validation_index: BoundaryIndex | None = None,
    source_index: BoundaryIndex | None = None,
    debug_words: set[str] | None = None,
    debug_typo_matcher: "DebugTypoMatcher | None" = None,
    num_workers: int = 1,
) -> tuple[
    list[tuple[tuple[str, str, BoundaryType], str]],
    dict[tuple[str, str, BoundaryType], tuple[str, str, BoundaryType]],
]:
    """Check conflicts for a bucket against accumulated shorter typos.

    Uses a two-phase approach when parallelization is enabled:
    1. Parallel detection (read-only): Find all conflicts without modifying state
    2. Sequential resolution: Apply deterministic rules to resolve conflicts

    Args:
        current_bucket: List of (formatted_typo, corrections) tuples for current length
        candidates_by_char: Character-based index of shorter typos from previous buckets
        match_direction: Platform match direction
        processed_pairs: Set of already processed correction pairs
        corrections_to_remove_set: Set of corrections already marked for removal
        progress_bar: Optional progress bar to update as typos are processed
        validation_index: Optional boundary index for validation set (for false trigger checks)
        source_index: Optional boundary index for source words (for false trigger checks)
        debug_words: Optional set of words to debug
        debug_typo_matcher: Optional matcher for debug typos
        num_workers: Number of worker processes to use (1 = sequential, >1 = parallel)

    Returns:
        Tuple of:
        - corrections_to_remove: List of (correction, reason) tuples
        - conflict_pairs: Dict mapping removed_correction -> conflicting_correction
    """
    # Determine if we should use parallel processing
    use_parallel = num_workers > 1 and len(current_bucket) >= 100

    # Initialize return values
    corrections_to_remove: list[tuple[tuple[str, str, BoundaryType], str]] = []
    conflict_pairs: dict[tuple[str, str, BoundaryType], tuple[str, str, BoundaryType]] = {}

    if use_parallel:
        # Phase 1: Parallel detection (read-only)
        chunks = parallel.divide_into_chunks(current_bucket, num_workers)

        with Pool(processes=num_workers) as pool:
            all_conflicts_lists = pool.starmap(
                parallel.detect_conflicts_for_chunk,
                [(chunk, candidates_by_char) for chunk in chunks],
            )

        # Flatten all conflicts from all workers
        all_conflicts = []
        for conflicts_list in all_conflicts_lists:
            all_conflicts.extend(conflicts_list)

        # Update progress bar
        if progress_bar is not None:
            progress_bar.update(len(current_bucket))

        # Phase 2: Sequential resolution (deterministic)
        # pylint: disable=duplicate-code
        # Acceptable pattern: This is a function call to resolve_conflicts_sequential
        # with standard parameters. The similar code in conflict_processing.py calls
        # process_conflict_pair with similar parameters. This is expected when both
        # places need to process conflicts with the same context.
        corrections_to_remove, conflict_pairs = parallel.resolve_conflicts_sequential(
            all_conflicts,
            match_direction,
            processed_pairs,
            corrections_to_remove_set,
            validation_index,
            source_index,
            debug_words,
            debug_typo_matcher,
        )
    else:
        # Sequential processing (original algorithm)

        for formatted_typo, corrections_for_typo in current_bucket:
            # Update progress bar for each formatted typo processed
            if progress_bar is not None:
                progress_bar.update(1)

            # Build index keys to check
            index_keys_to_check = build_index_keys_to_check(formatted_typo)

            # Process conflicts for this typo
            typo_corrections_to_remove, typo_conflict_pairs = _process_typo_conflicts(
                formatted_typo,
                corrections_for_typo,
                index_keys_to_check,
                candidates_by_char,
                match_direction,
                processed_pairs,
                corrections_to_remove_set,
                validation_index,
                source_index,
                debug_words,
                debug_typo_matcher,
            )

            corrections_to_remove.extend(typo_corrections_to_remove)
            conflict_pairs.update(typo_conflict_pairs)

    # Add to index for future checks (only shorter typos are added since we
    # process in length order)
    for formatted_typo, corrections_for_typo in current_bucket:
        index_key = formatted_typo[0] if formatted_typo else ""
        candidates_by_char[index_key].append((formatted_typo, corrections_for_typo))

    return corrections_to_remove, conflict_pairs
