"""Typo index for efficient conflict detection in QMK filtering."""

from entroppy.core import Correction


class TypoIndex:
    """Index for efficient conflict detection between typos.

    Pre-builds indexes to avoid O(n²) nested loop comparisons.
    Uses suffix and substring indexes to enable O(1) or O(log n) lookups
    instead of O(n) linear searches.

    Attributes:
        suffix_index: Dict mapping each typo to set of all its suffixes
        substring_index: Dict mapping each typo to set of all its substrings
        typo_to_correction: Dict mapping typo text to its correction tuple
    """

    def __init__(self, corrections: list[Correction]) -> None:
        """Build indexes from a list of corrections.

        Args:
            corrections: List of (typo, word, boundary) tuples
        """
        self.typo_to_correction: dict[str, Correction] = {}
        self.suffix_index: dict[str, set[str]] = {}
        self.substring_index: dict[str, set[str]] = {}

        # Build typo to correction mapping
        for typo, word, boundary in corrections:
            self.typo_to_correction[typo] = (typo, word, boundary)

        # Build suffix and substring indexes for each typo
        for typo, _, _ in corrections:
            # Build suffix index: all suffixes of this typo
            suffixes = set()
            for i in range(len(typo)):
                suffix = typo[i:]
                if suffix:  # Exclude empty string
                    suffixes.add(suffix)
            self.suffix_index[typo] = suffixes

            # Build substring index: all substrings of this typo
            substrings = set()
            for i in range(len(typo)):
                for j in range(i + 1, len(typo) + 1):
                    substring = typo[i:j]
                    if substring and substring != typo:  # Exclude empty and exact match
                        substrings.add(substring)
            self.substring_index[typo] = substrings

    def find_suffix_conflicts(self, corrections: list[Correction]) -> tuple[list[Correction], list]:
        """Find suffix conflicts using the index.

        A suffix conflict occurs when:
        - typo1 ends with typo2 (typo1 is longer)
        - The correction would produce the same result

        Uses reverse index: for each shorter typo, check if longer typos end with it.

        Args:
            corrections: List of corrections to check (should be sorted by length)

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

        for typo1, word1, bound1 in sorted_corrections:
            if typo1 in removed_typos:
                continue

            is_blocked = False

            # Check if typo1 ends with any shorter typo we've seen
            # Iterate through shorter typos and check if typo1 ends with them
            # This is O(k) where k is number of shorter typos, but with early termination
            for typo2, word2, _ in shorter_typos.values():
                if typo2 in removed_typos:
                    continue

                # Check if typo1 ends with typo2 (typo1 is longer)
                if typo1.endswith(typo2) and typo1 != typo2:
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
        self, corrections: list[Correction]
    ) -> tuple[list[Correction], list]:
        """Find substring conflicts using the index.

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

        Uses substring index for efficient lookup: check if shorter typos
        appear as suffixes of longer typos.

        Args:
            corrections: List of corrections to check (should be sorted by length)

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

        for typo1, word1, bound1 in sorted_corrections:
            if typo1 in removed_typos:
                continue

            is_blocked = False

            # For QMK (right-to-left), only check if shorter typos appear as SUFFIXES
            # QMK scans right-to-left, so it would see suffixes first
            for typo2, word2, _ in shorter_typos.values():
                if typo2 in removed_typos:
                    continue

                # Only block if shorter typo appears as SUFFIX (at the end)
                # This is where QMK would match first when scanning right-to-left
                if typo1.endswith(typo2) and typo1 != typo2:
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
