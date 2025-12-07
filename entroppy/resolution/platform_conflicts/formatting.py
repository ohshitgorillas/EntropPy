"""Formatting helpers for platform-specific correction formatting.

This module handles the formatting of corrections for platform-specific output,
including caching and parallel processing optimizations.
"""

from collections import defaultdict
from dataclasses import dataclass
from multiprocessing import Pool
import threading
from typing import TYPE_CHECKING, Any, Callable

from tqdm import tqdm

from entroppy.core.boundaries import BoundaryType
from entroppy.platforms.qmk.formatting import format_boundary_markers

if TYPE_CHECKING:
    from entroppy.resolution.state import DictionaryState


@dataclass(frozen=True)
class FormattingContext:
    """Immutable context for formatting workers.

    This encapsulates the platform information needed for formatting corrections.
    The frozen dataclass ensures immutability and thread-safety.

    Attributes:
        is_qmk: Whether the platform is QMK (requires boundary formatting)
    """

    is_qmk: bool


# Thread-local storage for formatting worker context
_formatting_worker_context = threading.local()


def init_formatting_worker(context: FormattingContext) -> None:
    """Initialize worker process with formatting context.

    Args:
        context: FormattingContext to store in thread-local storage
    """
    _formatting_worker_context.value = context


def get_formatting_worker_context() -> FormattingContext:
    """Get the current worker's formatting context from thread-local storage.

    Returns:
        FormattingContext for this worker

    Raises:
        RuntimeError: If called before init_formatting_worker
    """
    try:
        context = _formatting_worker_context.value
        if not isinstance(context, FormattingContext):
            raise RuntimeError("Invalid formatting context type")
        return context
    except AttributeError as e:
        raise RuntimeError(
            "Formatting worker context not initialized. Call init_formatting_worker first."
        ) from e


def _format_correction_worker(
    correction: tuple[str, str, BoundaryType],
) -> tuple[tuple[str, str, BoundaryType], str]:
    """Worker function to format a single correction.

    Args:
        correction: Tuple of (typo, word, boundary)

    Returns:
        Tuple of (correction, formatted_typo)
    """
    context = get_formatting_worker_context()
    typo, _word, boundary = correction

    if context.is_qmk:
        formatted_typo = format_boundary_markers(typo, boundary)
    else:
        # For non-QMK platforms, boundaries are handled separately
        formatted_typo = typo

    return correction, formatted_typo


def format_corrections_with_cache(
    all_corrections: list[tuple[str, str, BoundaryType]],
    state: "DictionaryState",
    dirty_corrections: set[tuple[str, str, BoundaryType]],
    is_qmk: bool,
    pass_name: str,
    jobs: int,
    verbose: bool,
    format_typo_fn: Callable[[str, BoundaryType], str],
) -> tuple[
    dict[str, list[tuple[tuple[str, str, BoundaryType], str, BoundaryType]]],
    dict[tuple[str, str, BoundaryType], str],
]:
    """Format corrections using cache, only reformatting dirty ones.

    Args:
        all_corrections: List of all corrections (need formatted strings for all)
        state: Dictionary state (for cache access)
        dirty_corrections: Set of corrections that have changed (need reformatting)
        is_qmk: Whether platform is QMK
        pass_name: Name of the pass (for progress bars)
        jobs: Number of parallel jobs
        verbose: Whether to show progress bars
        format_typo_fn: Function to format a typo (typo, boundary) -> str

    Returns:
        Tuple of:
        - formatted_to_corrections: Dict mapping formatted_typo ->
          list of (correction, typo, boundary)
        - correction_to_formatted: Dict mapping correction -> formatted_typo
    """
    # Optimization: Check cache first, only format dirty corrections
    corrections_to_format = []
    cached_results = []

    formatted_cache = state.get_formatted_cache()
    for correction in all_corrections:
        if correction in dirty_corrections:
            # This correction changed, need to reformat (check cache first though)
            if correction in formatted_cache:
                # Remove from cache (will be reformatted)
                del formatted_cache[correction]
            corrections_to_format.append(correction)
        elif correction in formatted_cache:
            # Use cached formatted string (correction hasn't changed)
            formatted_typo = formatted_cache[correction]
            cached_results.append((correction, formatted_typo))
        else:
            # Not in cache and not dirty - format it (first time or cache was cleared)
            corrections_to_format.append(correction)

    # Format uncached corrections
    if corrections_to_format:
        formatted_results_new = _format_corrections_batch(
            corrections_to_format, is_qmk, pass_name, jobs, verbose, format_typo_fn
        )
        # Update cache with newly formatted corrections
        formatted_cache = state.get_formatted_cache()
        for correction, formatted_typo in formatted_results_new:
            formatted_cache[correction] = formatted_typo
    else:
        formatted_results_new = []

    # Combine cached and newly formatted results
    formatted_results = cached_results + formatted_results_new

    # Build lookup structures
    # pylint: disable=duplicate-code
    # Acceptable pattern: Building lookup structures from formatted results is a common
    # pattern shared with formatting_helpers.py. Both need to build the same lookup
    # structures (formatted_to_corrections and correction_to_formatted) in the same way.
    # This is expected when both places need to process formatted corrections identically.
    formatted_to_corrections: dict[
        str, list[tuple[tuple[str, str, BoundaryType], str, BoundaryType]]
    ] = defaultdict(list)
    correction_to_formatted: dict[tuple[str, str, BoundaryType], str] = {}

    for correction, formatted_typo in formatted_results:
        typo, _word, boundary = correction
        formatted_to_corrections[formatted_typo].append((correction, typo, boundary))
        correction_to_formatted[correction] = formatted_typo

    return formatted_to_corrections, correction_to_formatted


def _format_corrections_batch(
    corrections_to_format: list[tuple[str, str, BoundaryType]],
    is_qmk: bool,
    pass_name: str,
    jobs: int,
    verbose: bool,
    format_typo_fn: Callable[[str, BoundaryType], str],
) -> list[tuple[tuple[str, str, BoundaryType], str]]:
    """Format a batch of corrections in parallel or sequentially.

    Args:
        corrections_to_format: List of corrections to format
        is_qmk: Whether platform is QMK
        pass_name: Name of the pass (for progress bars)
        jobs: Number of parallel jobs
        verbose: Whether to show progress bars
        format_typo_fn: Function to format a typo (typo, boundary) -> str

    Returns:
        List of (correction, formatted_typo) tuples
    """
    # Determine if we should use parallel processing
    use_parallel = jobs > 1 and len(corrections_to_format) >= 100

    if use_parallel:
        return _format_corrections_parallel_impl(
            corrections_to_format, is_qmk, pass_name, jobs, verbose
        )
    return _format_corrections_sequential_impl(
        corrections_to_format, pass_name, verbose, format_typo_fn
    )


def _format_corrections_parallel_impl(
    corrections_to_format: list[tuple[str, str, BoundaryType]],
    is_qmk: bool,
    pass_name: str,
    jobs: int,
    verbose: bool,
) -> list[tuple[tuple[str, str, BoundaryType], str]]:
    """Format corrections in parallel.

    Args:
        corrections_to_format: List of corrections to format
        is_qmk: Whether platform is QMK
        pass_name: Name of the pass (for progress bars)
        jobs: Number of parallel jobs
        verbose: Whether to show progress bars

    Returns:
        List of (correction, formatted_typo) tuples
    """
    # pylint: disable=duplicate-code
    # Acceptable pattern: Parallel processing setup using Pool with initializer pattern.
    # This pattern is shared with formatting_helpers.py because both need to set up
    # parallel formatting workers in the same way. The Pool initialization pattern
    # is standard and should not be refactored.

    # Create worker context (immutable, serializable)
    formatting_context = FormattingContext(is_qmk=is_qmk)

    # Process in parallel using initializer pattern (avoids pickle)
    with Pool(
        processes=jobs,
        initializer=init_formatting_worker,
        initargs=(formatting_context,),
    ) as pool:
        if verbose:
            results_iter = pool.imap(_format_correction_worker, corrections_to_format)
            results: Any = tqdm(
                results_iter,
                desc=f"    {pass_name}",
                total=len(corrections_to_format),
                unit="correction",
                leave=False,
            )
        else:
            results = pool.imap(_format_correction_worker, corrections_to_format)

        return list(results)


def _format_corrections_sequential_impl(
    corrections_to_format: list[tuple[str, str, BoundaryType]],
    pass_name: str,
    verbose: bool,
    format_typo_fn: Callable[[str, BoundaryType], str],
) -> list[tuple[tuple[str, str, BoundaryType], str]]:
    """Format corrections sequentially.

    Args:
        corrections_to_format: List of corrections to format
        pass_name: Name of the pass (for progress bars)
        verbose: Whether to show progress bars
        format_typo_fn: Function to format a typo (typo, boundary) -> str

    Returns:
        List of (correction, formatted_typo) tuples
    """
    if verbose:
        corrections_iter: Any = tqdm(
            corrections_to_format,
            desc=f"    {pass_name}",
            unit="correction",
            leave=False,
        )
    else:
        corrections_iter = corrections_to_format

    formatted_results = []
    for correction in corrections_iter:
        typo, _word, boundary = correction
        formatted_typo = format_typo_fn(typo, boundary)
        formatted_results.append((correction, formatted_typo))

    return formatted_results
