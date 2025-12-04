"""Behavioral tests for false trigger prevention.

Tests verify that typos which appear as substrings in validation words
are not added with NONE boundary.
"""

import pytest

from entroppy.core import BoundaryType
from entroppy.core.boundaries import BoundaryIndex
from entroppy.resolution.passes import CandidateSelectionPass
from entroppy.resolution.solver import PassContext
from entroppy.resolution.state import DictionaryState


class TestSubstringTyposNotAddedWithNoneBoundary:
    """Test that typos appearing as substrings are not added with NONE boundary."""

    @pytest.mark.slow
    def test_typo_in_middle_of_validation_word_not_none(self) -> None:
        """Typo appearing in middle of validation word must not use NONE boundary."""
        typo_map = {"tain": ["train"]}
        validation_set = {"train", "containing", "maintain"}
        source_words_set = {"train"}

        state = DictionaryState(typo_map)
        validation_index = BoundaryIndex(validation_set)
        source_index = BoundaryIndex(source_words_set)

        pass_context = PassContext(
            validation_set=validation_set,
            filtered_validation_set=validation_set,
            source_words_set=source_words_set,
            user_words_set=set(),
            exclusion_matcher=None,
            exclusion_set=set(),
            validation_index=validation_index,
            source_index=source_index,
            platform=None,
            min_typo_length=2,
            collision_threshold=2.0,
            jobs=1,
            verbose=False,
        )

        pass_obj = CandidateSelectionPass(pass_context)
        pass_obj.run(state)

        tain_corrections = [c for c in state.active_corrections if c[0] == "tain"]
        assert all(c[2] != BoundaryType.NONE for c in tain_corrections)

    @pytest.mark.slow
    def test_ethre_with_incomplete_validation_set_not_none(self) -> None:
        """Typo 'ethre' must not use NONE when it appears in validation words."""
        typo_map = {"ethre": ["there"]}
        # Use full validation set that includes words where 'ethre' appears as substring
        validation_set = {"there", "urethrectomy", "olethreutidae", "brethren", "rethread"}
        source_words_set = {"there"}

        state = DictionaryState(typo_map)
        validation_index = BoundaryIndex(validation_set)
        source_index = BoundaryIndex(source_words_set)

        pass_context = PassContext(
            validation_set=validation_set,
            filtered_validation_set=validation_set,
            source_words_set=source_words_set,
            user_words_set=set(),
            exclusion_matcher=None,
            exclusion_set=set(),
            validation_index=validation_index,
            source_index=source_index,
            platform=None,
            min_typo_length=2,
            collision_threshold=2.0,
            jobs=1,
            verbose=False,
        )

        pass_obj = CandidateSelectionPass(pass_context)
        pass_obj.run(state)

        ethre_corrections = [c for c in state.active_corrections if c[0] == "ethre"]
        assert all(c[2] != BoundaryType.NONE for c in ethre_corrections)
