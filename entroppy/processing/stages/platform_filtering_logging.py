"""Debug logging functions for platform filtering and ranking stage."""

from typing import TYPE_CHECKING

from entroppy.core import Correction
from entroppy.utils.debug import is_debug_correction, log_debug_correction

if TYPE_CHECKING:
    from entroppy.utils.debug import DebugTypoMatcher


def log_max_corrections_limit_application(
    correction: Correction,
    position: int,
    max_corrections: int,
    total_ranked: int,
    within_limit: bool,
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
) -> None:
    """Log when a correction is affected by max_corrections limit.

    Args:
        correction: The correction being checked
        position: Position in ranked list (1-indexed)
        max_corrections: Maximum corrections limit
        total_ranked: Total number of ranked corrections
        within_limit: Whether correction is within the limit
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
    """
    # pylint: disable=duplicate-code
    # This function intentionally duplicates logic from qmk_logging.log_max_corrections_limit
    # to maintain separation between platform-specific (QMK) and general pipeline logging.
    # The QMK version is used during platform ranking, while this version is used in the
    # general pipeline stage. Keeping them separate preserves existing debug logging
    # behavior and allows for platform-specific message customization.
    if is_debug_correction(correction, debug_words, debug_typo_matcher):
        if within_limit:
            log_debug_correction(
                correction,
                f"Included in final output: position {position} "
                f"(within limit of {max_corrections}, total ranked: {total_ranked})",
                debug_words,
                debug_typo_matcher,
                "Stage 6",
            )
        else:
            log_debug_correction(
                correction,
                f"Excluded from final output: position {position} "
                f"(exceeds limit of {max_corrections}, total ranked: {total_ranked})",
                debug_words,
                debug_typo_matcher,
                "Stage 6",
            )
