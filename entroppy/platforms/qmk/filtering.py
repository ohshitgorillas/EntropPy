"""QMK filtering logic for corrections."""

from entroppy.core import Correction


def filter_character_set(corrections: list[Correction]) -> tuple[list[Correction], list]:
    """Filter out corrections with invalid characters and convert to lowercase."""
    filtered = []
    char_filtered = []

    for typo, word, boundary in corrections:
        if not all(c.isalpha() or c == "'" for c in typo.lower()):
            char_filtered.append((typo, word, "typo contains invalid chars"))
            continue
        if not all(c.isalpha() or c == "'" for c in word.lower()):
            char_filtered.append((typo, word, "word contains invalid chars"))
            continue

        filtered.append((typo.lower(), word.lower(), boundary))

    return filtered, char_filtered


def filter_corrections(
    corrections: list[Correction],
) -> tuple[list[Correction], dict]:
    """Apply QMK-specific filtering.

    Simplified to only perform essential filtering:
    - Character set validation (only a-z and ') - Required by QMK

    NOTE: Removed same-typo conflict resolution, suffix, and substring
    conflict detection because:
    1. QMK DOES support boundaries (via ':' notation), so we should keep
       all boundary variants, not just the least restrictive one
    2. The iterative solver (ConflictRemovalPass) already handles conflicts
       within boundary groups
    3. The previous logic was removing good corrections (like "teh" -> "the")
       and keeping bad ones
    4. QMK's compiler will reject any remaining substring conflicts anyway,
       so pre-filtering is unnecessary
    5. The "garbage correction removal" logic was flawed and could restore
       invalid corrections

    Args:
        corrections: List of corrections to filter

    Returns:
        Tuple of (filtered_corrections, metadata)
    """
    # Only perform character set filtering - QMK supports boundaries, so keep all
    final, char_filtered = filter_character_set(corrections)

    metadata = {
        "total_input": len(corrections),
        "total_output": len(final),
        "filtered_count": len(corrections) - len(final),
        "filter_reasons": {
            "char_set": len(char_filtered),
            "same_typo_conflicts": 0,  # Removed - QMK supports boundaries
            "suffix_conflicts": 0,  # Removed - no longer performed
            "substring_conflicts": 0,  # Removed - no longer performed
        },
        "char_filtered": char_filtered,
        "same_typo_conflicts": [],  # Removed - QMK supports boundaries
        "suffix_conflicts": [],  # Removed - no longer performed
        "substring_conflicts": [],  # Removed - no longer performed
    }

    return final, metadata
