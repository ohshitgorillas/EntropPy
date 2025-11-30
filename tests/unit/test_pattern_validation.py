"""Unit tests for pattern validation behavior.

Tests verify pattern validation logic that ensures patterns produce correct results
and don't conflict with validation words or source words. Each test has a single
assertion and focuses on behavior.
"""

from entroppy.core.boundaries import BoundaryType
from entroppy.core.pattern_validation import (
    _validate_pattern_result,
    _would_corrupt_source_word,
    check_pattern_conflicts,
    validate_pattern_for_all_occurrences,
)
from entroppy.platforms.base import MatchDirection


class TestValidatePatternResult:
    """Test pattern result validation behavior."""

    def test_validates_rtl_prefix_pattern_correctly(self) -> None:
        """When RTL prefix pattern matches correctly, returns True with expected result."""
        is_valid, _ = _validate_pattern_result(
            "teh", "the", "tehword", "theword", MatchDirection.RIGHT_TO_LEFT
        )
        assert is_valid is True

    def test_computes_correct_result_for_rtl_prefix_pattern(self) -> None:
        """When RTL prefix pattern is applied, computes correct expected result."""
        _, expected_result = _validate_pattern_result(
            "teh", "the", "tehword", "theword", MatchDirection.RIGHT_TO_LEFT
        )
        assert expected_result == "theword"

    def test_validates_ltr_suffix_pattern_correctly(self) -> None:
        """When LTR suffix pattern matches correctly, returns True."""
        is_valid, _ = _validate_pattern_result(
            "eh", "he", "wordeh", "wordhe", MatchDirection.LEFT_TO_RIGHT
        )
        assert is_valid is True

    def test_computes_correct_result_for_ltr_suffix_pattern(self) -> None:
        """When LTR suffix pattern is applied, computes correct expected result."""
        _, expected_result = _validate_pattern_result(
            "eh", "he", "wordeh", "wordhe", MatchDirection.LEFT_TO_RIGHT
        )
        assert expected_result == "wordhe"

    def test_rejects_rtl_pattern_when_result_does_not_match(self) -> None:
        """When RTL prefix pattern produces wrong result, returns False."""
        is_valid, _ = _validate_pattern_result(
            "teh", "the", "tehword", "thewrd", MatchDirection.RIGHT_TO_LEFT
        )
        assert is_valid is False

    def test_rejects_ltr_pattern_when_result_does_not_match(self) -> None:
        """When LTR suffix pattern produces wrong result, returns False."""
        is_valid, _ = _validate_pattern_result(
            "eh", "he", "wordeh", "wordhr", MatchDirection.LEFT_TO_RIGHT
        )
        assert is_valid is False

    def test_handles_rtl_pattern_with_no_remaining_suffix(self) -> None:
        """When RTL pattern is the entire typo, handles correctly."""
        is_valid, _ = _validate_pattern_result(
            "teh", "the", "teh", "the", MatchDirection.RIGHT_TO_LEFT
        )
        assert is_valid is True

    def test_handles_ltr_pattern_with_no_remaining_prefix(self) -> None:
        """When LTR pattern is the entire typo, handles correctly."""
        is_valid, _ = _validate_pattern_result(
            "eh", "he", "eh", "he", MatchDirection.LEFT_TO_RIGHT
        )
        assert is_valid is True


class TestWouldCorruptSourceWord:
    """Test source word corruption detection behavior."""

    def test_detects_rtl_pattern_at_word_start(self) -> None:
        """When RTL pattern appears at word start, detects corruption."""
        result = _would_corrupt_source_word("teh", "tehword", MatchDirection.RIGHT_TO_LEFT)
        assert result is True

    def test_detects_rtl_pattern_after_non_alpha_character(self) -> None:
        """When RTL pattern appears after non-alpha character, detects corruption."""
        result = _would_corrupt_source_word("teh", "word teh", MatchDirection.RIGHT_TO_LEFT)
        assert result is True

    def test_ignores_rtl_pattern_in_middle_of_word(self) -> None:
        """When RTL pattern appears in middle of word, does not detect corruption."""
        result = _would_corrupt_source_word("teh", "wordtehword", MatchDirection.RIGHT_TO_LEFT)
        assert result is False

    def test_detects_ltr_pattern_at_word_end(self) -> None:
        """When LTR pattern appears at word end, detects corruption."""
        result = _would_corrupt_source_word("eh", "wordeh", MatchDirection.LEFT_TO_RIGHT)
        assert result is True

    def test_detects_ltr_pattern_before_non_alpha_character(self) -> None:
        """When LTR pattern appears before non-alpha character, detects corruption."""
        result = _would_corrupt_source_word("eh", "wordeh.", MatchDirection.LEFT_TO_RIGHT)
        assert result is True

    def test_ignores_ltr_pattern_in_middle_of_word(self) -> None:
        """When LTR pattern appears in middle of word, does not detect corruption."""
        result = _would_corrupt_source_word("eh", "wordehword", MatchDirection.LEFT_TO_RIGHT)
        assert result is False

    def test_handles_multiple_occurrences_of_rtl_pattern(self) -> None:
        """When RTL pattern appears multiple times, checks all occurrences."""
        result = _would_corrupt_source_word("teh", "teh word teh", MatchDirection.RIGHT_TO_LEFT)
        assert result is True

    def test_handles_multiple_occurrences_of_ltr_pattern(self) -> None:
        """When LTR pattern appears multiple times, checks all occurrences."""
        result = _would_corrupt_source_word("eh", "wordeh. wordeh", MatchDirection.LEFT_TO_RIGHT)
        assert result is True

    def test_returns_false_when_pattern_not_found(self) -> None:
        """When pattern is not in source word, returns False."""
        result = _would_corrupt_source_word("xyz", "word", MatchDirection.RIGHT_TO_LEFT)
        assert result is False


class TestValidatePatternForAllOccurrences:
    """Test pattern validation for all occurrences behavior."""

    def test_validates_pattern_when_all_occurrences_work(self) -> None:
        """When all occurrences produce correct results, returns True."""
        occurrences = [
            ("tehword", "theword", BoundaryType.LEFT),
            ("tehbook", "thebook", BoundaryType.LEFT),
        ]
        is_valid, _ = validate_pattern_for_all_occurrences(
            "teh", "the", occurrences, MatchDirection.RIGHT_TO_LEFT
        )
        assert is_valid is True

    def test_returns_none_error_when_all_occurrences_valid(self) -> None:
        """When all occurrences are valid, error message is None."""
        occurrences = [
            ("tehword", "theword", BoundaryType.LEFT),
            ("tehbook", "thebook", BoundaryType.LEFT),
        ]
        _, error_msg = validate_pattern_for_all_occurrences(
            "teh", "the", occurrences, MatchDirection.RIGHT_TO_LEFT
        )
        assert error_msg is None

    def test_rejects_pattern_when_any_occurrence_fails(self) -> None:
        """When any occurrence produces wrong result, returns False."""
        occurrences = [
            ("tehword", "theword", BoundaryType.LEFT),
            ("tehbook", "thewrong", BoundaryType.LEFT),
        ]
        is_valid, _ = validate_pattern_for_all_occurrences(
            "teh", "the", occurrences, MatchDirection.RIGHT_TO_LEFT
        )
        assert is_valid is False

    def test_provides_error_message_when_validation_fails(self) -> None:
        """When validation fails, provides non-None error message."""
        occurrences = [
            ("tehword", "theword", BoundaryType.LEFT),
            ("tehbook", "thewrong", BoundaryType.LEFT),
        ]
        _, error_msg = validate_pattern_for_all_occurrences(
            "teh", "the", occurrences, MatchDirection.RIGHT_TO_LEFT
        )
        assert error_msg is not None

    def test_error_message_includes_failed_typo(self) -> None:
        """When validation fails, error message includes the failed typo."""
        occurrences = [
            ("tehword", "theword", BoundaryType.LEFT),
            ("tehbook", "thewrong", BoundaryType.LEFT),
        ]
        _, error_msg = validate_pattern_for_all_occurrences(
            "teh", "the", occurrences, MatchDirection.RIGHT_TO_LEFT
        )
        assert "tehbook" in error_msg

    def test_error_message_includes_expected_word(self) -> None:
        """When validation fails, error message includes the expected word."""
        occurrences = [
            ("tehword", "theword", BoundaryType.LEFT),
            ("tehbook", "thewrong", BoundaryType.LEFT),
        ]
        _, error_msg = validate_pattern_for_all_occurrences(
            "teh", "the", occurrences, MatchDirection.RIGHT_TO_LEFT
        )
        assert "thewrong" in error_msg

    def test_validates_ltr_suffix_patterns_correctly(self) -> None:
        """When LTR suffix pattern works for all occurrences, returns True."""
        occurrences = [
            ("wordeh", "wordhe", BoundaryType.RIGHT),
            ("bookeh", "bookhe", BoundaryType.RIGHT),
        ]
        is_valid, _ = validate_pattern_for_all_occurrences(
            "eh", "he", occurrences, MatchDirection.LEFT_TO_RIGHT
        )
        assert is_valid is True

    def test_rejects_ltr_pattern_when_occurrence_fails(self) -> None:
        """When LTR suffix pattern fails for any occurrence, returns False."""
        occurrences = [
            ("wordeh", "wordhe", BoundaryType.RIGHT),
            ("bookeh", "bookhr", BoundaryType.RIGHT),
        ]
        is_valid, _ = validate_pattern_for_all_occurrences(
            "eh", "he", occurrences, MatchDirection.LEFT_TO_RIGHT
        )
        assert is_valid is False

    def test_handles_single_occurrence(self) -> None:
        """When pattern has single occurrence, validates correctly."""
        occurrences = [("tehword", "theword", BoundaryType.LEFT)]
        is_valid, _ = validate_pattern_for_all_occurrences(
            "teh", "the", occurrences, MatchDirection.RIGHT_TO_LEFT
        )
        assert is_valid is True

    def test_handles_empty_occurrences_list(self) -> None:
        """When occurrences list is empty, returns True."""
        occurrences: list[tuple[str, str, BoundaryType]] = []
        is_valid, _ = validate_pattern_for_all_occurrences(
            "teh", "the", occurrences, MatchDirection.RIGHT_TO_LEFT
        )
        assert is_valid is True


class TestCheckPatternConflicts:
    """Test pattern conflict detection behavior."""

    def test_accepts_pattern_not_in_validation_set(self) -> None:
        """When pattern is not in validation set, returns True."""
        is_safe, _ = check_pattern_conflicts(
            "teh", {"the", "word"}, set(), MatchDirection.RIGHT_TO_LEFT
        )
        assert is_safe is True

    def test_rejects_pattern_that_is_validation_word(self) -> None:
        """When pattern is a validation word, returns False."""
        is_safe, _ = check_pattern_conflicts(
            "the", {"the", "word"}, set(), MatchDirection.RIGHT_TO_LEFT
        )
        assert is_safe is False

    def test_provides_error_message_for_validation_word_conflict(self) -> None:
        """When pattern conflicts with validation word, provides non-None error message."""
        _, error_msg = check_pattern_conflicts(
            "the", {"the", "word"}, set(), MatchDirection.RIGHT_TO_LEFT
        )
        assert error_msg is not None

    def test_error_message_includes_validation_word(self) -> None:
        """When pattern conflicts with validation word, error message includes the word."""
        _, error_msg = check_pattern_conflicts(
            "the", {"the", "word"}, set(), MatchDirection.RIGHT_TO_LEFT
        )
        assert "the" in error_msg

    def test_rejects_pattern_that_triggers_at_end_of_validation_word(self) -> None:
        """When pattern triggers at end of validation word, returns False."""
        is_safe, _ = check_pattern_conflicts(
            "eh", {"wordeh", "other"}, set(), MatchDirection.LEFT_TO_RIGHT
        )
        assert is_safe is False

    def test_provides_error_message_for_end_trigger_conflict(self) -> None:
        """When pattern triggers at end, provides non-None error message."""
        _, error_msg = check_pattern_conflicts(
            "eh", {"wordeh", "other"}, set(), MatchDirection.LEFT_TO_RIGHT
        )
        assert error_msg is not None

    def test_error_message_mentions_end_trigger(self) -> None:
        """When pattern triggers at end, error message mentions end."""
        _, error_msg = check_pattern_conflicts(
            "eh", {"wordeh", "other"}, set(), MatchDirection.LEFT_TO_RIGHT
        )
        assert "end" in error_msg.lower()

    def test_rejects_pattern_that_corrupts_source_word_rtl(self) -> None:
        """When RTL pattern corrupts source word, returns False."""
        is_safe, _ = check_pattern_conflicts(
            "teh", set(), {"tehword"}, MatchDirection.RIGHT_TO_LEFT
        )
        assert is_safe is False

    def test_rejects_pattern_that_corrupts_source_word_ltr(self) -> None:
        """When LTR pattern corrupts source word, returns False."""
        is_safe, _ = check_pattern_conflicts(
            "eh", set(), {"wordeh"}, MatchDirection.LEFT_TO_RIGHT
        )
        assert is_safe is False

    def test_provides_error_message_for_source_word_corruption(self) -> None:
        """When pattern corrupts source word, provides non-None error message."""
        _, error_msg = check_pattern_conflicts(
            "teh", set(), {"tehword"}, MatchDirection.RIGHT_TO_LEFT
        )
        assert error_msg is not None

    def test_error_message_mentions_corruption(self) -> None:
        """When pattern corrupts source word, error message mentions corruption."""
        _, error_msg = check_pattern_conflicts(
            "teh", set(), {"tehword"}, MatchDirection.RIGHT_TO_LEFT
        )
        assert "corrupt" in error_msg.lower()

    def test_accepts_pattern_when_source_word_has_pattern_in_middle(self) -> None:
        """When pattern appears in middle of source word, does not corrupt."""
        is_safe, _ = check_pattern_conflicts(
            "teh", set(), {"wordtehword"}, MatchDirection.RIGHT_TO_LEFT
        )
        assert is_safe is True

    def test_checks_all_source_words_for_corruption(self) -> None:
        """When checking multiple source words, detects corruption in any."""
        is_safe, _ = check_pattern_conflicts(
            "teh", set(), {"word", "tehbook", "other"}, MatchDirection.RIGHT_TO_LEFT
        )
        assert is_safe is False

    def test_returns_none_error_when_no_conflicts(self) -> None:
        """When pattern has no conflicts, error message is None."""
        _, error_msg = check_pattern_conflicts(
            "teh", {"the"}, {"word"}, MatchDirection.RIGHT_TO_LEFT
        )
        assert error_msg is None

    def test_handles_empty_validation_set(self) -> None:
        """When validation set is empty, checks only source words."""
        is_safe, _ = check_pattern_conflicts(
            "teh", set(), {"word"}, MatchDirection.RIGHT_TO_LEFT
        )
        assert is_safe is True

    def test_handles_empty_source_words_set(self) -> None:
        """When source words set is empty, checks only validation set."""
        is_safe, _ = check_pattern_conflicts(
            "teh", {"the"}, set(), MatchDirection.RIGHT_TO_LEFT
        )
        assert is_safe is True

    def test_prioritizes_validation_word_conflict_over_other_checks(self) -> None:
        """When pattern is validation word, returns False immediately."""
        is_safe, _ = check_pattern_conflicts(
            "the", {"the"}, {"theword"}, MatchDirection.RIGHT_TO_LEFT
        )
        assert is_safe is False

    def test_validation_word_conflict_error_message_mentions_validation(self) -> None:
        """When pattern is validation word, error message mentions validation word."""
        _, error_msg = check_pattern_conflicts(
            "the", {"the"}, {"theword"}, MatchDirection.RIGHT_TO_LEFT
        )
        assert "validation word" in error_msg.lower()
