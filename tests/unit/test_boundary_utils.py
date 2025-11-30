"""Unit tests for boundary utilities behavior.

Tests verify boundary selection and override logic. Each test has a single assertion
and focuses on behavior.
"""

from unittest.mock import patch

from entroppy.core import BoundaryType
from entroppy.resolution.boundary_utils import (
    _should_skip_short_typo,
    apply_user_word_boundary_override,
    choose_strictest_boundary,
)


class TestChooseStrictestBoundary:
    """Test choose_strictest_boundary behavior."""

    def test_returns_both_when_both_present(self) -> None:
        """When BOTH is in boundaries list, returns BOTH."""
        boundaries = [BoundaryType.BOTH, BoundaryType.LEFT, BoundaryType.RIGHT]
        result = choose_strictest_boundary(boundaries)
        assert result == BoundaryType.BOTH

    def test_returns_both_when_left_and_right_present(self) -> None:
        """When LEFT and RIGHT are both present, returns BOTH."""
        boundaries = [BoundaryType.LEFT, BoundaryType.RIGHT]
        result = choose_strictest_boundary(boundaries)
        assert result == BoundaryType.BOTH

    def test_returns_left_when_only_left_present(self) -> None:
        """When only LEFT is present, returns LEFT."""
        boundaries = [BoundaryType.LEFT]
        result = choose_strictest_boundary(boundaries)
        assert result == BoundaryType.LEFT

    def test_returns_right_when_only_right_present(self) -> None:
        """When only RIGHT is present, returns RIGHT."""
        boundaries = [BoundaryType.RIGHT]
        result = choose_strictest_boundary(boundaries)
        assert result == BoundaryType.RIGHT

    def test_returns_none_when_only_none_present(self) -> None:
        """When only NONE is present, returns NONE."""
        boundaries = [BoundaryType.NONE]
        result = choose_strictest_boundary(boundaries)
        assert result == BoundaryType.NONE

    def test_returns_none_when_empty_list(self) -> None:
        """When boundaries list is empty, returns NONE."""
        boundaries: list[BoundaryType] = []
        result = choose_strictest_boundary(boundaries)
        assert result == BoundaryType.NONE

    def test_returns_left_when_left_and_none_present(self) -> None:
        """When LEFT and NONE are present, returns LEFT (stricter)."""
        boundaries = [BoundaryType.LEFT, BoundaryType.NONE]
        result = choose_strictest_boundary(boundaries)
        assert result == BoundaryType.LEFT

    def test_returns_right_when_right_and_none_present(self) -> None:
        """When RIGHT and NONE are present, returns RIGHT (stricter)."""
        boundaries = [BoundaryType.RIGHT, BoundaryType.NONE]
        result = choose_strictest_boundary(boundaries)
        assert result == BoundaryType.RIGHT


class TestApplyUserWordBoundaryOverride:
    """Test apply_user_word_boundary_override behavior."""

    def test_forces_both_for_two_letter_user_word(self) -> None:
        """When word is 2-letter user word, forces BOTH boundary."""
        word = "it"
        boundary = BoundaryType.LEFT
        user_words = {"it", "is", "at"}
        debug_words: set[str] = set()
        debug_typo_matcher = None
        typo = "ti"

        with patch("entroppy.resolution.boundary_utils.log_if_debug_correction"):
            result = apply_user_word_boundary_override(
                word, boundary, user_words, debug_words, debug_typo_matcher, typo
            )

        assert result == BoundaryType.BOTH

    def test_preserves_boundary_for_non_user_word(self) -> None:
        """When word is not in user words, preserves original boundary."""
        word = "test"
        boundary = BoundaryType.LEFT
        user_words = {"it", "is", "at"}
        debug_words: set[str] = set()
        debug_typo_matcher = None
        typo = "tset"

        result = apply_user_word_boundary_override(
            word, boundary, user_words, debug_words, debug_typo_matcher, typo
        )

        assert result == BoundaryType.LEFT

    def test_preserves_boundary_for_longer_user_word(self) -> None:
        """When user word is longer than 2 letters, preserves original boundary."""
        word = "test"
        boundary = BoundaryType.RIGHT
        user_words = {"test", "example"}
        debug_words: set[str] = set()
        debug_typo_matcher = None
        typo = "tset"

        result = apply_user_word_boundary_override(
            word, boundary, user_words, debug_words, debug_typo_matcher, typo
        )

        assert result == BoundaryType.RIGHT

    def test_forces_both_for_two_letter_user_word_regardless_of_original(self) -> None:
        """When word is 2-letter user word, forces BOTH even if original was NONE."""
        word = "at"
        boundary = BoundaryType.NONE
        user_words = {"at", "it", "is"}
        debug_words: set[str] = set()
        debug_typo_matcher = None
        typo = "ta"

        with patch("entroppy.resolution.boundary_utils.log_if_debug_correction"):
            result = apply_user_word_boundary_override(
                word, boundary, user_words, debug_words, debug_typo_matcher, typo
            )

        assert result == BoundaryType.BOTH

    def test_preserves_both_boundary_for_two_letter_user_word(self) -> None:
        """When word is 2-letter user word with BOTH boundary, preserves BOTH."""
        word = "it"
        boundary = BoundaryType.BOTH
        user_words = {"it", "is", "at"}
        debug_words: set[str] = set()
        debug_typo_matcher = None
        typo = "ti"

        with patch("entroppy.resolution.boundary_utils.log_if_debug_correction"):
            result = apply_user_word_boundary_override(
                word, boundary, user_words, debug_words, debug_typo_matcher, typo
            )

        assert result == BoundaryType.BOTH


class TestShouldSkipShortTypo:
    """Test _should_skip_short_typo behavior."""

    def test_skips_typo_when_shorter_than_min_and_word_longer_than_min_word(self) -> None:
        """When typo is shorter than min_typo_length and word
        is longer than min_word_length, returns True."""
        typo = "ab"
        word = "test"
        min_typo_length = 3
        min_word_length = 3

        result = _should_skip_short_typo(typo, word, min_typo_length, min_word_length)

        assert result is True

    def test_does_not_skip_typo_when_typo_meets_min_length(self) -> None:
        """When typo meets min_typo_length, returns False."""
        typo = "abc"
        word = "test"
        min_typo_length = 3
        min_word_length = 3

        result = _should_skip_short_typo(typo, word, min_typo_length, min_word_length)

        assert result is False

    def test_does_not_skip_typo_when_word_too_short(self) -> None:
        """When word is not longer than min_word_length, returns False."""
        typo = "ab"
        word = "ab"
        min_typo_length = 3
        min_word_length = 3

        result = _should_skip_short_typo(typo, word, min_typo_length, min_word_length)

        assert result is False

    def test_does_not_skip_typo_when_both_conditions_not_met(self) -> None:
        """When typo is short but word is also short, returns False."""
        typo = "a"
        word = "ab"
        min_typo_length = 2
        min_word_length = 3

        result = _should_skip_short_typo(typo, word, min_typo_length, min_word_length)

        assert result is False

    def test_skips_typo_when_exactly_at_thresholds(self) -> None:
        """When typo is exactly one less than min_typo_length
        and word is longer than min_word_length, returns True."""
        typo = "ab"
        word = "tests"
        min_typo_length = 3
        min_word_length = 4

        result = _should_skip_short_typo(typo, word, min_typo_length, min_word_length)

        assert result is True

    def test_does_not_skip_when_typo_exactly_at_min_length(self) -> None:
        """When typo length equals min_typo_length, returns False."""
        typo = "abc"
        word = "test"
        min_typo_length = 3
        min_word_length = 3

        result = _should_skip_short_typo(typo, word, min_typo_length, min_word_length)

        assert result is False

    def test_does_not_skip_when_word_exactly_at_min_length(self) -> None:
        """When word length equals min_word_length, returns False."""
        typo = "ab"
        word = "abc"
        min_typo_length = 3
        min_word_length = 3

        result = _should_skip_short_typo(typo, word, min_typo_length, min_word_length)

        assert result is False
