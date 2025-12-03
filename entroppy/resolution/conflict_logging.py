"""Debug logging functions for conflict resolution."""

from typing import TYPE_CHECKING

from entroppy.core import BoundaryType, Correction
from entroppy.utils.debug import (is_debug_correction, log_debug_correction,
                                  log_if_debug_correction)

if TYPE_CHECKING:
    from entroppy.resolution.conflicts import ConflictDetector
    from entroppy.utils.debug import DebugTypoMatcher


def log_blocked_correction(
    long_correction: Correction,
    typo: str,
    candidate: str,
    short_word: str,
    long_word: str,
    detector: "ConflictDetector",
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
) -> None:
    """Log that a correction was blocked by a shorter correction.

    Args:
        long_correction: The correction that was blocked
        typo: The typo string for the long correction
        candidate: The candidate typo that blocked it
        short_word: The correct word for the candidate typo
        long_word: The correct word for the long typo
        detector: Conflict detector for calculating expected result
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
    """
    if is_debug_correction(long_correction, debug_words, debug_typo_matcher):
        expected_result = detector.calculate_result(typo, candidate, short_word)
        log_debug_correction(
            long_correction,
            f"REMOVED - blocked by shorter correction '{candidate} → {short_word}' "
            f"(typing '{typo}' triggers '{candidate}' producing '{expected_result}' "
            f"= '{long_word}' ✓)",
            debug_words,
            debug_typo_matcher,
            "Stage 5",
        )


def log_kept_correction(
    correction: Correction,
    boundary: BoundaryType,
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
) -> None:
    """Log that a correction was kept (not blocked).

    Args:
        correction: The correction that was kept
        boundary: The boundary type
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
    """
    log_if_debug_correction(
        correction,
        f"Kept - no blocking substring conflicts found (boundary: {boundary.value})",
        debug_words,
        debug_typo_matcher,
        "Stage 5",
    )
