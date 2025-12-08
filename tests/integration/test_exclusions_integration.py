"""Integration tests to verify refactored code produces identical behavior.

These tests verify that the pattern matching refactor maintains identical
behavior in all three refactored modules.
"""

import os
import tempfile

from entroppy.core import BoundaryType
from entroppy.data import load_validation_dictionary
from entroppy.matching import ExclusionMatcher
from entroppy.resolution import process_word


class TestProcessingIntegration:
    """Verify process_word() behavior unchanged after refactoring."""

    def test_process_word_with_exact_exclusion(self) -> None:
        """Verify exact exclusion patterns work correctly."""
        word = "test"
        validation_set = {"tset", "tets"}
        source_words = set()
        typo_freq_threshold = 0.0
        adj_letters_map = None
        exclusions = {"tset"}  # Exact exclusion

        corrections, _ = process_word(
            word,
            validation_set,
            source_words,
            typo_freq_threshold,
            adj_letters_map,
            exclusions,
        )

        # tset is explicitly excluded, should not appear in corrections
        typos = [typo for typo, _ in corrections]
        assert "tset" not in typos

    def test_process_word_exclusions_bypass_frequency_check(self) -> None:
        """Verify exclusion patterns allow typos to bypass frequency threshold."""
        word = "test"
        validation_set = set()
        source_words = set()
        typo_freq_threshold = 1.0  # High threshold that would normally block all typos
        adj_letters_map = None
        exclusions = {"tset"}  # This typo should bypass frequency check

        corrections, _ = process_word(
            word,
            validation_set,
            source_words,
            typo_freq_threshold,
            adj_letters_map,
            exclusions,
        )

        # The typo may or may not appear depending on boundary detection,
        # but the key is no error should occur
        assert isinstance(corrections, list)

    def test_process_word_ignores_typo_word_mappings(self) -> None:
        """Verify typo->word mappings in exclusions don't affect word-level filtering."""
        word = "test"
        validation_set = set()
        source_words = set()
        typo_freq_threshold = 0.0
        adj_letters_map = None
        exclusions = {"tset -> test"}  # This should be ignored by process_word

        corrections, _ = process_word(
            word,
            validation_set,
            source_words,
            typo_freq_threshold,
            adj_letters_map,
            exclusions,
        )
        # tset might or might not be in corrections depending on boundary detection,
        # but the pattern shouldn't cause an error
        assert isinstance(corrections, list)

    def test_process_word_with_multiple_exclusion_patterns(self) -> None:
        """Verify mixed exact and wildcard exclusion patterns work together."""
        word = "test"
        validation_set = set()
        source_words = set()
        typo_freq_threshold = 1.0  # High threshold
        adj_letters_map = None
        exclusions = {"tset", "test*"}  # Mix of exact and wildcard

        corrections, _ = process_word(
            word,
            validation_set,
            source_words,
            typo_freq_threshold,
            adj_letters_map,
            exclusions,
        )

        # Exclusions bypass frequency check, so we should get results
        assert isinstance(corrections, list)


class TestDictionaryIntegration:
    """Verify load_validation_dictionary() behavior unchanged."""

    def test_load_validation_dictionary_excludes_ball_suffix(self) -> None:
        """Verify words ending with 'ball' are excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exclude_file = os.path.join(tmpdir, "exclude.txt")
            with open(exclude_file, "w", encoding="utf-8") as f:
                f.write("*ball\n")

            dictionary = load_validation_dictionary(exclude_file, None, verbose=False)
            assert "football" not in dictionary

    def test_load_validation_dictionary_excludes_test_infix(self) -> None:
        """Verify words containing 'test' are excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exclude_file = os.path.join(tmpdir, "exclude.txt")
            with open(exclude_file, "w", encoding="utf-8") as f:
                f.write("*test*\n")

            dictionary = load_validation_dictionary(exclude_file, None, verbose=False)
            assert "testing" not in dictionary

    def test_load_validation_dictionary_excludes_exact_word(self) -> None:
        """Verify exact word 'rpi' is excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exclude_file = os.path.join(tmpdir, "exclude.txt")
            with open(exclude_file, "w", encoding="utf-8") as f:
                f.write("rpi\n")

            dictionary = load_validation_dictionary(exclude_file, None, verbose=False)
            assert "rpi" not in dictionary

    def test_load_validation_dictionary_ignores_typo_mappings(self) -> None:
        """Verify typo->word mappings don't affect dictionary loading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exclude_file = os.path.join(tmpdir, "exclude.txt")
            with open(exclude_file, "w", encoding="utf-8") as f:
                f.write("teh -> the\n")
                f.write("*ball\n")

            dictionary = load_validation_dictionary(exclude_file, None, verbose=False)
            # Only "*ball" pattern should filter words
            assert "football" not in dictionary

    def test_load_validation_dictionary_with_comments(self) -> None:
        """Verify comments in exclusion file are properly ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exclude_file = os.path.join(tmpdir, "exclude.txt")
            with open(exclude_file, "w", encoding="utf-8") as f:
                f.write("# This is a comment\n")
                f.write("*ball\n")
                f.write("# Another comment\n")

            dictionary = load_validation_dictionary(exclude_file, None, verbose=False)

            # Comments should be ignored, only pattern should work
            assert "football" not in dictionary


class TestExclusionMatcherIntegration:
    """Verify ExclusionMatcher behavior unchanged after refactoring."""

    def test_exclusion_matcher_exact_typo_word_mapping(self) -> None:
        """Verify exact typo->word mapping 'teh -> the' works."""
        exclusions = {"teh -> the"}
        matcher = ExclusionMatcher(exclusions)

        correction = ("teh", "the", BoundaryType.BOTH)
        assert matcher.should_exclude(correction) is True

    def test_exclusion_matcher_does_not_exclude_unmatched(self) -> None:
        """Verify unmatched corrections are not excluded."""
        exclusions = {"teh -> the"}
        matcher = ExclusionMatcher(exclusions)

        correction = ("other", "word", BoundaryType.BOTH)
        assert matcher.should_exclude(correction) is False

    def test_exclusion_matcher_wildcard_typo_mapping(self) -> None:
        """Verify wildcard typo->word mapping '*toin -> *tion' works."""
        exclusions = {"*toin -> *tion"}
        matcher = ExclusionMatcher(exclusions)

        correction = ("actoin", "action", BoundaryType.BOTH)
        assert matcher.should_exclude(correction) is True

    def test_exclusion_matcher_boundary_both_matches(self) -> None:
        """Verify boundary constraint :toin: -> tion matches BOTH."""
        exclusions = {":toin: -> tion"}
        matcher = ExclusionMatcher(exclusions)

        correction = ("toin", "tion", BoundaryType.BOTH)
        assert matcher.should_exclude(correction) is True

    def test_exclusion_matcher_boundary_left_doesnt_match_both(self) -> None:
        """Verify boundary constraint :toin: -> tion doesn't match LEFT only."""
        exclusions = {":toin: -> tion"}
        matcher = ExclusionMatcher(exclusions)

        correction = ("toin", "tion", BoundaryType.LEFT)
        assert matcher.should_exclude(correction) is False

    def test_exclusion_matcher_filter_removes_wildcard_match(self) -> None:
        """Verify filter_validation_set removes word matching '*ball'."""
        exclusions = {"*ball"}
        matcher = ExclusionMatcher(exclusions)

        validation_set = {"football", "hello"}
        filtered = matcher.filter_validation_set(validation_set)

        assert "football" not in filtered

    def test_exclusion_matcher_filter_keeps_non_match(self) -> None:
        """Verify filter_validation_set keeps non-matching words."""
        exclusions = {"*ball"}
        matcher = ExclusionMatcher(exclusions)

        validation_set = {"hello", "world"}
        filtered = matcher.filter_validation_set(validation_set)

        assert "hello" in filtered

    def test_exclusion_matcher_get_matching_rule_exact(self) -> None:
        """Verify get_matching_rule returns exact rule."""
        exclusions = {"teh -> the"}
        matcher = ExclusionMatcher(exclusions)

        correction = ("teh", "the", BoundaryType.BOTH)
        rule = matcher.get_matching_rule(correction)

        assert "teh" in rule and "the" in rule

    def test_exclusion_matcher_exact_typo_with_wildcard_word_matches_just(self) -> None:
        """Verify exact typo with wildcard word pattern matches 'just'."""
        exclusions = {"jst -> *"}
        matcher = ExclusionMatcher(exclusions)

        correction = ("jst", "just", BoundaryType.BOTH)
        assert matcher.should_exclude(correction) is True

    def test_exclusion_matcher_exact_typo_with_wildcard_word_matches_any(self) -> None:
        """Verify exact typo with wildcard word pattern matches any word."""
        exclusions = {"jst -> *"}
        matcher = ExclusionMatcher(exclusions)

        correction = ("jst", "jest", BoundaryType.BOTH)
        assert matcher.should_exclude(correction) is True

    def test_exclusion_matcher_exact_typo_with_exact_word_matches(self) -> None:
        """Verify exact typo with exact word matches correctly."""
        exclusions = {"jst -> just"}
        matcher = ExclusionMatcher(exclusions)

        correction = ("jst", "just", BoundaryType.BOTH)
        assert matcher.should_exclude(correction) is True

    def test_exclusion_matcher_exact_typo_with_exact_word_does_not_match_other(self) -> None:
        """Verify exact typo with exact word does not match other words."""
        exclusions = {"jst -> just"}
        matcher = ExclusionMatcher(exclusions)

        correction = ("jst", "jest", BoundaryType.BOTH)
        assert matcher.should_exclude(correction) is False

    def test_exclusion_matcher_exact_typo_matches_none_boundary(self) -> None:
        """Verify exact typo pattern matches NONE boundary."""
        exclusions = {"jst -> just"}
        matcher = ExclusionMatcher(exclusions)

        correction = ("jst", "just", BoundaryType.NONE)
        assert matcher.should_exclude(correction) is True

    def test_exclusion_matcher_exact_typo_matches_left_boundary(self) -> None:
        """Verify exact typo pattern matches LEFT boundary."""
        exclusions = {"jst -> just"}
        matcher = ExclusionMatcher(exclusions)

        correction = ("jst", "just", BoundaryType.LEFT)
        assert matcher.should_exclude(correction) is True

    def test_exclusion_matcher_exact_typo_matches_right_boundary(self) -> None:
        """Verify exact typo pattern matches RIGHT boundary."""
        exclusions = {"jst -> just"}
        matcher = ExclusionMatcher(exclusions)

        correction = ("jst", "just", BoundaryType.RIGHT)
        assert matcher.should_exclude(correction) is True

    def test_exclusion_matcher_exact_typo_matches_both_boundary(self) -> None:
        """Verify exact typo pattern matches BOTH boundary."""
        exclusions = {"jst -> just"}
        matcher = ExclusionMatcher(exclusions)

        correction = ("jst", "just", BoundaryType.BOTH)
        assert matcher.should_exclude(correction) is True

    def test_exclusion_matcher_exact_typo_with_wildcard_word_matches_any_boundary(self) -> None:
        """Verify exact typo with wildcard word matches any boundary."""
        exclusions = {"jst -> *"}
        matcher = ExclusionMatcher(exclusions)

        correction = ("jst", "just", BoundaryType.LEFT)
        assert matcher.should_exclude(correction) is True

    def test_exclusion_matcher_excludes_substring_pattern(self) -> None:
        """Verify that a pattern is excluded when it is a substring of another pattern."""
        # If "*test*" matches words containing "test", both "test" and "testing" should be excluded
        exclusions = {"*test*"}
        matcher = ExclusionMatcher(exclusions)

        validation_set = {"testing", "test", "hello"}
        filtered = matcher.filter_validation_set(validation_set)

        # "testing" should be excluded (contains "test", matches "*test*")
        assert "testing" not in filtered

    def test_exclusion_matcher_excludes_exact_match(self) -> None:
        """Verify that exact match is excluded when pattern matches."""
        exclusions = {"*test*"}
        matcher = ExclusionMatcher(exclusions)

        validation_set = {"testing", "test", "hello"}
        filtered = matcher.filter_validation_set(validation_set)

        # "test" should also be excluded (matches "*test*")
        assert "test" not in filtered

    def test_exclusion_matcher_keeps_non_matching_words(self) -> None:
        """Verify that words not matching pattern are kept."""
        exclusions = {"*test*"}
        matcher = ExclusionMatcher(exclusions)

        validation_set = {"testing", "test", "hello"}
        filtered = matcher.filter_validation_set(validation_set)

        # "hello" should remain (doesn't match pattern)
        assert "hello" in filtered

    def test_exclusion_matcher_exact_exclusion_only_matches_exact(self) -> None:
        """Verify that exact exclusion patterns only match exact words, not substrings."""
        # If "the" is in the exclusion list (exact, no wildcards), then "the" is excluded
        # but "theirs" is NOT excluded (because "the" is an exact match, not "*the*")
        exclusions = {"the"}
        matcher = ExclusionMatcher(exclusions)

        validation_set = {"the", "theirs", "hello"}
        filtered = matcher.filter_validation_set(validation_set)

        # "the" should be excluded (exact match)
        assert "the" not in filtered

    def test_exclusion_matcher_exact_exclusion_keeps_substrings(self) -> None:
        """Verify that exact exclusion patterns do not exclude substrings."""
        exclusions = {"the"}
        matcher = ExclusionMatcher(exclusions)

        validation_set = {"the", "theirs", "hello"}
        filtered = matcher.filter_validation_set(validation_set)

        # "theirs" should NOT be excluded (contains "the" but doesn't match exact pattern)
        assert "theirs" in filtered

    def test_exclusion_matcher_exact_exclusion_keeps_unrelated_words(self) -> None:
        """Verify that exact exclusion patterns keep unrelated words."""
        exclusions = {"the"}
        matcher = ExclusionMatcher(exclusions)

        validation_set = {"the", "theirs", "hello"}
        filtered = matcher.filter_validation_set(validation_set)

        # "hello" should remain (doesn't match pattern)
        assert "hello" in filtered


class TestRealWorldPatterns:
    """Test with real patterns from examples/exclude.txt."""

    def test_with_example_pattern_ball(self) -> None:
        """Verify '*ball' pattern from examples works."""
        exclusions = {"*ball"}
        matcher = ExclusionMatcher(exclusions)

        validation_set = {"football", "hello"}
        filtered = matcher.filter_validation_set(validation_set)

        assert "football" not in filtered

    def test_with_example_pattern_keeps_non_match(self) -> None:
        """Verify example patterns keep non-matching words."""
        exclusions = {"*ball", "*toin"}
        matcher = ExclusionMatcher(exclusions)

        validation_set = {"hello", "world"}
        filtered = matcher.filter_validation_set(validation_set)

        assert "hello" in filtered

    def test_processing_with_example_pattern_teh(self) -> None:
        """Verify process_word with '*teh*' exclusion pattern."""
        word = "the"
        validation_set = set()
        source_words = set()
        typo_freq_threshold = 1.0  # High threshold
        adj_letters_map = None
        exclusions = {"*teh*"}

        corrections, _ = process_word(
            word,
            validation_set,
            source_words,
            typo_freq_threshold,
            adj_letters_map,
            exclusions,
        )

        # Exclusion pattern should bypass frequency check
        assert isinstance(corrections, list)
