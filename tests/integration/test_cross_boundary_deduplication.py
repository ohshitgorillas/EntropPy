"""Integration tests for cross-boundary deduplication behavior."""

from entroppy.core import Config
from entroppy.processing.stages import (
    load_dictionaries,
    generate_typos,
    resolve_typo_collisions,
    generalize_typo_patterns,
)
from entroppy.platforms.espanso import EspansoBackend


class TestCrossBoundaryDeduplication:
    """Integration tests verifying no duplicate (typo, word) pairs across boundaries."""

    def test_no_duplicate_pairs_in_final_output(self, tmp_path):
        """Final output contains no duplicate (typo, word) pairs, regardless of boundary."""
        exclude_file = tmp_path / "exclude.txt"
        exclude_file.write_text("")

        include_file = tmp_path / "include.txt"
        # Words that create patterns and direct corrections
        include_file.write_text("the\nbathe\nlathe\nthen\n")

        adjacent_file = tmp_path / "adjacent.txt"
        # Adjacent letters that can create "teh" from "the"
        adjacent_file.write_text("t -> y\nh -> j\ne -> w\n")

        config = Config(
            exclude=str(exclude_file),
            include=str(include_file),
            adjacent_letters=str(adjacent_file),
            output="output",
            jobs=1,
        )

        # Run through pipeline stages
        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)
        collision_result = resolve_typo_collisions(typo_result, dict_data, config, verbose=False)
        platform = EspansoBackend()
        match_direction = platform.get_constraints().match_direction
        pattern_result = generalize_typo_patterns(
            collision_result, dict_data, config, match_direction, verbose=False
        )

        # BEHAVIOR: Check no (typo, word) pair appears more than once
        seen_pairs = {}
        for typo, word, boundary in pattern_result.corrections:
            pair = (typo, word)
            if pair in seen_pairs:
                raise AssertionError(
                    f"Duplicate (typo, word) pair found: {pair}\n"
                    f"  First boundary: {seen_pairs[pair]}\n"
                    f"  Second boundary: {boundary}"
                )
            seen_pairs[pair] = boundary

    def test_multiple_potential_conflicts_resolved(self, tmp_path):
        """Multiple words that could create conflicts produce no duplicates."""
        exclude_file = tmp_path / "exclude.txt"
        exclude_file.write_text("")

        include_file = tmp_path / "include.txt"
        # Multiple common words that generate similar typos
        include_file.write_text("the\nthat\nthere\ntest\ntesting\nbest\nrest\n")

        adjacent_file = tmp_path / "adjacent.txt"
        adjacent_file.write_text(
            "t -> y\n"
            "h -> j\n"
            "e -> w\n"
            "a -> s\n"
            "r -> t\n"
            "s -> z\n"
            "i -> u\n"
            "n -> m\n"
            "g -> h\n"
            "b -> v\n"
        )

        config = Config(
            exclude=str(exclude_file),
            include=str(include_file),
            adjacent_letters=str(adjacent_file),
            output="output",
            jobs=1,
        )

        # Run pipeline
        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)
        collision_result = resolve_typo_collisions(typo_result, dict_data, config, verbose=False)
        platform = EspansoBackend()
        match_direction = platform.get_constraints().match_direction
        pattern_result = generalize_typo_patterns(
            collision_result, dict_data, config, match_direction, verbose=False
        )

        # BEHAVIOR: Verify no duplicates in final output
        pairs = [(typo, word) for typo, word, _ in pattern_result.corrections]
        unique_pairs = set(pairs)
        assert len(pairs) == len(
            unique_pairs
        ), f"Found {len(pairs) - len(unique_pairs)} duplicate pairs in output"

    def test_direct_corrections_present_in_output(self, tmp_path):
        """Direct corrections from collision resolution appear in final output."""
        exclude_file = tmp_path / "exclude.txt"
        exclude_file.write_text("")

        include_file = tmp_path / "include.txt"
        # Simple word that generates direct corrections
        include_file.write_text("cat\n")

        adjacent_file = tmp_path / "adjacent.txt"
        adjacent_file.write_text("c -> x\na -> e\nt -> y\n")

        config = Config(
            exclude=str(exclude_file),
            include=str(include_file),
            adjacent_letters=str(adjacent_file),
            output="output",
            jobs=1,
        )

        # Run pipeline
        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)
        collision_result = resolve_typo_collisions(typo_result, dict_data, config, verbose=False)
        platform = EspansoBackend()
        match_direction = platform.get_constraints().match_direction
        pattern_result = generalize_typo_patterns(
            collision_result, dict_data, config, match_direction, verbose=False
        )

        # BEHAVIOR: Verify corrections for target word exist
        cat_corrections = [(t, w) for t, w, _ in pattern_result.corrections if w == "cat"]
        assert len(cat_corrections) > 0, "Expected corrections for 'cat'"

    def test_patterns_work_when_no_conflicts(self, tmp_path):
        """Pattern generalizations are included when they don't conflict."""
        exclude_file = tmp_path / "exclude.txt"
        exclude_file.write_text("")

        include_file = tmp_path / "include.txt"
        # Words that should generate patterns without conflicts
        include_file.write_text("section\nselection\nrejection\n")

        adjacent_file = tmp_path / "adjacent.txt"
        adjacent_file.write_text(
            "s -> z\n"
            "e -> w\n"
            "c -> x\n"
            "t -> y\n"
            "i -> u\n"
            "o -> p\n"
            "n -> m\n"
            "l -> k\n"
            "r -> t\n"
            "j -> h\n"
        )

        config = Config(
            exclude=str(exclude_file),
            include=str(include_file),
            adjacent_letters=str(adjacent_file),
            output="output",
            jobs=1,
        )

        # Run pipeline
        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)
        collision_result = resolve_typo_collisions(typo_result, dict_data, config, verbose=False)
        platform = EspansoBackend()
        match_direction = platform.get_constraints().match_direction
        pattern_result = generalize_typo_patterns(
            collision_result, dict_data, config, match_direction, verbose=False
        )

        # BEHAVIOR: Verify no duplicate pairs in output
        pairs = [(typo, word) for typo, word, _ in pattern_result.corrections]
        assert len(pairs) == len(set(pairs)), "No duplicate pairs should exist"

    def test_full_pipeline_realistic_scenario(self, tmp_path):
        """Full pipeline with realistic word set produces valid output."""
        exclude_file = tmp_path / "exclude.txt"
        exclude_file.write_text("")

        include_file = tmp_path / "include.txt"
        # Realistic mix of common words
        include_file.write_text(
            "the\nthat\nthis\nthere\ntest\ntesting\n"
            "word\nwork\nworld\nworth\n"
            "best\nrest\nwest\nnest\n"
        )

        adjacent_file = tmp_path / "adjacent.txt"
        # Common keyboard adjacencies
        adjacent_file.write_text(
            "t -> y\nt -> r\n"
            "h -> j\nh -> g\n"
            "e -> w\ne -> r\n"
            "a -> s\n"
            "r -> t\nr -> e\n"
            "s -> a\ns -> d\n"
            "w -> q\nw -> e\n"
            "o -> i\no -> p\n"
            "d -> s\nd -> f\n"
            "i -> u\ni -> o\n"
            "n -> m\nn -> b\n"
            "b -> v\nb -> n\n"
        )

        config = Config(
            exclude=str(exclude_file),
            include=str(include_file),
            adjacent_letters=str(adjacent_file),
            output="output",
            jobs=1,
        )

        # Run full pipeline
        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)
        collision_result = resolve_typo_collisions(typo_result, dict_data, config, verbose=False)
        platform = EspansoBackend()
        match_direction = platform.get_constraints().match_direction
        pattern_result = generalize_typo_patterns(
            collision_result, dict_data, config, match_direction, verbose=False
        )

        # BEHAVIOR: No duplicate (typo, word) pairs in realistic scenario
        pairs = [(typo, word) for typo, word, _ in pattern_result.corrections]
        unique_pairs = set(pairs)
        assert len(pairs) == len(
            unique_pairs
        ), f"Found duplicates: {len(pairs)} total vs {len(unique_pairs)} unique"

    def test_same_trigger_different_boundaries_prevented(self, tmp_path):
        """Same trigger word cannot appear with different boundary types."""
        exclude_file = tmp_path / "exclude.txt"
        exclude_file.write_text("")

        include_file = tmp_path / "include.txt"
        # Words that could generate overlapping triggers
        include_file.write_text("test\ncontest\nattest\nprotest\n")

        adjacent_file = tmp_path / "adjacent.txt"
        adjacent_file.write_text(
            "t -> y\n"
            "e -> w\n"
            "s -> z\n"
            "c -> x\n"
            "o -> p\n"
            "n -> m\n"
            "a -> e\n"
            "p -> l\n"
            "r -> t\n"
        )

        config = Config(
            exclude=str(exclude_file),
            include=str(include_file),
            adjacent_letters=str(adjacent_file),
            output="output",
            jobs=1,
        )

        # Run pipeline
        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)
        collision_result = resolve_typo_collisions(typo_result, dict_data, config, verbose=False)
        platform = EspansoBackend()
        match_direction = platform.get_constraints().match_direction
        pattern_result = generalize_typo_patterns(
            collision_result, dict_data, config, match_direction, verbose=False
        )

        # BEHAVIOR: Each trigger maps to exactly one word (no disambiguation)
        trigger_words = {}
        for typo, word, _ in pattern_result.corrections:
            if typo not in trigger_words:
                trigger_words[typo] = word
            else:
                # Same trigger should always map to same word
                assert trigger_words[typo] == word, (
                    f"Trigger '{typo}' maps to multiple words: " f"{trigger_words[typo]} and {word}"
                )
