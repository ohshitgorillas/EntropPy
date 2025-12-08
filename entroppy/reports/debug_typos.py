"""Debug typo lifecycle report generation."""

from pathlib import Path
from typing import TYPE_CHECKING

from entroppy.core import BoundaryType
from entroppy.core.patterns.data_models import (
    IterationData,
    PlatformConflict,
    TypoLifecycle,
)
from entroppy.reports.debug_report_writers import (
    write_typo_report_from_lifecycle,
)
from entroppy.resolution.state import DebugTraceEntry
from entroppy.utils.debug import DebugTypoMatcher, is_debug_typo

if TYPE_CHECKING:
    from entroppy.resolution.state import DictionaryState


def _get_solver_events_for_typo(
    typo: str, debug_trace: list[DebugTraceEntry]
) -> list[DebugTraceEntry]:
    """Get solver events for a specific typo."""
    return [e for e in debug_trace if e.typo == typo]


def _add_extractions_to_iterations(
    typo: str,
    extractions: list,
    iterations_map: dict[int, IterationData],
) -> None:
    """Add pattern extractions to iterations map."""
    for extraction in extractions:
        if typo in extraction.typo_pattern or any(typo in occ[0] for occ in extraction.occurrences):
            iteration = extraction.iteration or 0
            if iteration not in iterations_map:
                iterations_map[iteration] = IterationData(iteration=iteration)
            iterations_map[iteration].pattern_extractions.append(extraction)


def _add_validations_to_iterations(
    typo: str,
    validations: list,
    iterations_map: dict[int, IterationData],
) -> None:
    """Add pattern validations to iterations map."""
    for validation in validations:
        if typo in validation.typo_pattern or (
            validation.occurrences and any(typo in occ[0] for occ in validation.occurrences)
        ):
            iteration = validation.iteration or 0
            if iteration not in iterations_map:
                iterations_map[iteration] = IterationData(iteration=iteration)
            iterations_map[iteration].pattern_validations.append(validation)


def _add_solver_events_to_iterations(
    solver_events: list[DebugTraceEntry],
    iterations_map: dict[int, IterationData],
) -> None:
    """Add solver events to iterations map."""
    for entry in solver_events:
        iteration = entry.iteration
        if iteration not in iterations_map:
            iterations_map[iteration] = IterationData(iteration=iteration)
        iterations_map[iteration].solver_events.append(entry)


def _add_platform_conflicts_to_iterations(
    typo: str,
    conflicts: list[PlatformConflict],
    iterations_map: dict[int, IterationData],
) -> None:
    """Add platform conflicts to iterations map."""
    for conflict in conflicts:
        if conflict.typo == typo:
            iteration = conflict.iteration or 0
            if iteration not in iterations_map:
                iterations_map[iteration] = IterationData(iteration=iteration)
            iterations_map[iteration].platform_conflicts.append(conflict)


def _build_typo_lifecycle_from_state(
    typo: str,
    state: "DictionaryState",
    debug_trace: list[DebugTraceEntry],
    debug_typo_matcher: DebugTypoMatcher | None = None,
) -> TypoLifecycle:
    """Build TypoLifecycle object from structured data in state.

    Args:
        typo: The typo to build lifecycle for
        state: Dictionary state with structured debug data
        debug_trace: Debug trace entries
        debug_typo_matcher: Optional matcher for debug typo patterns

    Returns:
        TypoLifecycle object with all events organized by iteration
    """
    lifecycle = TypoLifecycle(typo=typo)

    # Get solver events for this typo
    solver_events = _get_solver_events_for_typo(typo, debug_trace)

    # Get matched patterns
    if debug_typo_matcher and solver_events:
        boundary = solver_events[0].boundary
        if boundary is not None:
            lifecycle.matched_patterns = list(
                debug_typo_matcher.get_matching_patterns(typo, boundary)
            )

    # Get target word from solver events
    if solver_events:
        lifecycle.target_word = solver_events[0].word

    # Organize structured data by iteration
    iterations_map: dict[int, IterationData] = {}

    # Process pattern extractions
    _add_extractions_to_iterations(typo, state.pattern_extractions, iterations_map)

    # Process pattern validations
    _add_validations_to_iterations(typo, state.pattern_validations, iterations_map)

    # Add solver events to iterations
    _add_solver_events_to_iterations(solver_events, iterations_map)

    # Process platform conflicts
    _add_platform_conflicts_to_iterations(typo, state.platform_conflicts, iterations_map)

    lifecycle.iterations = iterations_map
    return lifecycle


def _collect_typos_from_state(
    state: "DictionaryState",
    debug_trace: list[DebugTraceEntry],
) -> set[str]:
    """Collect all typos from structured data in state."""
    all_typos: set[str] = set()

    # Extract typos from pattern extractions
    for extraction in state.pattern_extractions:
        all_typos.add(extraction.typo_pattern)
        for typo, _, _ in extraction.occurrences:
            all_typos.add(typo)

    # Extract typos from pattern validations
    for validation in state.pattern_validations:
        all_typos.add(validation.typo_pattern)
        if validation.occurrences:
            for typo, _ in validation.occurrences:
                all_typos.add(typo)

    # Extract typos from debug trace
    for entry in debug_trace:
        all_typos.add(entry.typo)

    return all_typos


def _filter_debug_typos(all_typos: set[str], debug_typo_matcher: DebugTypoMatcher) -> set[str]:
    """Filter typos to only those matching debug patterns."""
    filtered_typos = []
    for t in all_typos:
        # Check if typo matches any boundary type
        matches = False
        for boundary in BoundaryType:
            if is_debug_typo(t, boundary, debug_typo_matcher):
                matches = True
                break
        if matches:
            filtered_typos.append(t)
    return set(filtered_typos)


def _generate_reports_from_state(
    all_typos: set[str],
    state: "DictionaryState",
    debug_trace: list[DebugTraceEntry],
    debug_typo_matcher: DebugTypoMatcher | None,
    report_dir: Path,
) -> None:
    """Generate reports from structured data in state."""
    for typo in sorted(all_typos):
        lifecycle = _build_typo_lifecycle_from_state(typo, state, debug_trace, debug_typo_matcher)
        filepath = report_dir / f"debug_typo_{typo}.txt"
        write_typo_report_from_lifecycle(lifecycle, filepath)


def _generate_from_structured_data(
    state: "DictionaryState",
    debug_trace: list[DebugTraceEntry],
    debug_typo_matcher: DebugTypoMatcher | None,
    report_dir: Path,
) -> None:
    """Generate reports from structured data in state.

    Args:
        state: Dictionary state with structured debug data
        debug_trace: Debug trace entries from solver
        debug_typo_matcher: Optional matcher for debug typo patterns
        report_dir: Directory to write reports to
    """
    all_typos = _collect_typos_from_state(state, debug_trace)
    if debug_typo_matcher:
        all_typos = _filter_debug_typos(all_typos, debug_typo_matcher)
    _generate_reports_from_state(all_typos, state, debug_trace, debug_typo_matcher, report_dir)


def generate_debug_typos_report(
    debug_trace: list[DebugTraceEntry],
    report_dir: Path,
    debug_typo_matcher: DebugTypoMatcher | None = None,
    state: "DictionaryState | None" = None,
) -> None:
    """Generate debug typo lifecycle reports (one file per typo).

    Args:
        debug_messages: Stage 2 debug messages (unused, kept for API compatibility)
        debug_trace: Debug trace entries from solver
        report_dir: Directory to write reports to
        debug_typo_matcher: Optional matcher for debug typo patterns
        state: Dictionary state with structured debug data (required)
    """
    if not state:
        return  # Cannot generate reports without structured data

    _generate_from_structured_data(state, debug_trace, debug_typo_matcher, report_dir)
