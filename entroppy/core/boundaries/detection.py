"""Boundary detection functions."""

from entroppy.core.boundaries.types import BoundaryIndex, BoundaryType


def _check_typo_in_wordset(
    typo: str,
    check_type: str,
    index: BoundaryIndex,
) -> bool:
    """Check if typo matches any word in the set based on check type.

    Args:
        typo: The typo string to check
        check_type: Type of check - 'substring', 'prefix', or 'suffix'
        index: Pre-built index for faster lookups

    Returns:
        True if typo matches any word according to check_type
    """
    if check_type == "substring":
        return typo in index.substring_set
    if check_type == "prefix":
        # Check if typo is a prefix of any word (excluding exact match)
        if typo in index.prefix_index:
            matching_words = index.prefix_index[typo]
            # Exclude exact match
            return any(word != typo for word in matching_words)
        return False
    if check_type == "suffix":
        # Check if typo is a suffix of any word (excluding exact match)
        if typo in index.suffix_index:
            matching_words = index.suffix_index[typo]
            # Exclude exact match
            return any(word != typo for word in matching_words)
        return False

    return False


def is_substring_of_any(typo: str, index: BoundaryIndex) -> bool:
    """Check if typo is a substring of any word.

    Args:
        typo: The typo string to check
        index: Pre-built index for faster lookups

    Returns:
        True if typo is a substring of any word (excluding exact matches)
    """
    # First check the pre-built substring_set for fast lookup
    if typo in index.substring_set:
        return True
    # Also do a direct check against all words in case substring_set is incomplete
    # This is a fallback for when validation set doesn't include all possible words
    for word in index.word_set:
        if typo in word and typo != word:
            return True
    return False


def would_trigger_at_start(typo: str, index: BoundaryIndex) -> bool:
    """Check if typo appears as prefix.

    Args:
        typo: The typo string to check
        index: Pre-built index for faster lookups

    Returns:
        True if typo appears as a prefix of any word (excluding exact matches)
    """
    return _check_typo_in_wordset(typo, "prefix", index)


def would_trigger_at_end(typo: str, index: BoundaryIndex) -> bool:
    """Check if typo appears as suffix.

    Args:
        typo: The typo string to check
        index: Pre-built index for faster lookups

    Returns:
        True if typo appears as a suffix of any word (excluding exact matches)
    """
    return _check_typo_in_wordset(typo, "suffix", index)


def determine_boundaries(
    typo: str,
    validation_index: BoundaryIndex,
    source_index: BoundaryIndex,
) -> BoundaryType:
    """Determine what boundaries are needed for a typo.

    Args:
        typo: The typo string
        validation_index: Pre-built index for validation set
        source_index: Pre-built index for source words

    Returns:
        BoundaryType indicating what boundaries are needed
    """
    # Check if typo appears as substring in other contexts
    is_substring_source = is_substring_of_any(typo, source_index)
    is_substring_validation = is_substring_of_any(typo, validation_index)

    if not is_substring_source and not is_substring_validation:
        return BoundaryType.NONE

    appears_as_prefix = would_trigger_at_start(typo, validation_index)
    appears_as_suffix = would_trigger_at_end(typo, validation_index)

    if not appears_as_prefix and not appears_as_suffix:
        return BoundaryType.BOTH
    if appears_as_suffix and not appears_as_prefix:
        return BoundaryType.LEFT
    if appears_as_prefix and not appears_as_suffix:
        return BoundaryType.RIGHT
    return BoundaryType.BOTH
