"""Integration tests for platform substring conflict resolution behavior.

These tests verify that cross-boundary substring conflicts are correctly detected
and resolved, particularly for QMK where boundary markers create substring relationships.
"""

import pytest

from entroppy.core import Config
from entroppy.core.boundaries import BoundaryType
from entroppy.platforms import get_platform_backend
from entroppy.platforms.qmk.formatting import format_boundary_markers
from entroppy.processing.stages import generate_typos, load_dictionaries
from entroppy.resolution.passes import (
    CandidateSelectionPass,
    ConflictRemovalPass,
    PatternGeneralizationPass,
    PlatformConstraintsPass,
    PlatformSubstringConflictPass,
)
from entroppy.resolution.solver import IterativeSolver, PassContext
from entroppy.resolution.state import DictionaryState
from entroppy.utils.suffix_array import SubstringIndex


class TestPlatformSubstringConflicts:
    """Tests for platform substring conflict detection and resolution behavior."""

    def test_suffix_array_finds_shorter_in_longer(self):
        """Suffix array finds shorter typo when querying for it
        (finds ":aemr" when querying "aemr")."""
        formatted_typos = ["aemr", ":aemr"]
        sa = SubstringIndex(formatted_typos)
        matches = sa.find_conflicts("aemr")
        assert 1 in matches

    def test_suffix_array_finds_contained_typo(self):
        """Suffix array finds contained typo when querying for the containing typo
        (finds "aemr" when querying ":aemr").

        When processing ":aemr", we need to check if "aemr" is a substring.
        The suffix array query for ":aemr" MUST return "aemr" (index 0)
        to correctly detect the conflict.
        """
        formatted_typos = ["aemr", ":aemr"]
        sa = SubstringIndex(formatted_typos)
        matches = sa.find_conflicts(":aemr")
        assert 0 in matches, "Should find 'aemr' (index 0) when querying ':aemr'"

    @pytest.mark.slow
    def test_qmk_detects_colon_prefix_substring_conflict(self, tmp_path):
        """QMK detects substring conflict between 'aemr' and ':aemr'."""
        exclude_file = tmp_path / "exclude.txt"
        exclude_file.write_text("")

        include_file = tmp_path / "include.txt"
        include_file.write_text("america\namerican\namericana\n")

        adjacent_file = tmp_path / "adjacent.txt"
        adjacent_file.write_text("a -> s\ne -> w\nm -> n\nr -> t\n")

        output_dir = tmp_path / "output"

        config = Config(
            exclude=str(exclude_file),
            include=str(include_file),
            adjacent_letters=str(adjacent_file),
            output=str(output_dir),
            platform="qmk",
            max_corrections=1000,
            jobs=1,
            max_iterations=10,
        )

        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)

        platform = get_platform_backend(config.platform)
        pass_context = PassContext.from_dictionary_data(
            dictionary_data=dict_data,
            platform=platform,
            min_typo_length=config.min_typo_length,
            collision_threshold=config.freq_ratio,
            jobs=config.jobs,
            verbose=False,
        )

        state = DictionaryState(
            raw_typo_map=typo_result.typo_map,
            debug_words=config.debug_words,
            debug_typo_matcher=config.debug_typo_matcher,
        )

        passes = [
            CandidateSelectionPass(pass_context),
            PatternGeneralizationPass(pass_context),
            ConflictRemovalPass(pass_context),
            PlatformSubstringConflictPass(pass_context),
            PlatformConstraintsPass(pass_context),
        ]

        solver = IterativeSolver(passes, max_iterations=config.max_iterations)
        solver_result = solver.solve(state)

        # Get final corrections and generate output (like pipeline does)
        all_corrections = solver_result.corrections + solver_result.patterns
        ranked_corrections = platform.rank_corrections(
            all_corrections,
            solver_result.patterns,
            state.pattern_replacements,
            dict_data.user_words_set,
            config,
        )

        # Apply platform constraints
        constraints = platform.get_constraints()
        if constraints.max_corrections and len(ranked_corrections) > constraints.max_corrections:
            final_corrections = ranked_corrections[: constraints.max_corrections]
        else:
            final_corrections = ranked_corrections

        # Generate output file
        platform.generate_output(final_corrections, config.output, config)

        # Read the output file
        output_file = list(output_dir.glob("*.txt"))[0]
        output_content = output_file.read_text()

        # Should not contain both 'aemr' and ':aemr'
        has_aemr = "aemr ->" in output_content or "aemr\t" in output_content
        has_colon_aemr = ":aemr ->" in output_content or ":aemr\t" in output_content

        assert not (
            has_aemr and has_colon_aemr
        ), "Output should not contain both 'aemr' and ':aemr'"

    @pytest.mark.slow
    def test_qmk_removes_all_corrections_with_conflicting_formatted_typo(self, tmp_path):
        """QMK removes ALL corrections with a conflicting formatted typo, not just some.

        This test ensures that when a substring conflict is detected between two
        formatted typos (e.g., 'aemr' vs ':aemr'), ALL corrections with the losing
        formatted typo are removed, regardless of which word they come from.

        Bug regression test: Previously, only corrections that were in processed
        conflict pairs would be removed, leaving other corrections with the same
        formatted typo still active.

        This test manually creates the bug scenario by adding multiple corrections
        with the same formatted typo to the state, bypassing collision resolution.
        """
        exclude_file = tmp_path / "exclude.txt"
        exclude_file.write_text("")

        # Use words that generate 'aemr' typo - collision resolution will pick one,
        # but we'll manually add multiple to test the bug scenario
        include_file = tmp_path / "include.txt"
        include_file.write_text("america\namerican\namericana\n")

        adjacent_file = tmp_path / "adjacent.txt"
        adjacent_file.write_text("a -> s\ne -> w\nm -> n\nr -> t\n")

        output_dir = tmp_path / "output"

        config = Config(
            exclude=str(exclude_file),
            include=str(include_file),
            adjacent_letters=str(adjacent_file),
            output=str(output_dir),
            platform="qmk",
            max_corrections=1000,
            jobs=1,
            max_iterations=10,
        )

        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)

        platform = get_platform_backend(config.platform)
        pass_context = PassContext.from_dictionary_data(
            dictionary_data=dict_data,
            platform=platform,
            min_typo_length=config.min_typo_length,
            collision_threshold=config.freq_ratio,
            jobs=config.jobs,
            verbose=False,
        )

        state = DictionaryState(
            raw_typo_map=typo_result.typo_map,
            debug_words=config.debug_words,
            debug_typo_matcher=config.debug_typo_matcher,
        )

        # Run passes up to but not including PlatformSubstringConflictPass
        # to set up the state, then manually inject multiple corrections with same formatted typo
        CandidateSelectionPass(pass_context).run(state)
        PatternGeneralizationPass(pass_context).run(state)
        ConflictRemovalPass(pass_context).run(state)

        # Manually add multiple corrections with 'aemr' (NONE boundary) to test bug scenario
        # This simulates the case where multiple corrections share the same formatted typo
        # (which could happen with patterns or if collision resolution doesn't remove them)
        state.add_correction("aemr", "america", BoundaryType.NONE, "test")
        state.add_correction("aemr", "american", BoundaryType.NONE, "test")
        state.add_correction("aemr", "americana", BoundaryType.NONE, "test")
        # Also add one with LEFT boundary to create the conflict
        state.add_correction("aemr", "america", BoundaryType.LEFT, "test")

        # Now run PlatformSubstringConflictPass - it should remove ALL corrections with losing formatted typo
        PlatformSubstringConflictPass(pass_context).run(state)
        PlatformConstraintsPass(pass_context).run(state)

        # Check what corrections remain after PlatformSubstringConflictPass
        aemr_corrections = []
        colon_aemr_corrections = []
        for corr in state.active_corrections | state.active_patterns:
            typo, word, boundary = corr
            formatted = format_boundary_markers(typo, boundary)
            if formatted == "aemr":
                aemr_corrections.append(corr)
            elif formatted == ":aemr":
                colon_aemr_corrections.append(corr)

        # CRITICAL: Either ALL 'aemr' corrections are removed OR ALL ':aemr' corrections are removed
        # We should never have both, and we should never have partial removal
        # This ensures that when a substring conflict is resolved, ALL corrections with the losing
        # formatted typo are removed, not just the ones in processed conflict pairs.
        assert (len(aemr_corrections) == 0 and len(colon_aemr_corrections) >= 0) or (
            len(aemr_corrections) >= 0 and len(colon_aemr_corrections) == 0
        ), (
            f"Substring conflict not fully resolved: found {len(aemr_corrections)} 'aemr' corrections "
            f"and {len(colon_aemr_corrections)} ':aemr' corrections. "
            "ALL corrections with the losing formatted typo must be removed, not just some. "
            f"'aemr' corrections: {aemr_corrections}, ':aemr' corrections: {colon_aemr_corrections}"
        )

    @pytest.mark.slow
    def test_qmk_prefers_less_restrictive_boundary_when_safe(self, tmp_path):
        """QMK prefers NONE boundary over LEFT when NONE doesn't cause false triggers."""
        exclude_file = tmp_path / "exclude.txt"
        exclude_file.write_text("")

        include_file = tmp_path / "include.txt"
        include_file.write_text("america\namerican\namericana\n")

        adjacent_file = tmp_path / "adjacent.txt"
        adjacent_file.write_text("a -> s\ne -> w\nm -> n\nr -> t\n")

        output_dir = tmp_path / "output"

        config = Config(
            exclude=str(exclude_file),
            include=str(include_file),
            adjacent_letters=str(adjacent_file),
            output=str(output_dir),
            platform="qmk",
            max_corrections=1000,
            jobs=1,
            max_iterations=10,
        )

        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)

        platform = get_platform_backend(config.platform)
        pass_context = PassContext.from_dictionary_data(
            dictionary_data=dict_data,
            platform=platform,
            min_typo_length=config.min_typo_length,
            collision_threshold=config.freq_ratio,
            jobs=config.jobs,
            verbose=False,
        )

        state = DictionaryState(
            raw_typo_map=typo_result.typo_map,
            debug_words=config.debug_words,
            debug_typo_matcher=config.debug_typo_matcher,
        )

        passes = [
            CandidateSelectionPass(pass_context),
            PatternGeneralizationPass(pass_context),
            ConflictRemovalPass(pass_context),
            PlatformSubstringConflictPass(pass_context),
            PlatformConstraintsPass(pass_context),
        ]

        solver = IterativeSolver(passes, max_iterations=config.max_iterations)
        solver_result = solver.solve(state)

        # Get final corrections and generate output (like pipeline does)
        all_corrections = solver_result.corrections + solver_result.patterns
        ranked_corrections = platform.rank_corrections(
            all_corrections,
            solver_result.patterns,
            state.pattern_replacements,
            dict_data.user_words_set,
            config,
        )

        # Apply platform constraints
        constraints = platform.get_constraints()
        if constraints.max_corrections and len(ranked_corrections) > constraints.max_corrections:
            final_corrections = ranked_corrections[: constraints.max_corrections]
        else:
            final_corrections = ranked_corrections

        # Generate output file
        platform.generate_output(final_corrections, config.output, config)

        # Read the output file
        output_file = list(output_dir.glob("*.txt"))[0]
        output_content = output_file.read_text()

        # Should contain 'aemr' (NONE boundary) but not ':aemr' (LEFT boundary)
        has_aemr = "aemr ->" in output_content or "aemr\t" in output_content

        assert has_aemr, "Output should contain 'aemr' with NONE boundary when it's safe"

    @pytest.mark.slow
    def test_qmk_removes_colon_prefix_when_core_typo_is_safe(self, tmp_path):
        """QMK removes ':aemr' when 'aemr' with NONE boundary is safe."""
        exclude_file = tmp_path / "exclude.txt"
        exclude_file.write_text("")

        include_file = tmp_path / "include.txt"
        include_file.write_text("america\namerican\namericana\n")

        adjacent_file = tmp_path / "adjacent.txt"
        adjacent_file.write_text("a -> s\ne -> w\nm -> n\nr -> t\n")

        output_dir = tmp_path / "output"

        config = Config(
            exclude=str(exclude_file),
            include=str(include_file),
            adjacent_letters=str(adjacent_file),
            output=str(output_dir),
            platform="qmk",
            max_corrections=1000,
            jobs=1,
            max_iterations=10,
        )

        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)

        platform = get_platform_backend(config.platform)
        pass_context = PassContext.from_dictionary_data(
            dictionary_data=dict_data,
            platform=platform,
            min_typo_length=config.min_typo_length,
            collision_threshold=config.freq_ratio,
            jobs=config.jobs,
            verbose=False,
        )

        state = DictionaryState(
            raw_typo_map=typo_result.typo_map,
            debug_words=config.debug_words,
            debug_typo_matcher=config.debug_typo_matcher,
        )

        passes = [
            CandidateSelectionPass(pass_context),
            PatternGeneralizationPass(pass_context),
            ConflictRemovalPass(pass_context),
            PlatformSubstringConflictPass(pass_context),
            PlatformConstraintsPass(pass_context),
        ]

        solver = IterativeSolver(passes, max_iterations=config.max_iterations)
        solver_result = solver.solve(state)

        # Get final corrections and generate output (like pipeline does)
        all_corrections = solver_result.corrections + solver_result.patterns
        ranked_corrections = platform.rank_corrections(
            all_corrections,
            solver_result.patterns,
            state.pattern_replacements,
            dict_data.user_words_set,
            config,
        )

        # Apply platform constraints
        constraints = platform.get_constraints()
        if constraints.max_corrections and len(ranked_corrections) > constraints.max_corrections:
            final_corrections = ranked_corrections[: constraints.max_corrections]
        else:
            final_corrections = ranked_corrections

        # Generate output file
        platform.generate_output(final_corrections, config.output, config)

        # Read the output file
        output_file = list(output_dir.glob("*.txt"))[0]
        output_content = output_file.read_text()

        # Should not contain ':aemr'
        has_colon_aemr = ":aemr ->" in output_content or ":aemr\t" in output_content

        assert not has_colon_aemr, "Output should not contain ':aemr' when 'aemr' with NONE is safe"

    @pytest.mark.slow
    def test_qmk_output_compiles_without_substring_errors(self, tmp_path):
        """QMK output should not contain substring conflicts that cause compilation errors."""
        exclude_file = tmp_path / "exclude.txt"
        exclude_file.write_text("")

        include_file = tmp_path / "include.txt"
        include_file.write_text("america\namerican\namericana\n")

        adjacent_file = tmp_path / "adjacent.txt"
        adjacent_file.write_text("a -> s\ne -> w\nm -> n\nr -> t\n")

        output_dir = tmp_path / "output"

        config = Config(
            exclude=str(exclude_file),
            include=str(include_file),
            adjacent_letters=str(adjacent_file),
            output=str(output_dir),
            platform="qmk",
            max_corrections=1000,
            jobs=1,
            max_iterations=10,
        )

        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)

        platform = get_platform_backend(config.platform)
        pass_context = PassContext.from_dictionary_data(
            dictionary_data=dict_data,
            platform=platform,
            min_typo_length=config.min_typo_length,
            collision_threshold=config.freq_ratio,
            jobs=config.jobs,
            verbose=False,
        )

        state = DictionaryState(
            raw_typo_map=typo_result.typo_map,
            debug_words=config.debug_words,
            debug_typo_matcher=config.debug_typo_matcher,
        )

        passes = [
            CandidateSelectionPass(pass_context),
            PatternGeneralizationPass(pass_context),
            ConflictRemovalPass(pass_context),
            PlatformSubstringConflictPass(pass_context),
            PlatformConstraintsPass(pass_context),
        ]

        solver = IterativeSolver(passes, max_iterations=config.max_iterations)
        solver_result = solver.solve(state)

        # Get final corrections and generate output (like pipeline does)
        all_corrections = solver_result.corrections + solver_result.patterns
        ranked_corrections = platform.rank_corrections(
            all_corrections,
            solver_result.patterns,
            state.pattern_replacements,
            dict_data.user_words_set,
            config,
        )

        # Apply platform constraints
        constraints = platform.get_constraints()
        if constraints.max_corrections and len(ranked_corrections) > constraints.max_corrections:
            final_corrections = ranked_corrections[: constraints.max_corrections]
        else:
            final_corrections = ranked_corrections

        # Generate output file
        platform.generate_output(final_corrections, config.output, config)

        # Read the output file
        output_file = list(output_dir.glob("*.txt"))[0]
        output_lines = output_file.read_text().strip().split("\n")

        # Extract all formatted typos (left side of -> or tab)
        formatted_typos = []
        for line in output_lines:
            if "->" in line:
                formatted_typo = line.split("->")[0].strip()
            elif "\t" in line:
                formatted_typo = line.split("\t")[0].strip()
            else:
                continue
            if formatted_typo:
                formatted_typos.append(formatted_typo)

        # Check that no formatted typo is a substring of another
        for i, typo1 in enumerate(formatted_typos):
            for typo2 in formatted_typos[i + 1 :]:
                # Skip if they're identical
                if typo1 == typo2:
                    continue
                # Check if one is a substring of the other
                shorter, longer = (typo1, typo2) if len(typo1) < len(typo2) else (typo2, typo1)
                if shorter in longer and shorter != longer:
                    assert (
                        False
                    ), f"Substring conflict found: '{shorter}' is substring of '{longer}'"

    @pytest.mark.slow
    def test_qmk_handles_suffix_boundary_conflicts(self, tmp_path):
        """QMK detects substring conflicts with suffix boundaries (e.g., 'typo' vs 'typo:')."""
        exclude_file = tmp_path / "exclude.txt"
        exclude_file.write_text("")

        include_file = tmp_path / "include.txt"
        include_file.write_text("test\nbest\nrest\n")

        adjacent_file = tmp_path / "adjacent.txt"
        adjacent_file.write_text("t -> y\ne -> w\ns -> a\nb -> v\nr -> t\n")

        output_dir = tmp_path / "output"

        config = Config(
            exclude=str(exclude_file),
            include=str(include_file),
            adjacent_letters=str(adjacent_file),
            output=str(output_dir),
            platform="qmk",
            max_corrections=1000,
            jobs=1,
            max_iterations=10,
        )

        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)

        platform = get_platform_backend(config.platform)
        pass_context = PassContext.from_dictionary_data(
            dictionary_data=dict_data,
            platform=platform,
            min_typo_length=config.min_typo_length,
            collision_threshold=config.freq_ratio,
            jobs=config.jobs,
            verbose=False,
        )

        state = DictionaryState(
            raw_typo_map=typo_result.typo_map,
            debug_words=config.debug_words,
            debug_typo_matcher=config.debug_typo_matcher,
        )

        passes = [
            CandidateSelectionPass(pass_context),
            PatternGeneralizationPass(pass_context),
            ConflictRemovalPass(pass_context),
            PlatformSubstringConflictPass(pass_context),
            PlatformConstraintsPass(pass_context),
        ]

        solver = IterativeSolver(passes, max_iterations=config.max_iterations)
        solver_result = solver.solve(state)

        # Get final corrections and generate output (like pipeline does)
        all_corrections = solver_result.corrections + solver_result.patterns
        ranked_corrections = platform.rank_corrections(
            all_corrections,
            solver_result.patterns,
            state.pattern_replacements,
            dict_data.user_words_set,
            config,
        )

        # Apply platform constraints
        constraints = platform.get_constraints()
        if constraints.max_corrections and len(ranked_corrections) > constraints.max_corrections:
            final_corrections = ranked_corrections[: constraints.max_corrections]
        else:
            final_corrections = ranked_corrections

        # Generate output file
        platform.generate_output(final_corrections, config.output, config)

        # Read the output file
        output_file = list(output_dir.glob("*.txt"))[0]
        output_lines = output_file.read_text().strip().split("\n")

        # Extract all formatted typos
        formatted_typos = []
        for line in output_lines:
            if "->" in line:
                formatted_typo = line.split("->")[0].strip()
            elif "\t" in line:
                formatted_typo = line.split("\t")[0].strip()
            else:
                continue
            if formatted_typo:
                formatted_typos.append(formatted_typo)

        # Check that no typo ending with ':' is a substring of a typo without ':'
        # (e.g., 'test' should not coexist with 'test:')
        for typo1 in formatted_typos:
            for typo2 in formatted_typos:
                if typo1 == typo2:
                    continue
                # If one ends with ':' and the other doesn't, check substring relationship
                if typo1.endswith(":") and not typo2.endswith(":"):
                    core1 = typo1[:-1]  # Remove trailing ':'
                    if core1 == typo2:
                        assert (
                            False
                        ), f"Substring conflict: '{typo2}' and '{typo1}' should not both exist"

    @pytest.mark.slow
    def test_qmk_handles_both_boundary_conflicts(self, tmp_path):
        """QMK detects substring conflicts with BOTH boundaries (e.g., 'typo' vs ':typo:')."""
        exclude_file = tmp_path / "exclude.txt"
        exclude_file.write_text("")

        include_file = tmp_path / "include.txt"
        include_file.write_text("word\n")

        adjacent_file = tmp_path / "adjacent.txt"
        adjacent_file.write_text("w -> q\no -> i\nr -> t\nd -> s\n")

        output_dir = tmp_path / "output"

        config = Config(
            exclude=str(exclude_file),
            include=str(include_file),
            adjacent_letters=str(adjacent_file),
            output=str(output_dir),
            platform="qmk",
            max_corrections=1000,
            jobs=1,
            max_iterations=10,
        )

        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)

        platform = get_platform_backend(config.platform)
        pass_context = PassContext.from_dictionary_data(
            dictionary_data=dict_data,
            platform=platform,
            min_typo_length=config.min_typo_length,
            collision_threshold=config.freq_ratio,
            jobs=config.jobs,
            verbose=False,
        )

        state = DictionaryState(
            raw_typo_map=typo_result.typo_map,
            debug_words=config.debug_words,
            debug_typo_matcher=config.debug_typo_matcher,
        )

        passes = [
            CandidateSelectionPass(pass_context),
            PatternGeneralizationPass(pass_context),
            ConflictRemovalPass(pass_context),
            PlatformSubstringConflictPass(pass_context),
            PlatformConstraintsPass(pass_context),
        ]

        solver = IterativeSolver(passes, max_iterations=config.max_iterations)
        solver_result = solver.solve(state)

        # Get final corrections and generate output (like pipeline does)
        all_corrections = solver_result.corrections + solver_result.patterns
        ranked_corrections = platform.rank_corrections(
            all_corrections,
            solver_result.patterns,
            state.pattern_replacements,
            dict_data.user_words_set,
            config,
        )

        # Apply platform constraints
        constraints = platform.get_constraints()
        if constraints.max_corrections and len(ranked_corrections) > constraints.max_corrections:
            final_corrections = ranked_corrections[: constraints.max_corrections]
        else:
            final_corrections = ranked_corrections

        # Generate output file
        platform.generate_output(final_corrections, config.output, config)

        # Read the output file
        output_file = list(output_dir.glob("*.txt"))[0]
        output_lines = output_file.read_text().strip().split("\n")

        # Extract all formatted typos
        formatted_typos = []
        for line in output_lines:
            if "->" in line:
                formatted_typo = line.split("->")[0].strip()
            elif "\t" in line:
                formatted_typo = line.split("\t")[0].strip()
            else:
                continue
            if formatted_typo:
                formatted_typos.append(formatted_typo)

        # Check that no typo with ':typo:' is a substring of a typo without boundaries
        for typo1 in formatted_typos:
            for typo2 in formatted_typos:
                if typo1 == typo2:
                    continue
                # If one has both boundaries and the other has none, check substring relationship
                has_both_boundaries = typo1.startswith(":") and typo1.endswith(":")
                has_no_boundaries = not (typo2.startswith(":") or typo2.endswith(":"))
                if has_both_boundaries and has_no_boundaries:
                    core1 = typo1.strip(":")  # Remove both colons
                    if core1 == typo2:
                        assert (
                            False
                        ), f"Substring conflict: '{typo2}' and '{typo1}' should not both exist"

    @pytest.mark.slow
    def test_qmk_resolves_colon_prefix_substring_conflict_in_middle(self, tmp_path):
        """QMK resolves substring conflict where shorter typo is in middle of longer.

        Tests the case where ':abot' (LEFT boundary) is a substring of ':abotu:' (BOTH boundary).
        QMK compiler will reject this with: "Typos may not be substrings of one another,
        otherwise the longer typo would never trigger: ':abotu:' vs ':abot'."

        This test ensures that only one of these corrections remains in the output.
        """
        exclude_file = tmp_path / "exclude.txt"
        exclude_file.write_text("")

        include_file = tmp_path / "include.txt"
        include_file.write_text("about\n")

        adjacent_file = tmp_path / "adjacent.txt"
        adjacent_file.write_text("a -> s\no -> i\nb -> v\nt -> y\nu -> i\n")

        output_dir = tmp_path / "output"

        config = Config(
            exclude=str(exclude_file),
            include=str(include_file),
            adjacent_letters=str(adjacent_file),
            output=str(output_dir),
            platform="qmk",
            max_corrections=1000,
            jobs=1,
            max_iterations=10,
        )

        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)

        platform = get_platform_backend(config.platform)
        pass_context = PassContext.from_dictionary_data(
            dictionary_data=dict_data,
            platform=platform,
            min_typo_length=config.min_typo_length,
            collision_threshold=config.freq_ratio,
            jobs=config.jobs,
            verbose=False,
        )

        state = DictionaryState(
            raw_typo_map=typo_result.typo_map,
            debug_words=config.debug_words,
            debug_typo_matcher=config.debug_typo_matcher,
        )

        passes = [
            CandidateSelectionPass(pass_context),
            PatternGeneralizationPass(pass_context),
            ConflictRemovalPass(pass_context),
            PlatformSubstringConflictPass(pass_context),
            PlatformConstraintsPass(pass_context),
        ]

        solver = IterativeSolver(passes, max_iterations=config.max_iterations)
        solver_result = solver.solve(state)

        # Get final corrections and generate output (like pipeline does)
        all_corrections = solver_result.corrections + solver_result.patterns
        ranked_corrections = platform.rank_corrections(
            all_corrections,
            solver_result.patterns,
            state.pattern_replacements,
            dict_data.user_words_set,
            config,
        )

        # Apply platform constraints
        constraints = platform.get_constraints()
        if constraints.max_corrections and len(ranked_corrections) > constraints.max_corrections:
            final_corrections = ranked_corrections[: constraints.max_corrections]
        else:
            final_corrections = ranked_corrections

        # Generate output file
        platform.generate_output(final_corrections, config.output, config)

        # Read the output file
        output_file = list(output_dir.glob("*.txt"))[0]
        output_content = output_file.read_text()

        # Extract all formatted typos (left side of -> or tab)
        formatted_typos = []
        for line in output_content.strip().split("\n"):
            if "->" in line:
                formatted_typo = line.split("->")[0].strip()
            elif "\t" in line:
                formatted_typo = line.split("\t")[0].strip()
            else:
                continue
            if formatted_typo:
                formatted_typos.append(formatted_typo)

        # Should not contain both ':abot' and ':abotu:'
        has_colon_abot = ":abot" in formatted_typos
        has_colon_abotu = ":abotu:" in formatted_typos

        assert not (has_colon_abot and has_colon_abotu), (
            "Output should not contain both ':abot' and ':abotu:' - "
            "QMK compiler rejects this with 'Typos may not be substrings of one another' error. "
            f"Found formatted typos: {[t for t in formatted_typos if 'abot' in t]}"
        )
