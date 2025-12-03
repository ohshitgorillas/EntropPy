"""QMK ranking and scoring logic."""

from typing import TYPE_CHECKING

from tqdm import tqdm

from entroppy.core import BoundaryType, Correction
from entroppy.utils.debug import is_debug_correction
from entroppy.utils.helpers import cached_word_frequency

from .qmk_logging import (log_direct_scoring, log_max_corrections_limit,
                          log_pattern_scoring, log_ranking_position,
                          log_separation_by_type)

if TYPE_CHECKING:
    from entroppy.utils.debug import DebugTypoMatcher


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


def score_patterns(
    pattern_corrections: list[Correction],
    pattern_replacements: dict[Correction, list[Correction]],
    verbose: bool = False,
    debug_words: set[str] | None = None,
    debug_typo_matcher: "DebugTypoMatcher | None" = None,
) -> list[tuple[float, str, str, BoundaryType]]:
    """Score patterns by sum of replaced word frequencies."""
    scores = []
    if verbose:
        pattern_iter: list[Correction] = list(
            tqdm(pattern_corrections, desc="  Scoring patterns", unit="pattern", leave=False)
        )
    else:
        pattern_iter = pattern_corrections

    for typo, word, boundary in pattern_iter:
        pattern_key = (typo, word, boundary)
        correction = (typo, word, boundary)

        if pattern_key in pattern_replacements:
            replacements = pattern_replacements[pattern_key]
            total_freq = sum(
                cached_word_frequency(replaced_word, "en") for _, replaced_word, _ in replacements
            )
            scores.append((total_freq, typo, word, boundary))
            replacement_words = [w for _, w, _ in replacements]
            replacement_list = ", ".join(replacement_words[:5])
            if len(replacement_words) > 5:
                replacement_list += "..."
            log_pattern_scoring(
                correction,
                total_freq,
                len(replacements),
                replacement_list,
                debug_words or set(),
                debug_typo_matcher,
            )
    return scores


def score_direct_corrections(
    direct_corrections: list[Correction],
    verbose: bool = False,
    debug_words: set[str] | None = None,
    debug_typo_matcher: "DebugTypoMatcher | None" = None,
) -> list[tuple[float, str, str, BoundaryType]]:
    """Score direct corrections by word frequency."""
    scores = []
    if verbose:
        direct_iter: list[Correction] = list(
            tqdm(
                direct_corrections,
                desc="  Scoring direct corrections",
                unit="correction",
                leave=False,
            )
        )
    else:
        direct_iter = direct_corrections

    for typo, word, boundary in direct_iter:
        correction = (typo, word, boundary)

        freq = cached_word_frequency(word, "en")
        scores.append((freq, typo, word, boundary))
        log_direct_scoring(correction, freq, debug_words or set(), debug_typo_matcher)
    return scores


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
    """
    Rank corrections by QMK-specific usefulness.

    Three-tier system:
    1. User words (infinite priority)
    2. Patterns (scored by sum of replaced word frequencies)
    3. Direct corrections (scored by word frequency)

    Optimized to use a single unified sort with tier-based comparison instead of
    separate sorts for patterns and direct corrections.

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

    # Score all corrections with unified tier-based scoring
    # Tier 0: User words (handled separately, infinite priority)
    # Tier 1: Patterns (scored by sum of replacement frequencies)
    # Tier 2: Direct corrections (scored by word frequency)
    all_scored_items = []

    # Score patterns
    pattern_scores = score_patterns(
        pattern_corrections, pattern_replacements, verbose, debug_words, debug_typo_matcher
    )
    for score, typo, word, boundary in pattern_scores:
        # Tier 1 for patterns
        all_scored_items.append((1, score, typo, word, boundary))

    # Score direct corrections
    direct_scores = score_direct_corrections(
        direct_corrections, verbose, debug_words, debug_typo_matcher
    )
    for score, typo, word, boundary in direct_scores:
        # Tier 2 for direct corrections
        all_scored_items.append((2, score, typo, word, boundary))

    # Single unified sort: by tier (ascending), then by score (descending)
    # This ensures patterns (tier 1) come before direct (tier 2), and within each tier,
    # higher scores come first
    all_scored_items.sort(key=lambda x: (x[0], -x[1]))

    # Extract the scored items in sorted order (without tier)
    all_scored = [
        (score, typo, word, boundary) for _, score, typo, word, boundary in all_scored_items
    ]

    # Build ranked list: user words first, then sorted patterns and direct corrections
    ranked = user_corrections + [(t, w, b) for _, t, w, b in all_scored]

    # Debug logging for final ranking position with context
    if debug_words or debug_typo_matcher:
        # Build tier boundaries for context
        user_count = len(user_corrections)
        pattern_count = len(pattern_scores)
        direct_count = len(direct_scores)

        for i, correction in enumerate(ranked):
            if is_debug_correction(correction, debug_words or set(), debug_typo_matcher):
                typo, word, boundary = correction

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
                    # Find score for this pattern
                    pattern_score = next(
                        (s for s, t, w, b in pattern_scores if (t, w, b) == correction), None
                    )
                    score_info = (
                        f"score: {pattern_score:.2e}"
                        if pattern_score is not None
                        else "score: unknown"
                    )
                else:
                    tier = 2
                    tier_pos = i - user_count - pattern_count + 1
                    tier_name = "direct corrections"
                    tier_total = direct_count
                    # Find score for this direct correction
                    direct_score = next(
                        (s for s, t, w, b in direct_scores if (t, w, b) == correction), None
                    )
                    score_info = (
                        f"score: {direct_score:.2e}"
                        if direct_score is not None
                        else "score: unknown"
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
                    debug_words or set(),
                    debug_typo_matcher,
                )

    # Apply max_corrections limit if specified
    if max_corrections:
        if debug_words or debug_typo_matcher:
            # Log if any debug corrections are cut off by the limit
            for i, correction in enumerate(ranked):
                if is_debug_correction(correction, debug_words or set(), debug_typo_matcher):
                    log_max_corrections_limit(
                        correction,
                        i + 1,
                        max_corrections,
                        len(ranked),
                        i < max_corrections,
                        debug_words or set(),
                        debug_typo_matcher,
                    )
        ranked = ranked[:max_corrections]

    return ranked, user_corrections, pattern_scores, direct_scores, all_scored
