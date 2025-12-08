"""Regression tests for debug word/typo logging across all pipeline phases.

This test suite verifies that debug word and debug typo logging works correctly
at each phase of the program:

1. Dict loading: debug word only
2-7. Typo generation and every phase after: both debug word AND typo
"""

import io

import pytest
from loguru import logger

from entroppy.core import Config
from entroppy.platforms import get_platform_backend
from entroppy.processing.stages import generate_typos, load_dictionaries
from entroppy.processing.pipeline_stages import run_stage_3_6_solver, run_stage_7_ranking
from entroppy.utils.debug import DebugTypoMatcher
from entroppy.utils.logging import setup_logger


def _setup_dict_loading_test(tmp_path):
    """Helper function to set up test files and config for dict loading tests."""
    exclude_file = tmp_path / "exclude.txt"
    exclude_file.write_text("")

    include_file = tmp_path / "include.txt"
    include_file.write_text("the\nthen\nthere\nthem\nthey\nbathe\nwhether\nweather\n")

    return Config(
        exclude=str(exclude_file),
        include=str(include_file),
        debug_words=["the"],
        debug_typos=["hte"],
        debug=True,
        verbose=True,
        top_n=100,
        jobs=1,
    )


def test_debug_word_logging_during_dict_loading(tmp_path):
    """Regression test: Verify debug word logging appears during Stage 1 (dict loading).

    This test verifies that when debug_words is set and debug=True, debug word
    logging messages appear during the dictionary loading phase.
    """
    config = _setup_dict_loading_test(tmp_path)

    # Setup logger to capture debug output
    setup_logger(verbose=True, debug=True)

    # Capture log messages using StringIO sink
    # Add after setup_logger so it doesn't get removed
    log_capture = io.StringIO()
    handler_id = logger.add(
        log_capture,
        level="DEBUG",
        format="{message}",
    )

    try:
        # Run dictionary loading (Stage 1)
        dict_data = load_dictionaries(config, verbose=False)

        # Get captured log text
        log_text = log_capture.getvalue()
        assert "[DEBUG WORD: 'the']" in log_text, (
            f"Expected debug word logging for 'the' in Stage 1, but not found. "
            f"Captured messages:\n{log_text}"
        )
        assert "[Stage 1]" in log_text, (
            f"Expected '[Stage 1]' marker in debug output, but not found. "
            f"Captured messages:\n{log_text}"
        )

        # Verify the word was actually loaded
        assert (
            "the" in dict_data.source_words_set or "the" in dict_data.user_words_set
        ), "Test word 'the' should be in source words or user words"

    finally:
        logger.remove(handler_id)


def _setup_typo_generation_test(tmp_path):
    """Helper function to set up test files and config for typo generation tests."""
    exclude_file = tmp_path / "exclude.txt"
    exclude_file.write_text("")

    include_file = tmp_path / "include.txt"
    # Use "the" which is definitely in top 1000 words (rank 1)
    # and will generate typos like "hte", "teh", etc.
    include_file.write_text("the\n")

    # Create config with debug word and/or typo enabled
    config = Config(
        exclude=str(exclude_file),
        include=str(include_file),
        debug_words=["the"],  # Use list, not set (validator doesn't handle sets)
        debug_typos=["hte"],  # Common typo of "the"
        debug=True,
        verbose=True,
        top_n=10,  # Use a reasonable top_n so "the" is definitely included
        jobs=1,
    )

    # Manually create debug_typo_matcher (normally done in __main__.py)
    if config.debug_typos:
        config.debug_typo_matcher = DebugTypoMatcher.from_patterns(config.debug_typos)

    return config


def test_debug_word_logging_appears_in_stage_2(tmp_path):
    """Regression test: Verify debug word logging appears during Stage 2 (typo generation)."""
    config = _setup_typo_generation_test(tmp_path)

    # Setup logger to capture debug output
    setup_logger(verbose=True, debug=True)

    # Capture log messages using StringIO sink
    log_capture = io.StringIO()
    handler_id = logger.add(
        log_capture,
        level="DEBUG",
        format="{message}",
    )

    try:
        # Load dictionaries first
        dict_data = load_dictionaries(config, verbose=False)

        # Run typo generation (Stage 2)
        generate_typos(dict_data, config, verbose=False)

        # Get captured log text
        log_text = log_capture.getvalue()
        assert "[DEBUG WORD: 'the']" in log_text and "[Stage 2]" in log_text, (
            f"Expected debug word logging for 'the' in Stage 2, but not found. "
            f"Captured messages:\n{log_text[:500]}"
        )
    finally:
        logger.remove(handler_id)


def test_debug_typo_logging_appears_in_stage_2(tmp_path):
    """Regression test: Verify debug typo logging appears during Stage 2 (typo generation)."""
    config = _setup_typo_generation_test(tmp_path)

    # Setup logger to capture debug output
    setup_logger(verbose=True, debug=True)

    # Capture log messages using StringIO sink
    log_capture = io.StringIO()
    handler_id = logger.add(
        log_capture,
        level="DEBUG",
        format="{message}",
    )

    try:
        # Load dictionaries first
        dict_data = load_dictionaries(config, verbose=False)

        # Run typo generation (Stage 2)
        generate_typos(dict_data, config, verbose=False)

        # Get captured log text
        log_text = log_capture.getvalue()
        assert "[DEBUG TYPO:" in log_text and "[Stage 2]" in log_text, (
            f"Expected debug typo logging in Stage 2, but not found. "
            f"Captured messages:\n{log_text[:500]}"
        )
    finally:
        logger.remove(handler_id)


def _setup_iterative_solver_test(tmp_path):
    """Helper function to set up test files and config for iterative solver tests."""
    exclude_file = tmp_path / "exclude.txt"
    exclude_file.write_text("")

    include_file = tmp_path / "include.txt"
    include_file.write_text("the\n")

    config = Config(
        exclude=str(exclude_file),
        include=str(include_file),
        debug_words=["the"],
        debug_typos=["hte"],
        debug=True,
        verbose=True,
        top_n=10,
        jobs=1,
        platform="qmk",
        max_corrections=1000,
        max_iterations=2,
    )

    if config.debug_typos:
        config.debug_typo_matcher = DebugTypoMatcher.from_patterns(config.debug_typos)

    return config


@pytest.mark.slow
def test_debug_word_logging_appears_in_stage_3_candidate_selection(tmp_path):
    """Regression test: Verify debug word logging appears during Stage 3 (CandidateSelection)."""
    config = _setup_iterative_solver_test(tmp_path)
    setup_logger(verbose=True, debug=True)
    log_capture = io.StringIO()
    handler_id = logger.add(log_capture, level="DEBUG", format="{message}")

    try:
        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)
        platform = get_platform_backend(config.platform)
        run_stage_3_6_solver(
            typo_result, dict_data, platform, config, verbose=False, report_data=None
        )
        log_text = log_capture.getvalue()
        assert "[DEBUG WORD: 'the']" in log_text and "[Stage 3]" in log_text, (
            f"Expected debug word logging for 'the' in Stage 3, but not found. "
            f"Captured messages:\n{log_text[:1000]}"
        )
    finally:
        logger.remove(handler_id)


@pytest.mark.slow
def test_debug_typo_logging_appears_in_stage_3_candidate_selection(tmp_path):
    """Regression test: Verify debug typo logging appears during Stage 3 (CandidateSelection)."""
    config = _setup_iterative_solver_test(tmp_path)
    setup_logger(verbose=True, debug=True)
    log_capture = io.StringIO()
    handler_id = logger.add(log_capture, level="DEBUG", format="{message}")

    try:
        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)
        platform = get_platform_backend(config.platform)
        run_stage_3_6_solver(
            typo_result, dict_data, platform, config, verbose=False, report_data=None
        )
        log_text = log_capture.getvalue()
        assert "[DEBUG TYPO:" in log_text and "[Stage 3]" in log_text, (
            f"Expected debug typo logging in Stage 3, but not found. "
            f"Captured messages:\n{log_text[:1000]}"
        )
    finally:
        logger.remove(handler_id)


@pytest.mark.slow
def test_debug_word_logging_appears_in_stage_4_pattern_generalization(tmp_path):
    """Regression test: Verify debug word logging appears during Stage 4 (PatternGeneralization)."""
    config = _setup_iterative_solver_test(tmp_path)
    setup_logger(verbose=True, debug=True)
    log_capture = io.StringIO()
    handler_id = logger.add(log_capture, level="DEBUG", format="{message}")

    try:
        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)
        platform = get_platform_backend(config.platform)
        run_stage_3_6_solver(
            typo_result, dict_data, platform, config, verbose=False, report_data=None
        )
        log_text = log_capture.getvalue()
        assert "[DEBUG WORD: 'the']" in log_text and "[Stage 4]" in log_text, (
            f"Expected debug word logging for 'the' in Stage 4, but not found. "
            f"Captured messages:\n{log_text[:1000]}"
        )
    finally:
        logger.remove(handler_id)


@pytest.mark.slow
def test_debug_typo_logging_appears_in_stage_4_pattern_generalization(tmp_path):
    """Regression test: Verify debug typo logging appears during Stage 4 (PatternGeneralization)."""
    config = _setup_iterative_solver_test(tmp_path)
    setup_logger(verbose=True, debug=True)
    log_capture = io.StringIO()
    handler_id = logger.add(log_capture, level="DEBUG", format="{message}")

    try:
        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)
        platform = get_platform_backend(config.platform)
        run_stage_3_6_solver(
            typo_result, dict_data, platform, config, verbose=False, report_data=None
        )
        log_text = log_capture.getvalue()
        assert "[DEBUG TYPO:" in log_text and "[Stage 4]" in log_text, (
            f"Expected debug typo logging in Stage 4, but not found. "
            f"Captured messages:\n{log_text[:1000]}"
        )
    finally:
        logger.remove(handler_id)


@pytest.mark.slow
def test_debug_word_logging_appears_in_stage_5_conflict_removal(tmp_path):
    """Regression test: Verify debug word logging appears during Stage 5 (ConflictRemoval)."""
    config = _setup_iterative_solver_test(tmp_path)
    setup_logger(verbose=True, debug=True)
    log_capture = io.StringIO()
    handler_id = logger.add(log_capture, level="DEBUG", format="{message}")

    try:
        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)
        platform = get_platform_backend(config.platform)
        run_stage_3_6_solver(
            typo_result, dict_data, platform, config, verbose=False, report_data=None
        )
        log_text = log_capture.getvalue()
        assert "[DEBUG WORD: 'the']" in log_text and "[Stage 5]" in log_text, (
            f"Expected debug word logging for 'the' in Stage 5, but not found. "
            f"Captured messages:\n{log_text[:1000]}"
        )
    finally:
        logger.remove(handler_id)


@pytest.mark.slow
def test_debug_typo_logging_appears_in_stage_5_conflict_removal(tmp_path):
    """Regression test: Verify debug typo logging appears during Stage 5 (ConflictRemoval)."""
    config = _setup_iterative_solver_test(tmp_path)
    setup_logger(verbose=True, debug=True)
    log_capture = io.StringIO()
    handler_id = logger.add(log_capture, level="DEBUG", format="{message}")

    try:
        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)
        platform = get_platform_backend(config.platform)
        run_stage_3_6_solver(
            typo_result, dict_data, platform, config, verbose=False, report_data=None
        )
        log_text = log_capture.getvalue()
        assert "[DEBUG TYPO:" in log_text and "[Stage 5]" in log_text, (
            f"Expected debug typo logging in Stage 5, but not found. "
            f"Captured messages:\n{log_text[:1000]}"
        )
    finally:
        logger.remove(handler_id)


@pytest.mark.slow
def test_debug_word_logging_appears_in_stage_6_platform_constraints(tmp_path):
    """Regression test: Verify debug word logging appears during Stage 6 (PlatformConstraints)."""
    config = _setup_iterative_solver_test(tmp_path)
    setup_logger(verbose=True, debug=True)
    log_capture = io.StringIO()
    handler_id = logger.add(log_capture, level="DEBUG", format="{message}")

    try:
        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)
        platform = get_platform_backend(config.platform)
        run_stage_3_6_solver(
            typo_result, dict_data, platform, config, verbose=False, report_data=None
        )
        log_text = log_capture.getvalue()
        assert "[DEBUG WORD: 'the']" in log_text and "[Stage 6]" in log_text, (
            f"Expected debug word logging for 'the' in Stage 6, but not found. "
            f"Captured messages:\n{log_text[:1000]}"
        )
    finally:
        logger.remove(handler_id)


@pytest.mark.slow
def test_debug_typo_logging_appears_in_stage_6_platform_constraints(tmp_path):
    """Regression test: Verify debug typo logging appears during Stage 6 (PlatformConstraints)."""
    config = _setup_iterative_solver_test(tmp_path)
    setup_logger(verbose=True, debug=True)
    log_capture = io.StringIO()
    handler_id = logger.add(log_capture, level="DEBUG", format="{message}")

    try:
        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)
        platform = get_platform_backend(config.platform)
        run_stage_3_6_solver(
            typo_result, dict_data, platform, config, verbose=False, report_data=None
        )
        log_text = log_capture.getvalue()
        assert "[DEBUG TYPO:" in log_text and "[Stage 6]" in log_text, (
            f"Expected debug typo logging in Stage 6, but not found. "
            f"Captured messages:\n{log_text[:1000]}"
        )
    finally:
        logger.remove(handler_id)


@pytest.mark.slow
def test_debug_word_logging_appears_in_stage_7_platform_ranking(tmp_path):
    """Regression test: Verify debug word logging appears during Stage 7 (PlatformRanking)."""
    config = _setup_iterative_solver_test(tmp_path)
    setup_logger(verbose=True, debug=True)
    log_capture = io.StringIO()
    handler_id = logger.add(log_capture, level="DEBUG", format="{message}")

    try:
        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)
        platform = get_platform_backend(config.platform)
        solver_result, state = run_stage_3_6_solver(
            typo_result, dict_data, platform, config, verbose=False, report_data=None
        )
        constraints = platform.get_constraints()
        run_stage_7_ranking(
            solver_result,
            state,
            dict_data,
            platform,
            config,
            constraints,
            verbose=False,
            report_data=None,
        )
        log_text = log_capture.getvalue()
        assert "[DEBUG WORD:" in log_text and "[Stage 7]" in log_text, (
            f"Expected debug word logging in Stage 7, but not found. "
            f"Captured messages:\n{log_text[:1000]}"
        )
    finally:
        logger.remove(handler_id)


@pytest.mark.slow
def test_debug_typo_logging_appears_in_stage_7_platform_ranking(tmp_path):
    """Regression test: Verify debug typo logging appears during Stage 7 (PlatformRanking)."""
    config = _setup_iterative_solver_test(tmp_path)
    setup_logger(verbose=True, debug=True)
    log_capture = io.StringIO()
    handler_id = logger.add(log_capture, level="DEBUG", format="{message}")

    try:
        dict_data = load_dictionaries(config, verbose=False)
        typo_result = generate_typos(dict_data, config, verbose=False)
        platform = get_platform_backend(config.platform)
        solver_result, state = run_stage_3_6_solver(
            typo_result, dict_data, platform, config, verbose=False, report_data=None
        )
        constraints = platform.get_constraints()
        run_stage_7_ranking(
            solver_result,
            state,
            dict_data,
            platform,
            config,
            constraints,
            verbose=False,
            report_data=None,
        )
        log_text = log_capture.getvalue()
        assert "[DEBUG TYPO:" in log_text and "[Stage 7]" in log_text, (
            f"Expected debug typo logging in Stage 7, but not found. "
            f"Captured messages:\n{log_text[:1000]}"
        )
    finally:
        logger.remove(handler_id)
