"""Tier separation for QMK ranking."""

from typing import TYPE_CHECKING

from entroppy.core import Correction
from entroppy.platforms.qmk.qmk_logging import log_separation_by_type

if TYPE_CHECKING:
    from entroppy.utils.debug import DebugTypoMatcher


def _build_pattern_sets(
    patterns: list[Correction], pattern_replacements: dict[Correction, list[Correction]]
) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    """Build pattern sets for caching.

    Args:
        patterns: List of pattern corrections
        pattern_replacements: Dictionary mapping patterns to their replacements

    Returns:
        Tuple of (pattern_typos, replaced_by_patterns) sets
    """
    pattern_typos = {(p[0], p[1]) for p in patterns}

    replaced_by_patterns = set()
    for pattern in patterns:
        pattern_key = (pattern[0], pattern[1], pattern[2])
        if pattern_key in pattern_replacements:
            for replaced in pattern_replacements[pattern_key]:
                replaced_by_patterns.add((replaced[0], replaced[1]))

    return pattern_typos, replaced_by_patterns


def separate_by_type(
    corrections: list[Correction],
    patterns: list[Correction],
    pattern_replacements: dict[Correction, list[Correction]],
    user_words: set[str],
    cached_pattern_typos: set[tuple[str, str]] | None = None,
    cached_replaced_by_patterns: set[tuple[str, str]] | None = None,
    debug_words: set[str] | None = None,
    debug_typo_matcher: "DebugTypoMatcher | None" = None,
) -> tuple[list[Correction], list[Correction], list[Correction]]:
    """Separate corrections into user words, patterns, and direct corrections.

    Args:
        corrections: List of corrections to separate
        patterns: List of pattern corrections
        pattern_replacements: Dictionary mapping patterns to their replacements
        user_words: Set of user-defined words
        cached_pattern_typos: Optional cached set of (typo, word) tuples for patterns
        cached_replaced_by_patterns: Optional cached set of (typo, word) tuples replaced by patterns
        debug_words: Set of words to debug (exact matches)
        debug_typo_matcher: Matcher for debug typos (with wildcards/boundaries)

    Returns:
        Tuple of (user_corrections, pattern_corrections, direct_corrections)
    """
    user_corrections = []
    pattern_corrections = []
    direct_corrections = []

    # Use cached sets if provided, otherwise build them
    if cached_pattern_typos is not None:
        pattern_typos = cached_pattern_typos
    else:
        pattern_typos = {(p[0], p[1]) for p in patterns}

    if cached_replaced_by_patterns is not None:
        replaced_by_patterns = cached_replaced_by_patterns
    else:
        replaced_by_patterns = set()
        for pattern in patterns:
            pattern_key = (pattern[0], pattern[1], pattern[2])
            if pattern_key in pattern_replacements:
                for replaced in pattern_replacements[pattern_key]:
                    replaced_by_patterns.add((replaced[0], replaced[1]))

    for typo, word, boundary in corrections:
        correction = (typo, word, boundary)

        if word in user_words:
            user_corrections.append((typo, word, boundary))
            log_separation_by_type(
                correction,
                "user word",
                f"Separated as user word (infinite priority, tier 0, "
                f"total user words: {len(user_corrections)})",
                debug_words or set(),
                debug_typo_matcher,
            )
        elif (typo, word) in pattern_typos:
            pattern_corrections.append((typo, word, boundary))
            log_separation_by_type(
                correction,
                "pattern",
                f"Separated as pattern (tier 1, scored by sum of replacement "
                f"frequencies, total patterns: {len(pattern_corrections)})",
                debug_words or set(),
                debug_typo_matcher,
            )
        elif (typo, word) not in replaced_by_patterns:
            direct_corrections.append((typo, word, boundary))
            log_separation_by_type(
                correction,
                "direct",
                f"Separated as direct correction (tier 2, scored by word frequency, "
                f"total direct: {len(direct_corrections)})",
                debug_words or set(),
                debug_typo_matcher,
            )
        else:
            # Correction was replaced by a pattern
            log_separation_by_type(
                correction,
                "replaced",
                "Separated - replaced by pattern (not included in ranking)",
                debug_words or set(),
                debug_typo_matcher,
            )

    return user_corrections, pattern_corrections, direct_corrections
