"""Collision resolution for typo corrections."""

from multiprocessing import Pool
from typing import TYPE_CHECKING

from loguru import logger
from tqdm import tqdm

from entroppy.core import Correction
from entroppy.core.boundaries import BoundaryIndex
from entroppy.matching import ExclusionMatcher
from entroppy.utils.helpers import cached_word_frequency

from entroppy.core import BoundaryType

from .boundary_selection import log_boundary_selection_details
from .correction_processing import process_collision_case, process_single_word_correction
from .worker_context import (
    CollisionResolutionContext,
    get_collision_worker_context,
    get_worker_indexes,
    init_collision_worker,
)

if TYPE_CHECKING:
    from entroppy.utils.debug import DebugTypoMatcher


def _process_typo_worker(item: tuple[str, list[str]]) -> tuple[
    Correction | None,
    bool,
    tuple[str, str, str | None] | None,
    tuple[str, list[str], float] | None,
    tuple[str, str, int] | None,
    dict | None,  # boundary_details
]:
    """Worker function to process a single typo collision.

    Args:
        item: Tuple of (typo, word_list)

    Returns:
        Tuple of (correction, was_skipped_short, excluded_info, skipped_collision, skipped_short_info)
        - correction: The resolved correction, or None if skipped/excluded/ambiguous
        - was_skipped_short: True if skipped due to short typo length
        - excluded_info: (typo, word, matching_rule) if excluded, None otherwise
        - skipped_collision: (typo, unique_words, ratio) if ambiguous collision, None otherwise
        - skipped_short_info: (typo, word, len(typo)) if skipped short, None otherwise
    """
    typo, word_list = item
    context = get_collision_worker_context()
    validation_index, source_index = get_worker_indexes()

    # Recreate ExclusionMatcher in worker (not serializable due to compiled regex)
    exclusion_matcher = ExclusionMatcher(set(context.exclusion_set))

    # Convert frozensets back to sets for compatibility
    validation_set = set(context.validation_set)
    source_words = set(context.source_words)
    user_words = set(context.user_words)
    debug_words = set(context.debug_words)

    unique_words = list(set(word_list))

    if len(unique_words) == 1:
        # Single word case: no collision
        word = unique_words[0]

        correction, was_skipped_short, excluded_info, boundary_details = (
            process_single_word_correction(
                typo,
                word,
                validation_set,
                source_words,
                context.min_typo_length,
                context.min_word_length,
                user_words,
                exclusion_matcher,
                debug_words,
                None,  # debug_typo_matcher not passed to workers (not easily serializable)
                validation_index,
                source_index,
            )
        )

        if was_skipped_short:
            return None, True, None, None, (typo, word, len(typo)), boundary_details
        elif excluded_info:
            return None, False, excluded_info, None, None, boundary_details
        elif correction:
            return correction, False, None, None, None, boundary_details
        else:
            return None, False, None, None, None, boundary_details
    else:
        # Collision case: multiple words compete for same typo
        correction, was_skipped_short, excluded_info, ratio, boundary_details = (
            process_collision_case(
                typo,
                unique_words,
                validation_set,
                source_words,
                context.freq_ratio,
                context.min_typo_length,
                context.min_word_length,
                user_words,
                exclusion_matcher,
                debug_words,
                None,  # debug_typo_matcher not passed to workers
                validation_index,
                source_index,
            )
        )

        if was_skipped_short:
            # Find the word that was selected before skipping
            word_freqs = [(w, cached_word_frequency(w, "en")) for w in unique_words]
            word_freqs.sort(key=lambda x: x[1], reverse=True)
            selected_word = word_freqs[0][0]
            return None, True, None, None, (typo, selected_word, len(typo)), boundary_details
        elif excluded_info:
            return None, False, excluded_info, None, None, boundary_details
        elif correction:
            return correction, False, None, None, None, boundary_details
        else:
            # Ambiguous collision - ratio too low
            return None, False, None, (typo, unique_words, ratio), None, boundary_details


def resolve_collisions(
    typo_map: dict[str, list[str]],
    validation_set: set[str],
    source_words: set[str],
    freq_ratio: float,
    min_typo_length: int,
    min_word_length: int,
    user_words: set[str],
    exclusion_matcher: ExclusionMatcher,
    debug_words: set[str] | None = None,
    debug_typo_matcher: "DebugTypoMatcher | None" = None,
    exclusion_set: set[str] | None = None,
    jobs: int = 1,
    verbose: bool = False,
) -> tuple[list[Correction], list, list, list]:
    """Resolve collisions where multiple words map to same typo.

    Args:
        typo_map: Map of typos to word lists (boundaries determined during resolution)
        validation_set: Set of validation words
        source_words: Set of source words
        freq_ratio: Minimum frequency ratio for collision resolution
        min_typo_length: Minimum typo length
        min_word_length: Minimum word length
        user_words: Set of user-provided words
        exclusion_matcher: Matcher for exclusion rules
        debug_words: Set of words to debug (exact matches)
        debug_typo_matcher: Matcher for debug typos (with wildcards/boundaries)
        exclusion_set: Set of exclusion patterns (needed for parallel workers)
        jobs: Number of parallel workers to use (1 = sequential)
        verbose: Whether to show progress bar

    Returns:
        Tuple of (final_corrections, skipped_collisions, skipped_short, excluded_corrections)
    """
    if debug_words is None:
        debug_words = set()

    if exclusion_set is None:
        # Fallback: use empty set if not provided (workers will recreate matcher)
        # This should only happen in single-threaded mode
        exclusion_set = set()

    final_corrections = []
    skipped_collisions = []
    skipped_short = []
    excluded_corrections = []

    if jobs > 1 and len(typo_map) > 1:
        # Parallel processing mode
        if verbose:
            logger.info(f"  Using {jobs} parallel workers")
            logger.info("  Preparing worker context...")

        # Create context for workers
        context = CollisionResolutionContext(
            validation_set=frozenset(validation_set),
            source_words=frozenset(source_words),
            freq_ratio=freq_ratio,
            min_typo_length=min_typo_length,
            min_word_length=min_word_length,
            user_words=frozenset(user_words),
            exclusion_set=frozenset(exclusion_set),
            debug_words=frozenset(debug_words),
        )

        if verbose:
            logger.info("  Initializing workers and building boundary indexes...")

        with Pool(
            processes=jobs,
            initializer=init_collision_worker,
            initargs=(context,),
        ) as pool:
            items = list(typo_map.items())
            results = pool.imap_unordered(_process_typo_worker, items)

            # Wrap with progress bar if verbose
            if verbose:
                results = tqdm(
                    results,
                    total=len(items),
                    desc="Resolving collisions",
                    unit="typo",
                )

            all_boundary_details = []
            for (
                correction,
                was_skipped_short,
                excluded_info,
                skipped_collision,
                skipped_short_info,
                boundary_details,
            ) in results:
                if was_skipped_short and skipped_short_info:
                    skipped_short.append(skipped_short_info)
                elif excluded_info:
                    excluded_corrections.append(excluded_info)
                elif skipped_collision:
                    skipped_collisions.append(skipped_collision)
                elif correction:
                    final_corrections.append(correction)

                if boundary_details:
                    all_boundary_details.append(boundary_details)

            # Log boundary selection details AFTER processing completes
            if all_boundary_details and debug_typo_matcher:
                for bd in all_boundary_details:
                    log_boundary_selection_details(
                        bd["typo"],
                        bd["word"],
                        BoundaryType(bd["boundary"]),
                        bd["details"],
                        debug_typo_matcher,
                    )
    else:
        # Single-threaded mode (original implementation)
        # Build boundary indexes for efficient lookups
        if verbose:
            logger.info("  Building boundary indexes...")
        validation_index = BoundaryIndex(validation_set)
        source_index = BoundaryIndex(source_words)

        # Wrap with progress bar if verbose
        items_iter = typo_map.items()
        if verbose:
            items_iter = tqdm(
                typo_map.items(),
                total=len(typo_map),
                desc="Resolving collisions",
                unit="typo",
            )

        for typo, word_list in items_iter:
            unique_words = list(set(word_list))

            if len(unique_words) == 1:
                # Single word case: no collision
                word = unique_words[0]

                correction, was_skipped_short, excluded_info, _ = process_single_word_correction(
                    typo,
                    word,
                    validation_set,
                    source_words,
                    min_typo_length,
                    min_word_length,
                    user_words,
                    exclusion_matcher,
                    debug_words,
                    debug_typo_matcher,
                    validation_index,
                    source_index,
                )

                if was_skipped_short:
                    skipped_short.append((typo, word, len(typo)))
                elif excluded_info:
                    excluded_corrections.append(excluded_info)
                elif correction:
                    final_corrections.append(correction)
            else:
                # Collision case: multiple words compete for same typo
                correction, was_skipped_short, excluded_info, ratio, _ = process_collision_case(
                    typo,
                    unique_words,
                    validation_set,
                    source_words,
                    freq_ratio,
                    min_typo_length,
                    min_word_length,
                    user_words,
                    exclusion_matcher,
                    debug_words,
                    debug_typo_matcher,
                    validation_index,
                    source_index,
                )

                if was_skipped_short:
                    # Find the word that was selected before skipping
                    word_freqs = [(w, cached_word_frequency(w, "en")) for w in unique_words]
                    word_freqs.sort(key=lambda x: x[1], reverse=True)
                    selected_word = word_freqs[0][0]
                    skipped_short.append((typo, selected_word, len(typo)))
                elif excluded_info:
                    excluded_corrections.append(excluded_info)
                elif correction:
                    final_corrections.append(correction)
                else:
                    # Ambiguous collision - ratio too low
                    skipped_collisions.append((typo, unique_words, ratio))

    return final_corrections, skipped_collisions, skipped_short, excluded_corrections
