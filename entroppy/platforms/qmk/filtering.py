"""QMK filtering logic for corrections."""

from collections import defaultdict

from entroppy.core import BoundaryType, Correction


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


def resolve_same_typo_conflicts(corrections: list[Correction]) -> tuple[list[Correction], list]:
    """
    When multiple boundaries exist for same typo text, keep least restrictive.

    Example: `riet` (NONE) and `:riet` (LEFT) both present
    → Keep `riet` (NONE) since it's less restrictive
    """
    typo_groups = defaultdict(list)
    for typo, word, boundary in corrections:
        typo_groups[typo].append((typo, word, boundary))

    boundary_priority = {
        BoundaryType.NONE: 0,
        BoundaryType.LEFT: 1,
        BoundaryType.RIGHT: 1,
        BoundaryType.BOTH: 2,
    }

    deduped = []
    conflicts = []

    for _, corrections_list in typo_groups.items():
        if len(corrections_list) == 1:
            deduped.append(corrections_list[0])
        else:
            sorted_by_restriction = sorted(corrections_list, key=lambda c: boundary_priority[c[2]])
            kept = sorted_by_restriction[0]
            deduped.append(kept)

            for removed in sorted_by_restriction[1:]:
                conflicts.append((removed[0], removed[1], kept[0], kept[1], removed[2]))

    return deduped, conflicts


def detect_conflicts_generic(
    corrections: list[Correction], conflict_check_fn
) -> tuple[list[Correction], list]:
    """
    Generic conflict detection for QMK constraints.

    Args:
        corrections: List of corrections to analyze
        conflict_check_fn: Function that takes (typo1, word1, typo2, word2)
                         and returns True if there's a conflict

    Returns:
        Tuple of (kept_corrections, conflicts)
    """
    # Sort all corrections by typo length (shortest first)
    sorted_corrections = sorted(corrections, key=lambda c: len(c[0]))

    kept = []
    conflicts = []
    removed_typos = set()

    for i, (typo1, word1, bound1) in enumerate(sorted_corrections):
        if typo1 in removed_typos:
            continue

        is_blocked = False
        # Check against all shorter typos (processed earlier)
        for typo2, word2, _ in sorted_corrections[:i]:
            if typo2 in removed_typos:
                continue

            if conflict_check_fn(typo1, word1, typo2, word2):
                is_blocked = True
                conflicts.append((typo1, word1, typo2, word2, bound1))
                removed_typos.add(typo1)
                break

        if not is_blocked:
            kept.append((typo1, word1, bound1))

    return kept, conflicts


def detect_suffix_conflicts(corrections: list[Correction]) -> tuple[list[Correction], list]:
    """
    Detect RTL suffix conflicts across ALL typos.

    QMK scans right-to-left. If typing "wriet":
    - Finds suffix "riet" first
    - Produces "w" + "rite" = "write"
    - So `riet -> rite` makes `wriet -> write` redundant

    This checks across all boundary types since QMK's RTL matching
    doesn't respect boundaries during the matching phase.
    """

    def check_suffix_conflict(typo1, word1, typo2, word2):
        # Check if typo1 ends with typo2 AND produces same correction
        if typo1.endswith(typo2) and typo1 != typo2:
            remaining = typo1[: -len(typo2)]
            expected = remaining + word2
            return expected == word1
        return False

    return detect_conflicts_generic(corrections, check_suffix_conflict)


def detect_substring_conflicts(corrections: list[Correction]) -> tuple[list[Correction], list]:
    """
    Detect general substring conflicts required by QMK.

    QMK's compiler rejects any case where one typo is a substring
    of another typo, regardless of position (prefix, suffix, or middle)
    or boundary type. This is a hard constraint in QMK's trie structure.

    Examples that QMK rejects:
    - "asbout" contains "sbout" as suffix
    - "beejn" contains "beej" as prefix
    - "xbeejy" contains "beej" in middle

    We keep the shorter typo and remove the longer one.
    """

    def check_substring_conflict(typo1: str, _word1: str, typo2: str, _word2: str) -> bool:
        # If typo2 is anywhere in typo1, QMK rejects it
        return typo2 in typo1 and typo1 != typo2

    return detect_conflicts_generic(corrections, check_substring_conflict)


def filter_corrections(
    corrections: list[Correction], allowed_chars: set[str]
) -> tuple[list[Correction], dict]:
    """
    Apply QMK-specific filtering.

    - Character set validation (only a-z and ')
    - Same-typo-text conflict detection (different boundaries)
    - Suffix conflict detection (RTL matching optimization)
    - Substring conflict detection (QMK's hard constraint)

    Args:
        corrections: List of corrections to filter
        allowed_chars: Set of allowed characters (for validation)

    Returns:
        Tuple of (filtered_corrections, metadata)
    """
    filtered, char_filtered = filter_character_set(corrections)
    deduped, same_typo_conflicts = resolve_same_typo_conflicts(filtered)
    after_suffix, suffix_conflicts = detect_suffix_conflicts(deduped)
    final, substring_conflicts = detect_substring_conflicts(after_suffix)

    metadata = {
        "total_input": len(corrections),
        "total_output": len(final),
        "filtered_count": len(corrections) - len(final),
        "filter_reasons": {
            "char_set": len(char_filtered),
            "same_typo_conflicts": len(same_typo_conflicts),
            "suffix_conflicts": len(suffix_conflicts),
            "substring_conflicts": len(substring_conflicts),
        },
        "char_filtered": char_filtered,
        "same_typo_conflicts": same_typo_conflicts,
        "suffix_conflicts": suffix_conflicts,
        "substring_conflicts": substring_conflicts,
    }

    return final, metadata
