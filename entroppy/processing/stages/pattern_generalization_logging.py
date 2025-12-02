"""Debug logging functions for pattern generalization stage."""

from typing import TYPE_CHECKING

from entroppy.core import Correction
from entroppy.utils.debug import log_if_debug_correction

if TYPE_CHECKING:
    from entroppy.utils.debug import DebugTypoMatcher


def log_pattern_collision_resolution(
    typo: str,
    word_list: list[str],
    resolved_corrections: list[Correction],
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
) -> None:
    """Log when patterns have collisions resolved (multiple words map to same pattern typo).

    Args:
        typo: The pattern typo that had a collision
        word_list: List of words that mapped to this pattern typo
        resolved_corrections: List of resolved corrections (one per boundary/word)
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
    """
    if len(word_list) > 1:
        # Check if any of the words or the typo is being debugged
        for correction in resolved_corrections:
            log_if_debug_correction(
                correction,
                f"Pattern collision resolved: {len(word_list)} words mapped to pattern "
                f"typo '{typo}' (words: {', '.join(word_list)})",
                debug_words,
                debug_typo_matcher,
                "Stage 4",
            )


def log_cross_boundary_pattern_conflict(
    pattern: Correction,
    conflicting_correction: Correction,
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
) -> None:
    """Log when a pattern is rejected due to cross-boundary conflict with a direct correction.

    Args:
        pattern: The pattern that was rejected
        conflicting_correction: The direct correction that conflicts with it
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
    """
    pattern_typo, pattern_word, pattern_boundary = pattern
    conflict_typo, conflict_word, conflict_boundary = conflicting_correction

    log_if_debug_correction(
        pattern,
        f"Pattern REJECTED - cross-boundary conflict with direct correction "
        f"'{conflict_typo}' → '{conflict_word}' (boundary: {conflict_boundary.value})",
        debug_words,
        debug_typo_matcher,
        "Stage 4",
    )

    log_if_debug_correction(
        conflicting_correction,
        f"Direct correction conflicts with pattern '{pattern_typo}' → '{pattern_word}' "
        f"(boundary: {pattern_boundary.value}) - pattern rejected",
        debug_words,
        debug_typo_matcher,
        "Stage 4",
    )


def log_pattern_replacement_restored(
    correction: Correction,
    pattern: Correction,
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
) -> None:
    """Log when a correction is restored because its pattern was rejected.

    Args:
        correction: The correction that was restored
        pattern: The pattern that was rejected
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
    """
    pattern_typo, pattern_word, _ = pattern
    log_if_debug_correction(
        correction,
        f"Restored to direct correction (pattern '{pattern_typo}' → '{pattern_word}' "
        f"was rejected due to cross-boundary conflict)",
        debug_words,
        debug_typo_matcher,
        "Stage 4",
    )


def log_pattern_substring_conflict_removal(
    removed_pattern: Correction,
    kept_pattern: Correction,
    debug_words: set[str],
    debug_typo_matcher: "DebugTypoMatcher | None",
) -> None:
    """Log when a pattern is removed due to substring conflict with another pattern.

    Args:
        removed_pattern: The pattern that was removed
        kept_pattern: The pattern that was kept
        debug_words: Set of words to debug
        debug_typo_matcher: Matcher for debug typos
    """
    removed_typo, removed_word, _ = removed_pattern
    kept_typo, kept_word, _ = kept_pattern

    log_if_debug_correction(
        removed_pattern,
        f"Pattern REMOVED - substring conflict with pattern '{kept_typo}' → '{kept_word}'",
        debug_words,
        debug_typo_matcher,
        "Stage 4",
    )

    log_if_debug_correction(
        kept_pattern,
        f"Pattern KEPT - blocks pattern '{removed_typo}' → '{removed_word}' "
        f"due to substring conflict",
        debug_words,
        debug_typo_matcher,
        "Stage 4",
    )
