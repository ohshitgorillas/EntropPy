"""Regression tests to expose bugs.

Each test has ONE ASSERT to follow the one-assertion-per-test rule.
These tests verify that previously fixed bugs do not regress.
"""

from entroppy.core import BoundaryType
from entroppy.core.patterns.extraction.finder import find_prefix_patterns, find_suffix_patterns


class TestPatternBoundaryAssignment:
    """Regression: Patterns should not be assigned BOTH boundary type."""

    def test_suffix_pattern_not_assigned_both_boundary(self) -> None:
        """Suffix patterns extracted from BOTH boundary corrections
        are not assigned BOTH boundary."""
        corrections = [
            ("testeh", "testhe", BoundaryType.BOTH),
            ("wordteh", "wordthe", BoundaryType.BOTH),
        ]
        result = find_suffix_patterns(corrections)
        both_boundary_patterns = [p for p in result.keys() if p[2] == BoundaryType.BOTH]
        assert len(both_boundary_patterns) == 0

    def test_prefix_pattern_not_assigned_both_boundary(self) -> None:
        """Prefix patterns extracted from BOTH boundary corrections
        are not assigned BOTH boundary."""
        corrections = [
            ("htest", "thest", BoundaryType.BOTH),
            ("hteword", "theword", BoundaryType.BOTH),
        ]
        result = find_prefix_patterns(corrections)
        both_boundary_patterns = [p for p in result.keys() if p[2] == BoundaryType.BOTH]
        assert len(both_boundary_patterns) == 0


class TestNoneBoundaryPatternExtraction:
    """Regression: Patterns are extracted with NONE boundary, not inheriting from corrections."""

    def test_patterns_exist_when_extracted(self) -> None:
        """Patterns are extracted from corrections."""
        corrections = [
            ("testeh", "testhe", BoundaryType.BOTH),
            ("wordteh", "wordthe", BoundaryType.BOTH),
        ]
        result = find_suffix_patterns(corrections)
        assert len(result) > 0

    def test_patterns_have_none_boundary(self) -> None:
        """All extracted patterns have NONE boundary."""
        corrections = [
            ("testeh", "testhe", BoundaryType.BOTH),
            ("wordteh", "wordthe", BoundaryType.BOTH),
        ]
        result = find_suffix_patterns(corrections)
        none_boundary_patterns = [p for p in result.keys() if p[2] == BoundaryType.NONE]
        assert len(none_boundary_patterns) == len(result)

    def test_patterns_do_not_have_both_boundary(self) -> None:
        """No extracted patterns have BOTH boundary."""
        corrections = [
            ("testeh", "testhe", BoundaryType.BOTH),
            ("wordteh", "wordthe", BoundaryType.BOTH),
        ]
        result = find_suffix_patterns(corrections)
        both_boundary_patterns = [p for p in result.keys() if p[2] == BoundaryType.BOTH]
        assert len(both_boundary_patterns) == 0
