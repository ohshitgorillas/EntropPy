"""Exclusion pattern matching."""

from .config import Correction


class ExclusionMatcher:
    """Handle exclusion patterns with wildcards."""

    def __init__(self, exclusion_set: set[str]):
        self.exact = set()
        self.wildcards = []

        for exclusion in exclusion_set:
            if "*" in exclusion:
                self.wildcards.append(exclusion)
            else:
                self.exact.add(exclusion)

    def should_exclude(self, correction: Correction) -> bool:
        """Check if correction should be excluded."""
        typo, word, _ = correction

        if typo in self.exact:
            return True

        for pattern in self.wildcards:
            if self._matches_wildcard(typo, pattern):
                return True

        return False

    def _matches_wildcard(self, typo: str, pattern: str) -> bool:
        """Check if typo matches wildcard pattern."""
        if pattern.startswith("*") and pattern.endswith("*"):
            return pattern[1:-1] in typo
        elif pattern.startswith("*"):
            return typo.endswith(pattern[1:])
        elif pattern.endswith("*"):
            return typo.startswith(pattern[:-1])
        return typo == pattern
