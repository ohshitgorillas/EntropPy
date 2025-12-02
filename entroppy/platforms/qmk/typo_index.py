"""Typo index for efficient conflict detection in QMK filtering."""

from collections import defaultdict

from tqdm import tqdm

from entroppy.core import Correction


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
        self, corrections: list[Correction], verbose: bool = False
    ) -> tuple[list[Correction], list]:
        """Find substring conflicts using the reverse suffix index.

        A substring conflict occurs when:
        - typo2 is a substring of typo1 (typo1 is longer)
        - For QMK (right-to-left matching), typo2 must appear as a SUFFIX of typo1
          (at the end), since QMK scans right-to-left and would see the suffix first
        - Applying the pattern (typo2 → word2) to typo1 must produce word1
          (i.e., remaining + word2 == word1)
        - This is a hard QMK constraint, but only if the pattern produces correct result

        If the pattern would produce an incorrect result, the longer typo is kept
        (e.g., `toin → tion` pattern should NOT block `washingtoin → washington` because
        applying the pattern would produce `washingtion` ≠ `washington`).

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
                desc="    Checking substring conflicts",
                unit="correction",
                leave=False,
            )

        for typo1, word1, bound1 in corrections_iter:
            if typo1 in removed_typos:
                continue

            is_blocked = False

            # Use reverse suffix index: check all suffixes of typo1
            # For each suffix, check if we've seen a shorter typo with that exact text
            # For QMK (right-to-left), only check if shorter typos appear as SUFFIXES
            for i in range(len(typo1)):
                suffix = typo1[i:]
                if suffix in shorter_typos and suffix != typo1:
                    # Found a shorter typo that matches this suffix
                    typo2, word2, _ = shorter_typos[suffix]
                    if typo2 in removed_typos:
                        continue

                    # Verify it would produce the same correction
                    # If applying the pattern doesn't produce the expected result,
                    # it's not a valid conflict - keep the longer typo
                    remaining = typo1[: -len(typo2)]
                    expected = remaining + word2
                    if expected == word1:
                        # Valid conflict: pattern produces same result
                        is_blocked = True
                        conflicts.append((typo1, word1, typo2, word2, bound1))
                        removed_typos.add(typo1)
                        break
                    # Invalid conflict: pattern would produce wrong result, keep longer typo

            if not is_blocked:
                kept.append((typo1, word1, bound1))
                shorter_typos[typo1] = (typo1, word1, bound1)

        return kept, conflicts
