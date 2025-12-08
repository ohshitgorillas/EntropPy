"""Regression test for pattern generalization bug.

This test exposes the bug where patterns are extracted but then all rejected
because they're too short, resulting in NO patterns in the final QMK output.
"""

import pytest

from entroppy.core import Config
from entroppy.processing.stages import generate_typos, load_dictionaries
from entroppy.platforms import get_platform_backend
from entroppy.resolution.passes import (
    CandidateSelectionPass,
    ConflictRemovalPass,
    PatternGeneralizationPass,
    PlatformConstraintsPass,
    PlatformSubstringConflictPass,
)
from entroppy.resolution.solver import IterativeSolver, PassContext
from entroppy.resolution.state import DictionaryState


@pytest.mark.slow
def test_qmk_solver_contains_patterns(tmp_path):
    """Regression test: Solver should contain patterns, not just direct corrections.

    This test fails when patterns are extracted but then all rejected,
    leaving only direct corrections in the solver result.
    """
    exclude_file = tmp_path / "exclude.txt"
    exclude_file.write_text("")

    include_file = tmp_path / "include.txt"
    # Use words that will definitely generate patterns (common suffix pattern)
    # Words ending in 'ember' that create '*bet' -> '*ber' pattern
    include_file.write_text("december\nnovember\nremember\nseptember\n")

    config = Config(
        exclude=str(exclude_file),
        include=str(include_file),
        top_n=100,  # Use top N words to get enough words for pattern generalization
        adjacent_letters="settings/adjacent_qmk.txt",
        platform="qmk",
        max_corrections=100,
        jobs=1,
        max_iterations=10,
        verbose=False,  # Disable verbose for faster test execution
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

    # THE BUG: Patterns are extracted but then all rejected, resulting in 0 patterns
    # This test should FAIL when the bug exists (0 patterns)
    # and PASS when fixed (patterns exist)
    assert len(solver_result.patterns) > 0, (
        f"Expected patterns in solver result, but found 0 patterns. "
        f"Found {len(solver_result.corrections)} direct corrections instead. "
        f"This indicates patterns were extracted but then all rejected during validation."
    )
