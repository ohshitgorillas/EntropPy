"""Boundary types and index classes."""

from enum import Enum
from multiprocessing import Pool


def _check_typo_substring_worker(typo: str, word_list: list[str]) -> tuple[str, bool]:
    """Worker function to check if a typo is a substring of any word.

    Args:
        typo: Typo string to check
        word_list: List of words to check against

    Returns:
        Tuple of (typo, True if it is a substring)
    """
    return typo, any(typo in word and typo != word for word in word_list)


class BoundaryType(Enum):
    """Boundary types for Espanso matches."""

    NONE = "none"  # No boundaries - triggers anywhere
    LEFT = "left"  # Left boundary only - must be at word start
    RIGHT = "right"  # Right boundary only - must be at word end
    BOTH = "both"  # Both boundaries - standalone word only


class BoundaryIndex:
    """Index for efficient boundary detection queries.

    Pre-builds indexes for prefix, suffix, and substring checks to avoid
    linear searches through word sets. Provides O(1) or O(log n) lookups
    instead of O(n) linear scans.

    Attributes:
        prefix_index: Dict mapping prefixes to sets of words starting with that prefix
        suffix_index: Dict mapping suffixes to sets of words ending with that suffix
        substring_set: Set of all substrings (excluding exact matches) from all words
        word_set: Original word set for reference
    """

    def _build_prefix_index(self, word: str) -> None:
        """Build prefix index entries for a word."""
        for i in range(1, len(word) + 1):
            prefix = word[:i]
            if prefix not in self.prefix_index:
                self.prefix_index[prefix] = set()
            self.prefix_index[prefix].add(word)

    def _build_suffix_index(self, word: str) -> None:
        """Build suffix index entries for a word."""
        for i in range(len(word)):
            suffix = word[i:]
            if suffix not in self.suffix_index:
                self.suffix_index[suffix] = set()
            self.suffix_index[suffix].add(word)

    def _build_substring_set(self, word: str) -> None:
        """Build substring set entries for a word."""
        for i in range(len(word)):
            for j in range(i + 1, len(word) + 1):
                substring = word[i:j]
                if substring != word:  # Exclude exact matches
                    self.substring_set.add(substring)

    def __init__(self, word_set: set[str] | frozenset[str]) -> None:
        """Build indexes from a word set.

        Args:
            word_set: Set of words to build indexes from
        """
        self.word_set = word_set
        self.prefix_index: dict[str, set[str]] = {}
        self.suffix_index: dict[str, set[str]] = {}
        self.substring_set: set[str] = set()

        # Build indexes for each word
        for word in word_set:
            self._build_prefix_index(word)
            self._build_suffix_index(word)
            self._build_substring_set(word)

    def batch_check_start(self, typos: list[str]) -> dict[str, bool]:
        """Batch check if typos appear as prefixes of any word.

        Args:
            typos: List of typo strings to check

        Returns:
            Dict mapping typo -> True if it appears as a prefix (excluding exact matches)
        """
        results: dict[str, bool] = {}
        for typo in typos:
            if typo in self.prefix_index:
                matching_words = self.prefix_index[typo]
                # Exclude exact match
                results[typo] = any(word != typo for word in matching_words)
            else:
                results[typo] = False
        return results

    def batch_check_end(self, typos: list[str]) -> dict[str, bool]:
        """Batch check if typos appear as suffixes of any word.

        Args:
            typos: List of typo strings to check

        Returns:
            Dict mapping typo -> True if it appears as a suffix (excluding exact matches)
        """
        results: dict[str, bool] = {}
        for typo in typos:
            if typo in self.suffix_index:
                matching_words = self.suffix_index[typo]
                # Exclude exact match
                results[typo] = any(word != typo for word in matching_words)
            else:
                results[typo] = False
        return results

    def batch_check_substring(self, typos: list[str], jobs: int = 1) -> dict[str, bool]:
        """Batch check if typos are substrings of any word.

        Args:
            typos: List of typo strings to check
            jobs: Number of parallel jobs (1 = sequential)

        Returns:
            Dict mapping typo -> True if it is a substring (excluding exact matches)
        """
        results: dict[str, bool] = {}
        # Pre-filter typos that are definitely in substring_set (fast path)
        for typo in typos:
            if typo in self.substring_set:
                results[typo] = True

        # For typos not in substring_set, check if they're substrings of any word
        remaining_typos = [typo for typo in typos if typo not in results]

        if not remaining_typos:
            return results

        # Fallback: check against word_set (O(M) per typo)
        # Only needed for typos not in substring_set
        if jobs > 1 and len(remaining_typos) > 100:
            results.update(self._batch_check_substring_parallel(remaining_typos, jobs))
        else:
            results.update(self._batch_check_substring_sequential(remaining_typos))

        return results

    def _batch_check_substring_sequential(self, typos: list[str]) -> dict[str, bool]:
        """Sequential fallback check for substrings.

        Args:
            typos: List of typo strings to check

        Returns:
            Dict mapping typo -> True if it is a substring
        """
        results: dict[str, bool] = {}
        word_set = self.word_set
        for typo in typos:
            results[typo] = any(typo in word and typo != word for word in word_set)
        return results

    def _batch_check_substring_parallel(self, typos: list[str], jobs: int) -> dict[str, bool]:
        """Parallel fallback check for substrings.

        Args:
            typos: List of typo strings to check
            jobs: Number of parallel jobs

        Returns:
            Dict mapping typo -> True if it is a substring
        """
        word_list = list(self.word_set)

        with Pool(processes=jobs) as pool:
            results_list = pool.starmap(
                _check_typo_substring_worker, [(typo, word_list) for typo in typos]
            )

        return dict(results_list)
