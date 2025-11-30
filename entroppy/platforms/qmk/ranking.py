"""QMK ranking and scoring logic."""

from wordfreq import word_frequency

from entroppy.core import BoundaryType, Correction


def separate_by_type(
    corrections: list[Correction],
    patterns: list[Correction],
    pattern_replacements: dict[Correction, list[Correction]],
    user_words: set[str],
) -> tuple[list[Correction], list[Correction], list[Correction]]:
    """Separate corrections into user words, patterns, and direct corrections."""
    user_corrections = []
    pattern_corrections = []
    direct_corrections = []

    pattern_typos = {(p[0], p[1]) for p in patterns}

    replaced_by_patterns = set()
    for pattern in patterns:
        pattern_key = (pattern[0], pattern[1], pattern[2])
        if pattern_key in pattern_replacements:
            for replaced in pattern_replacements[pattern_key]:
                replaced_by_patterns.add((replaced[0], replaced[1]))

    for typo, word, boundary in corrections:
        if word in user_words:
            user_corrections.append((typo, word, boundary))
        elif (typo, word) in pattern_typos:
            pattern_corrections.append((typo, word, boundary))
        elif (typo, word) not in replaced_by_patterns:
            direct_corrections.append((typo, word, boundary))

    return user_corrections, pattern_corrections, direct_corrections


def score_patterns(
    pattern_corrections: list[Correction], pattern_replacements: dict[Correction, list[Correction]]
) -> list[tuple[float, str, str, BoundaryType]]:
    """Score patterns by sum of replaced word frequencies."""
    scores = []
    for typo, word, boundary in pattern_corrections:
        pattern_key = (typo, word, boundary)
        if pattern_key in pattern_replacements:
            total_freq = sum(
                word_frequency(replaced_word, "en")
                for _, replaced_word, _ in pattern_replacements[pattern_key]
            )
            scores.append((total_freq, typo, word, boundary))
    return scores


def score_direct_corrections(
    direct_corrections: list[Correction],
) -> list[tuple[float, str, str, BoundaryType]]:
    """Score direct corrections by word frequency."""
    scores = []
    for typo, word, boundary in direct_corrections:
        freq = word_frequency(word, "en")
        scores.append((freq, typo, word, boundary))
    return scores


def rank_corrections(
    corrections: list[Correction],
    patterns: list[Correction],
    pattern_replacements: dict[Correction, list[Correction]],
    user_words: set[str],
    max_corrections: int | None = None,
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

    Args:
        corrections: List of corrections to rank
        patterns: List of pattern corrections
        pattern_replacements: Dictionary mapping patterns to their replacements
        user_words: Set of user-defined words
        max_corrections: Optional limit on number of corrections

    Returns:
        Tuple of (ranked_corrections, user_corrections, pattern_scores, direct_scores, all_scored)
    """
    user_corrections, pattern_corrections, direct_corrections = separate_by_type(
        corrections, patterns, pattern_replacements, user_words
    )

    pattern_scores = score_patterns(pattern_corrections, pattern_replacements)
    direct_scores = score_direct_corrections(direct_corrections)

    all_scored = pattern_scores + direct_scores
    all_scored.sort(key=lambda x: x[0], reverse=True)

    ranked = user_corrections + [(t, w, b) for _, t, w, b in all_scored]

    # Apply max_corrections limit if specified
    if max_corrections:
        ranked = ranked[:max_corrections]

    return ranked, user_corrections, pattern_scores, direct_scores, all_scored
