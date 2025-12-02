"""Typo index for efficient conflict detection in QMK filtering."""

from collections import defaultdict
from typing import TYPE_CHECKING

from tqdm import tqdm

from entroppy.core import Correction

from .qmk_logging import log_garbage_correction_removal

if TYPE_CHECKING:
    from entroppy.utils.debug import DebugTypoMatcher


class TypoIndex:
    """Index for efficient conflict detection between typos.

    Uses reverse indexes to enable O(1) lookups instead of O(n) linear searches.
    Builds indexes only for what's actually needed, avoiding expensive substring
    generation that was never used.

    Attributes:
        typo_to_correction: Dict mapping typo text to its correction tuple
        typo_by_length: Dict mapping length to list of typos of that length
    """

    def __init__(self, corrections: list[Correction]) -> None:
        """Build indexes from a list of corrections.

        Args:
            corrections: List of (typo, word, boundary) tuples
        """
        self.typo_to_correction: dict[str, Correction] = {}
        # Group typos by length for efficient processing
        # (not currently used but useful for future optimizations)
        self.typo_by_length: dict[int, list[str]] = defaultdict(list)

        # Build typo to correction mapping
        for typo, word, boundary in corrections:
            self.typo_to_correction[typo] = (typo, word, boundary)
            self.typo_by_length[len(typo)].append(typo)

    def find_suffix_conflicts(
        self, corrections: list[Correction], verbose: bool = False
    ) -> tuple[list[Correction], list]:
        """Find suffix conflicts using the reverse suffix index.

        A suffix conflict occurs when:
        - typo1 ends with typo2 (typo1 is longer)
        - The correction would produce the same result

        Uses reverse suffix index for O(1) lookups: for each typo, check if it ends
        with any shorter typo that we've already processed.

        Args:
            corrections: List of corrections to check
            verbose: Whether to show progress bar

        Returns:
            Tuple of (kept_corrections, conflicts)
        """
        # Sort by length (shortest first) for processing order
        sorted_corrections = sorted(corrections, key=lambda c: len(c[0]))

        kept = []
        conflicts = []
        removed_typos = set()

        # Track shorter typos we've seen: typo -> (typo, word, boundary)
        shorter_typos: dict[str, Correction] = {}

        corrections_iter = sorted_corrections
        if verbose:
            corrections_iter = tqdm(
                sorted_corrections,
                desc="    Checking suffix conflicts",
                unit="correction",
                leave=False,
            )

        for typo1, word1, bound1 in corrections_iter:
            if typo1 in removed_typos:
                continue

            is_blocked = False

            # Use reverse suffix index: check all suffixes of typo1
            # For each suffix, check if we've seen a shorter typo with that exact text
            for i in range(len(typo1)):
                suffix = typo1[i:]
                if suffix in shorter_typos and suffix != typo1:
                    # Found a shorter typo that matches this suffix
                    typo2, word2, _ = shorter_typos[suffix]
                    if typo2 in removed_typos:
                        continue

                    # Verify it would produce the same correction
                    remaining = typo1[: -len(typo2)]
                    expected = remaining + word2
                    if expected == word1:
                        is_blocked = True
                        conflicts.append((typo1, word1, typo2, word2, bound1))
                        removed_typos.add(typo1)
                        break

            if not is_blocked:
                kept.append((typo1, word1, bound1))
                shorter_typos[typo1] = (typo1, word1, bound1)

        return kept, conflicts

    def find_substring_conflicts(
        self,
        corrections: list[Correction],
        verbose: bool = False,
        debug_words: set[str] | None = None,
        debug_typo_matcher: "DebugTypoMatcher | None" = None,
    ) -> tuple[list[Correction], list]:
        """Find substring conflicts - QMK's hard constraint.

        A substring conflict occurs when:
        - typo2 is a substring of typo1 (typo1 is longer)
        - Can appear as prefix, suffix, or middle substring
        - QMK's compiler rejects ANY substring relationship regardless of position
          or boundary type (hard constraint in QMK's trie structure)

        This catches all substring conflicts that weren't already removed by
        find_suffix_conflicts (which only removes conflicts where the pattern
        would produce the correct result). QMK rejects ALL substring relationships.

        However, we check if keeping the shorter typo would produce garbage corrections.
        If the shorter typo would produce garbage when matching the longer typo, we
        remove the shorter typo instead of the longer one.

        Args:
            corrections: List of corrections to check
            verbose: Whether to show progress bar
            debug_words: Set of words to debug (exact matches)
            debug_typo_matcher: Matcher for debug typos (with wildcards/boundaries)

        Returns:
            Tuple of (kept_corrections, conflicts)
        """
        # Sort by length (shortest first) for processing order
        sorted_corrections = sorted(corrections, key=lambda c: len(c[0]))

        kept = []
        conflicts = []
        removed_typos = set()

        # Track shorter typos we've seen: typo -> (typo, word, boundary)
        shorter_typos: dict[str, Correction] = {}

        corrections_iter = sorted_corrections
        if verbose:
            corrections_iter = tqdm(
                sorted_corrections,
                desc="    Checking substring conflicts",
                unit="correction",
                leave=False,
            )

        for typo1, word1, bound1 in corrections_iter:
            if typo1 in removed_typos:
                continue

            is_blocked = False

            # Check if typo1 contains any shorter typo as a substring (prefix, suffix, or middle)
            # Check all shorter typos we've seen so far
            for typo2, word2, _ in list(
                shorter_typos.values()
            ):  # Use list() to avoid modification during iteration
                if typo2 in removed_typos:
                    continue

                # Check if typo2 is a substring of typo1 (anywhere: prefix, suffix, or middle)
                if typo2 in typo1 and typo2 != typo1:
                    # Check if keeping typo2 would produce garbage for typo1
                    # For QMK RTL matching, find the rightmost occurrence
                    # (where it would match first)
                    last_pos = typo1.rfind(typo2)
                    if last_pos != -1:
                        # Calculate what would happen if typo2 triggers on typo1 at this position
                        # Replace typo2 with word2 in typo1
                        before = typo1[:last_pos]
                        after = typo1[last_pos + len(typo2) :]
                        result = before + word2 + after

                        # If this would produce garbage (not the intended correction),
                        # remove typo2 instead
                        if result != word1:
                            # Remove the shorter typo (typo2) because it would produce garbage
                            # Don't add to conflicts - this isn't a blocking relationship,
                            # we're just removing a problematic correction

                            # Debug logging for garbage corrections
                            if debug_words or debug_typo_matcher:
                                typo2_correction = (typo2, word2, bound1)
                                typo1_correction = (typo1, word1, bound1)
                                log_garbage_correction_removal(
                                    typo2_correction,
                                    typo1_correction,
                                    result,
                                    debug_words or set(),
                                    debug_typo_matcher,
                                )

                            removed_typos.add(typo2)
                            # Remove typo2 from shorter_typos if it was already added
                            if typo2 in shorter_typos:
                                del shorter_typos[typo2]
                            # Remove typo2 from kept if it was already added
                            kept = [c for c in kept if c[0] != typo2]
                            # Continue checking other shorter typos
                            # (typo1 might still be blocked by others)
                            continue

                    # If it would produce the correct result, keep typo2 and remove typo1
                    is_blocked = True
                    conflicts.append((typo1, word1, typo2, word2, bound1))
                    removed_typos.add(typo1)
                    break

            if not is_blocked:
                kept.append((typo1, word1, bound1))
                shorter_typos[typo1] = (typo1, word1, bound1)

        return kept, conflicts
