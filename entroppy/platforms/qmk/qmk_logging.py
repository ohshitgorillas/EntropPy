"""Debug logging functions for QMK platform filtering and ranking."""

from typing import TYPE_CHECKING

from entroppy.core import Correction
from entroppy.utils.debug import is_debug_correction, log_debug_correction

if TYPE_CHECKING:
    from entroppy.utils.debug import DebugTypoMatcher


def log_separation_by_type(
    correction: Correction,
    _correction_type: str,  # Unused but kept for API consistency
    message: str,
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
) -> None:
    """Log when a correction is separated by type (user word, pattern, or direct).

    Args:
        correction: The correction being separated
        _correction_type: Type of correction ("user word", "pattern", "direct", or "replaced")
        message: The message to log
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
    """
    if is_debug_correction(correction, debug_words, debug_typo_matcher):
        log_debug_correction(correction, message, debug_words, debug_typo_matcher, "Stage 6")


def log_pattern_scoring(
    correction: Correction,
    total_freq: float,
    replacement_count: int,
    replacement_list: str,
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
) -> None:
    """Log when a pattern is scored.

    Args:
        correction: The pattern correction
        total_freq: Total frequency score
        replacement_count: Number of replacements
        replacement_list: String representation of replacement words
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
    """
    if is_debug_correction(correction, debug_words, debug_typo_matcher):
        log_debug_correction(
            correction,
            f"Scored pattern: {total_freq:.2e} (sum of frequencies for "
            f"{replacement_count} replacements: {replacement_list})",
            debug_words,
            debug_typo_matcher,
            "Stage 6",
        )


def log_direct_scoring(
    correction: Correction,
    freq: float,
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
) -> None:
    """Log when a direct correction is scored.

    Args:
        correction: The direct correction
        freq: Word frequency score
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
    """
    if is_debug_correction(correction, debug_words, debug_typo_matcher):
        log_debug_correction(
            correction,
            f"Scored direct correction: {freq:.2e} (word frequency)",
            debug_words,
            debug_typo_matcher,
            "Stage 6",
        )


def log_ranking_position(
    correction: Correction,
    position: int,
    total: int,
    tier: int,
    tier_name: str,
    tier_pos: int,
    tier_total: int,
    score_info: str,
    nearby_info: str,
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
) -> None:
    """Log the final ranking position of a correction.

    Args:
        correction: The correction being ranked
        position: Overall position (1-indexed)
        total: Total number of corrections
        tier: Tier number (0=user, 1=pattern, 2=direct)
        tier_name: Name of the tier
        tier_pos: Position within tier (1-indexed)
        tier_total: Total in tier
        score_info: Score information string
        nearby_info: Nearby corrections information
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
    """
    if is_debug_correction(correction, debug_words, debug_typo_matcher):
        log_debug_correction(
            correction,
            f"Ranked at position {position}/{total} (tier {tier}: {tier_name}, "
            f"position {tier_pos}/{tier_total}, {score_info}){nearby_info}",
            debug_words,
            debug_typo_matcher,
            "Stage 6",
        )


def log_max_corrections_limit(
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
    if is_debug_correction(correction, debug_words, debug_typo_matcher):
        if within_limit:
            log_debug_correction(
                correction,
                f"Made the cut: position {position} (within limit of {max_corrections})",
                debug_words,
                debug_typo_matcher,
                "Stage 6",
            )
        else:
            log_debug_correction(
                correction,
                f"Cut off by max_corrections limit: position {position} "
                f"(limit: {max_corrections}, total ranked: {total_ranked})",
                debug_words,
                debug_typo_matcher,
                "Stage 6",
            )


def log_character_filtering(
    correction: Correction,
    reason: str,
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
) -> None:
    """Log when a correction is filtered due to invalid characters.

    Args:
        correction: The correction being filtered
        reason: Reason for filtering
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
    """
    if is_debug_correction(correction, debug_words, debug_typo_matcher):
        log_debug_correction(
            correction,
            f"Filtered - {reason}",
            debug_words,
            debug_typo_matcher,
            "Stage 6",
        )


def log_same_typo_conflict(
    removed_correction: Correction,
    kept_correction: Correction,
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
) -> None:
    """Log when a same-typo conflict is resolved.

    Args:
        removed_correction: The correction that was removed
        kept_correction: The correction that was kept
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
    """
    removed_typo, removed_word, removed_boundary = removed_correction
    kept_typo, kept_word, kept_boundary = kept_correction

    if is_debug_correction(removed_correction, debug_words, debug_typo_matcher):
        log_debug_correction(
            removed_correction,
            f"Filtered - same-typo conflict (kept: {kept_typo} -> {kept_word} "
            f"with boundary {kept_boundary.name})",
            debug_words,
            debug_typo_matcher,
            "Stage 6",
        )

    if is_debug_correction(kept_correction, debug_words, debug_typo_matcher):
        log_debug_correction(
            kept_correction,
            f"Kept - same-typo conflict (removed: {removed_typo} -> {removed_word} "
            f"with boundary {removed_boundary.name})",
            debug_words,
            debug_typo_matcher,
            "Stage 6",
        )


def log_suffix_conflict(
    long_correction: Correction,
    short_correction: Correction,
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
) -> None:
    """Log when a suffix conflict is detected.

    Args:
        long_correction: The longer correction that was removed
        short_correction: The shorter correction that was kept
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
    """
    long_typo, long_word, _ = long_correction
    short_typo, short_word, _ = short_correction

    if is_debug_correction(long_correction, debug_words, debug_typo_matcher):
        log_debug_correction(
            long_correction,
            f"Filtered - suffix conflict (shorter typo '{short_typo}' -> "
            f"'{short_word}' blocks it)",
            debug_words,
            debug_typo_matcher,
            "Stage 6",
        )

    if is_debug_correction(short_correction, debug_words, debug_typo_matcher):
        log_debug_correction(
            short_correction,
            f"Kept - suffix conflict (blocks longer typo '{long_typo}' -> '{long_word}')",
            debug_words,
            debug_typo_matcher,
            "Stage 6",
        )


def log_substring_conflict(
    removed_correction: Correction,
    kept_correction: Correction,
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
) -> None:
    """Log when a substring conflict is detected.

    Args:
        removed_correction: The correction that was removed
        kept_correction: The correction that was kept
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
    """
    removed_typo, removed_word, _ = removed_correction
    kept_typo, kept_word, _ = kept_correction

    if is_debug_correction(removed_correction, debug_words, debug_typo_matcher):
        log_debug_correction(
            removed_correction,
            f"Filtered - substring conflict (shorter typo '{kept_typo}' -> "
            f"'{kept_word}' blocks it)",
            debug_words,
            debug_typo_matcher,
            "Stage 6",
        )

    if is_debug_correction(kept_correction, debug_words, debug_typo_matcher):
        log_debug_correction(
            kept_correction,
            f"Kept - substring conflict (blocks longer typo '{removed_typo}' -> '{removed_word}')",
            debug_words,
            debug_typo_matcher,
            "Stage 6",
        )


def log_garbage_correction_removal(
    typo2_correction: Correction,
    typo1_correction: Correction,
    result: str,
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
) -> None:
    """Log when a shorter typo is removed because it would produce garbage.

    Args:
        typo2_correction: The shorter correction that was removed
        typo1_correction: The longer correction that was kept
        result: The garbage result that would have been produced
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
    """
    typo1, word1, _ = typo1_correction
    typo2, word2, _ = typo2_correction

    if is_debug_correction(typo2_correction, debug_words, debug_typo_matcher):
        log_debug_correction(
            typo2_correction,
            f"Filtered - substring conflict (would produce garbage "
            f"'{result}' for '{typo1}' -> '{word1}', "
            f"kept longer typo instead)",
            debug_words,
            debug_typo_matcher,
            "Stage 6",
        )

    if is_debug_correction(typo1_correction, debug_words, debug_typo_matcher):
        log_debug_correction(
            typo1_correction,
            f"Kept - substring conflict (removed shorter typo "
            f"'{typo2}' -> '{word2}' that would produce garbage '{result}')",
            debug_words,
            debug_typo_matcher,
            "Stage 6",
        )
