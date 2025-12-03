"""QMK filtering logic for corrections."""

from collections import defaultdict
from typing import TYPE_CHECKING

from loguru import logger
from tqdm import tqdm

from entroppy.core import BoundaryType, Correction
from entroppy.platforms.qmk.typo_index import TypoIndex

from .qmk_logging import (log_character_filtering, log_same_typo_conflict,
                          log_substring_conflict, log_suffix_conflict)

if TYPE_CHECKING:
    from entroppy.utils.debug import DebugTypoMatcher


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


def filter_character_set_and_resolve_same_typo(
    corrections: list[Correction],
    verbose: bool = False,
    debug_words: set[str] | None = None,
    debug_typo_matcher: "DebugTypoMatcher | None" = None,
) -> tuple[list[Correction], list, list]:
    """
    Combined pass: filter invalid characters and resolve same-typo conflicts.

    This combines two operations in a single pass to reduce iterations:
    1. Character set validation (only a-z and ')
    2. Same-typo conflict resolution (keep least restrictive boundary)

    Args:
        corrections: List of corrections to filter
        verbose: Whether to show progress bar
        debug_words: Set of words to debug (exact matches)
        debug_typo_matcher: Matcher for debug typos (with wildcards/boundaries)

    Returns:
        Tuple of (filtered_corrections, char_filtered, same_typo_conflicts)
    """
    char_filtered = []
    typo_groups = defaultdict(list)

    # Single pass: filter characters and group by typo
    if verbose:
        corrections_iter: list[Correction] = list(
            tqdm(corrections, desc="  Filtering characters", unit="correction", leave=False)
        )
    else:
        corrections_iter = corrections

    for typo, word, boundary in corrections_iter:
        correction = (typo, word, boundary)

        # Character validation
        if not all(c.isalpha() or c == "'" for c in typo.lower()):
            char_filtered.append((typo, word, "typo contains invalid chars"))
            log_character_filtering(
                correction,
                "typo contains invalid characters",
                debug_words or set(),
                debug_typo_matcher,
            )
            continue
        if not all(c.isalpha() or c == "'" for c in word.lower()):
            char_filtered.append((typo, word, "word contains invalid chars"))
            log_character_filtering(
                correction,
                "word contains invalid characters",
                debug_words or set(),
                debug_typo_matcher,
            )
            continue

        # Convert to lowercase and group by typo
        typo_lower = typo.lower()
        word_lower = word.lower()
        typo_groups[typo_lower].append((typo_lower, word_lower, boundary))

    # Resolve same-typo conflicts
    boundary_priority = {
        BoundaryType.NONE: 0,
        BoundaryType.LEFT: 1,
        BoundaryType.RIGHT: 1,
        BoundaryType.BOTH: 2,
    }

    deduped = []
    same_typo_conflicts = []

    for _, corrections_list in typo_groups.items():
        if len(corrections_list) == 1:
            deduped.append(corrections_list[0])
        else:
            sorted_by_restriction = sorted(corrections_list, key=lambda c: boundary_priority[c[2]])
            kept = sorted_by_restriction[0]
            deduped.append(kept)

            for removed in sorted_by_restriction[1:]:
                same_typo_conflicts.append((removed[0], removed[1], kept[0], kept[1], removed[2]))
                # Debug logging for same-typo conflicts
                removed_correction = (removed[0], removed[1], removed[2])
                kept_correction = (kept[0], kept[1], kept[2])
                log_same_typo_conflict(
                    removed_correction,
                    kept_correction,
                    debug_words or set(),
                    debug_typo_matcher,
                )

    return deduped, char_filtered, same_typo_conflicts


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


def detect_suffix_conflicts(
    corrections: list[Correction],
    verbose: bool = False,
    debug_words: set[str] | None = None,
    debug_typo_matcher: "DebugTypoMatcher | None" = None,
) -> tuple[list[Correction], list]:
    """
    Detect RTL suffix conflicts across ALL typos.

    QMK scans right-to-left. If typing "wriet":
    - Finds suffix "riet" first
    - Produces "w" + "rite" = "write"
    - So `riet -> rite` makes `wriet -> write` redundant

    This checks across all boundary types since QMK's RTL matching
    doesn't respect boundaries during the matching phase.

    Uses TypoIndex for optimized O(n log n) conflict detection instead of O(n²).

    Args:
        corrections: List of corrections to check
        verbose: Whether to show progress bar
        debug_words: Set of words to debug (exact matches)
        debug_typo_matcher: Matcher for debug typos (with wildcards/boundaries)
    """
    if not corrections:
        return [], []

    # Build index once for efficient lookups
    if verbose:
        logger.info("  Building suffix conflict index...")
    index = TypoIndex(corrections)

    filtered, conflicts = index.find_suffix_conflicts(corrections, verbose)

    # Debug logging for suffix conflicts
    if debug_words or debug_typo_matcher:
        for long_typo, long_word, short_typo, short_word, boundary in conflicts:
            long_correction = (long_typo, long_word, boundary)
            short_correction = (short_typo, short_word, boundary)
            log_suffix_conflict(
                long_correction,
                short_correction,
                debug_words or set(),
                debug_typo_matcher,
            )

    return filtered, conflicts


def detect_substring_conflicts(
    corrections: list[Correction],
    verbose: bool = False,
    debug_words: set[str] | None = None,
    debug_typo_matcher: "DebugTypoMatcher | None" = None,
) -> tuple[list[Correction], list]:
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

    Uses TypoIndex for optimized O(n log n) conflict detection instead of O(n²).

    Args:
        corrections: List of corrections to check
        verbose: Whether to show progress bar
        debug_words: Set of words to debug (exact matches)
        debug_typo_matcher: Matcher for debug typos (with wildcards/boundaries)
    """
    if not corrections:
        return [], []

    # Build index once for efficient lookups
    if verbose:
        logger.info("  Building substring conflict index...")
    index = TypoIndex(corrections)

    filtered, conflicts = index.find_substring_conflicts(
        corrections, verbose, debug_words, debug_typo_matcher
    )

    # Debug logging for substring conflicts
    # Conflict tuple format: (removed_typo, removed_word, kept_typo, kept_word, boundary)
    # Only includes conflicts where shorter typo is kept and blocks longer one
    # (Conflicts where shorter typo produces garbage are not added to conflicts list)
    if debug_words or debug_typo_matcher:
        for removed_typo, removed_word, kept_typo, kept_word, boundary in conflicts:
            removed_correction = (removed_typo, removed_word, boundary)
            kept_correction = (kept_typo, kept_word, boundary)
            log_substring_conflict(
                removed_correction,
                kept_correction,
                debug_words or set(),
                debug_typo_matcher,
            )

    return filtered, conflicts


def filter_corrections(
    corrections: list[Correction],
) -> tuple[list[Correction], dict]:
    """
    Apply QMK-specific filtering.

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
