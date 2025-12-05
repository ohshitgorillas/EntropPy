"""Convergence checking for the iterative solver."""

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from entroppy.resolution.state import DictionaryState


def _get_state_counts(state: "DictionaryState") -> tuple[int, int, int]:
    """Get current state counts.

    Args:
        state: The dictionary state

    Returns:
        Tuple of (corrections_count, patterns_count, graveyard_count)
    """
    return (
        len(state.active_corrections),
        len(state.active_patterns),
        len(state.graveyard),
    )


def _check_convergence(
    state: "DictionaryState",
    iteration: int,
    previous_corrections: int,
    previous_patterns: int,
    previous_graveyard: int,
) -> tuple[bool, int, int, int]:
    """Check if the solver has converged.

    Args:
        state: The dictionary state
        iteration: Current iteration number
        previous_corrections: Corrections count from previous iteration
        previous_patterns: Patterns count from previous iteration
        previous_graveyard: Graveyard count from previous iteration

    Returns:
        Tuple of (converged, current_corrections, current_patterns, current_graveyard)
    """
    corrections, patterns, graveyard = _get_state_counts(state)

    corrections_change = corrections - previous_corrections
    patterns_change = patterns - previous_patterns
    graveyard_change = graveyard - previous_graveyard

    converged = corrections_change == 0 and patterns_change == 0 and graveyard_change == 0

    if converged:
        logger.info(f"  ✓ Converged (no net changes in iteration {iteration})")
        state.clear_dirty_flag()
    else:
        logger.info(
            f"  State changed: corrections {corrections_change:+d}, "
            f"patterns {patterns_change:+d}, graveyard {graveyard_change:+d}"
        )

    return converged, corrections, patterns, graveyard
