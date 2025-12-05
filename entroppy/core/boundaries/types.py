"""Boundary types and index classes."""

from enum import Enum


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

    def __init__(self, word_set: set[str] | frozenset[str]) -> None:
        """Build indexes from a word set.

        Args:
            word_set: Set of words to build indexes from
        """
        self.word_set = word_set
        self.prefix_index: dict[str, set[str]] = {}
        self.suffix_index: dict[str, set[str]] = {}
        self.substring_set: set[str] = set()

        # Build prefix index: for each word, add all prefixes to index
        for word in word_set:
            for i in range(1, len(word) + 1):
                prefix = word[:i]
                if prefix not in self.prefix_index:
                    self.prefix_index[prefix] = set()
                self.prefix_index[prefix].add(word)

        # Build suffix index: for each word, add all suffixes to index
        for word in word_set:
            for i in range(len(word)):
                suffix = word[i:]
                if suffix not in self.suffix_index:
                    self.suffix_index[suffix] = set()
                self.suffix_index[suffix].add(word)

        # Build substring set: for each word, add all substrings (excluding exact match)
        for word in word_set:
            for i in range(len(word)):
                for j in range(i + 1, len(word) + 1):
                    substring = word[i:j]
                    if substring != word:  # Exclude exact matches
                        self.substring_set.add(substring)
