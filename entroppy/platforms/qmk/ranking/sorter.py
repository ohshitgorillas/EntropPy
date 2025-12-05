"""Sorting and ranking functions for QMK."""

from typing import TYPE_CHECKING

from entroppy.core import BoundaryType, Correction
from entroppy.platforms.qmk.qmk_logging import log_max_corrections_limit, log_ranking_position
from entroppy.utils.debug import is_debug_correction

from .scorer import (
    _build_word_frequency_cache,
    _collect_all_words,
    score_direct_corrections,
    score_patterns,
)
from .tiers import separate_by_type

if TYPE_CHECKING:
    from entroppy.utils.debug import DebugTypoMatcher


def _log_ranking_debug(
    ranked: list[Correction],
    user_corrections: list[Correction],
    pattern_scores: list[tuple[float, str, str, BoundaryType]],
    direct_scores: list[tuple[float, str, str, BoundaryType]],
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
) -> None:
    """Log ranking debug information for debug corrections.

    Args:
        ranked: Ranked list of corrections
        user_corrections: User corrections list
        pattern_scores: Pattern scores list
        direct_scores: Direct correction scores list
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
    """
    # Build lookup dictionaries once instead of searching lists
    pattern_score_dict = {(t, w, b): score for score, t, w, b in pattern_scores}
    direct_score_dict = {(t, w, b): score for score, t, w, b in direct_scores}

    # Build tier boundaries for context
    user_count = len(user_corrections)
    pattern_count = len(pattern_scores)
    direct_count = len(direct_scores)

    for i, correction in enumerate(ranked):
        if is_debug_correction(correction, debug_words, debug_typo_matcher):
            # Determine tier and position within tier
            if i < user_count:
                tier = 0
                tier_pos = i + 1
                tier_name = "user words"
                tier_total = user_count
                score_info = "infinite priority"
            elif i < user_count + pattern_count:
                tier = 1
                tier_pos = i - user_count + 1
                tier_name = "patterns"
                tier_total = pattern_count
                # O(1) lookup instead of O(n) search
                pattern_score = pattern_score_dict.get(correction)
                score_info = (
                    f"score: {pattern_score:.2e}" if pattern_score is not None else "score: unknown"
                )
            else:
                tier = 2
                tier_pos = i - user_count - pattern_count + 1
                tier_name = "direct corrections"
                tier_total = direct_count
                # O(1) lookup instead of O(n) search
                direct_score = direct_score_dict.get(correction)
                score_info = (
                    f"score: {direct_score:.2e}" if direct_score is not None else "score: unknown"
                )

            # Find nearby corrections for context
            nearby = []
            for j in range(max(0, i - 2), min(len(ranked), i + 3)):
                if j != i:
                    nearby_typo, nearby_word, _ = ranked[j]
                    nearby.append(f"{nearby_typo}->{nearby_word}")

            nearby_str = ", ".join(nearby[:3])
            if len(nearby) > 3:
                nearby_str += "..."

            nearby_info = f" [nearby: {nearby_str}]" if nearby_str else ""
            log_ranking_position(
                correction,
                i + 1,
                len(ranked),
                tier,
                tier_name,
                tier_pos,
                tier_total,
                score_info,
                nearby_info,
                debug_words,
                debug_typo_matcher,
            )


def _log_max_corrections_debug(
    ranked: list[Correction],
    max_corrections: int,
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
) -> None:
    """Log max corrections limit debug information.

    Args:
        ranked: Ranked list of corrections
        max_corrections: Maximum number of corrections
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
    """
    # Log if any debug corrections are cut off by the limit
    for i, correction in enumerate(ranked):
        if is_debug_correction(correction, debug_words, debug_typo_matcher):
            log_max_corrections_limit(
                correction,
                i + 1,
                max_corrections,
                len(ranked),
                i < max_corrections,
                debug_words,
                debug_typo_matcher,
            )


def rank_corrections(
    corrections: list[Correction],
    patterns: list[Correction],
    pattern_replacements: dict[Correction, list[Correction]],
    user_words: set[str],
    max_corrections: int | None = None,
    cached_pattern_typos: set[tuple[str, str]] | None = None,
    cached_replaced_by_patterns: set[tuple[str, str]] | None = None,
    verbose: bool = False,
    debug_words: set[str] | None = None,
    debug_typo_matcher: "DebugTypoMatcher | None" = None,
) -> tuple[
    list[Correction],
    list[Correction],
    list[tuple[float, str, str, BoundaryType]],
    list[tuple[float, str, str, BoundaryType]],
    list[tuple[float, str, str, BoundaryType]],
]:
    """Rank corrections by QMK-specific usefulness.

    Three-tier system:
    1. User words (infinite priority)
    2. Patterns (scored by sum of replaced word frequencies)
    3. Direct corrections (scored by word frequency)

    Optimized with:
    - Batch word frequency lookups (Priority 1)
    - Lazy evaluation for debug logging (Priority 2)
    - Separate sorting per tier (Priority 5)
    - O(1) score lookups for debug logging (Priority 4)

    Args:
        corrections: List of corrections to rank
        patterns: List of pattern corrections
        pattern_replacements: Dictionary mapping patterns to their replacements
        user_words: Set of user-defined words
        max_corrections: Optional limit on number of corrections
        cached_pattern_typos: Optional cached set of (typo, word) tuples for patterns
        cached_replaced_by_patterns: Optional cached set of (typo, word) tuples replaced by patterns
        verbose: Whether to show progress bars
        debug_words: Set of words to debug (exact matches)
        debug_typo_matcher: Matcher for debug typos (with wildcards/boundaries)

    Returns:
        Tuple of (ranked_corrections, user_corrections, pattern_scores, direct_scores, all_scored)
    """
    user_corrections, pattern_corrections, direct_corrections = separate_by_type(
        corrections,
        patterns,
        pattern_replacements,
        user_words,
        cached_pattern_typos,
        cached_replaced_by_patterns,
        debug_words,
        debug_typo_matcher,
    )

    # Priority 1: Batch word frequency lookups
    # Collect all unique words that need frequency lookups
    all_words = _collect_all_words(pattern_corrections, direct_corrections, pattern_replacements)

    # Pre-compute all word frequencies in one batch
    word_freq_cache = _build_word_frequency_cache(all_words, verbose)

    # Score patterns using pre-computed cache
    pattern_scores = score_patterns(
        pattern_corrections,
        pattern_replacements,
        word_freq_cache,
        verbose,
        debug_words,
        debug_typo_matcher,
    )

    # Score direct corrections using pre-computed cache
    direct_scores = score_direct_corrections(
        direct_corrections,
        word_freq_cache,
        verbose,
        debug_words,
        debug_typo_matcher,
    )

    # Priority 5: Sort patterns and direct corrections separately (they're in different tiers)
    # Sort patterns by score (descending)
    pattern_scores.sort(key=lambda x: -x[0])

    # Sort direct corrections by score (descending)
    direct_scores.sort(key=lambda x: -x[0])

    # Build ranked list: user words first, then sorted patterns, then sorted direct corrections
    ranked = (
        user_corrections
        + [(t, w, b) for _, t, w, b in pattern_scores]
        + [(t, w, b) for _, t, w, b in direct_scores]
    )

    # Priority 4: Optimize debug logging with O(1) lookup dictionaries
    if debug_words or debug_typo_matcher:
        _log_ranking_debug(
            ranked,
            user_corrections,
            pattern_scores,
            direct_scores,
            debug_words or set(),
            debug_typo_matcher,
        )

    # Apply max_corrections limit if specified
    if max_corrections:
        if debug_words or debug_typo_matcher:
            _log_max_corrections_debug(
                ranked, max_corrections, debug_words or set(), debug_typo_matcher
            )
        ranked = ranked[:max_corrections]

    # Build all_scored for backward compatibility (combines patterns and direct)
    all_scored = pattern_scores + direct_scores

    return ranked, user_corrections, pattern_scores, direct_scores, all_scored
