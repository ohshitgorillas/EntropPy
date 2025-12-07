"""Helper functions for report generation."""

from datetime import datetime
from typing import TYPE_CHECKING, Callable, Protocol, TextIO, Union

from entroppy.core import format_boundary_display

if TYPE_CHECKING:
    from entroppy.core.boundaries import BoundaryType
    from entroppy.resolution.history import (
        CorrectionHistoryEntry,
        GraveyardHistoryEntry,
        PatternHistoryEntry,
    )
    from entroppy.resolution.state_types import DebugTraceEntry


# Minimal protocol for entries that can be grouped by iteration and pass
class IterationPassEntry(Protocol):
    """Protocol for entries that have iteration, pass_name, and timestamp attributes.

    This protocol is used for various history entry types that share common structure.
    """

    iteration: int
    pass_name: str
    timestamp: float


# Protocol for entries that have action, typo, word, boundary for formatting
class FormattableEntry(Protocol):
    """Protocol for entries that can be formatted with action, typo, word, boundary."""

    action: str
    typo: str
    word: str
    boundary: "BoundaryType"
    timestamp: float


# Protocol for solver events that have all fields for solver lifecycle reporting
class SolverEventEntry(Protocol):
    """Protocol for solver event entries with all lifecycle fields.

    This protocol matches DebugTraceEntry and similar solver event types.
    """

    iteration: int
    pass_name: str
    action: str
    typo: str
    word: str
    boundary: "BoundaryType"
    reason: str | None


def write_solver_events(
    f: TextIO,
    solver_events: Union[list["DebugTraceEntry"], list[SolverEventEntry]],
) -> None:
    """Write solver lifecycle events to file.

    Args:
        f: File object to write to
        solver_events: List of solver event entries (DebugTraceEntry or compatible)
    """
    if solver_events:
        f.write("Solver Lifecycle:\n")
        f.write("-" * 70 + "\n")
        for entry in sorted(solver_events, key=lambda e: (e.iteration, e.pass_name)):
            boundary_str = format_boundary_display(entry.boundary)
            f.write(
                f"  Iter {entry.iteration} [{entry.pass_name}] {entry.action}: "
                f"{entry.typo} -> {entry.word} ({boundary_str})\n"
            )
            if entry.reason:
                f.write(f"    Reason: {entry.reason}\n")
        f.write("\n")
    else:
        f.write("Solver Lifecycle: No events tracked\n\n")


def format_time(seconds: float) -> str:
    """Format seconds into human-readable time."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, secs = divmod(seconds, 60)
    return f"{int(minutes)}m {secs:.1f}s"


def write_report_header(f: TextIO, title: str) -> None:
    """Write a standard report header with title and timestamp.

    Args:
        f: File object to write to
        title: Title of the report
    """
    f.write("=" * 80 + "\n")
    f.write(f"{title}\n")
    f.write("=" * 80 + "\n")
    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")


def write_section_header(f: TextIO, title: str) -> None:
    """Write a section header with separator line.

    Args:
        f: File object to write to
        title: Title of the section (empty string to write only separator)
    """
    if title:
        f.write(f"{title}\n")
    f.write("-" * 80 + "\n")


def format_entry_header(
    entry: FormattableEntry,
) -> tuple[str, str, str]:
    """Format the common header for a debug entry.

    Args:
        entry: Entry with typo, word, boundary, action, and timestamp attributes

    Returns:
        Tuple of (timestamp_str, action_str, boundary_str)
    """
    timestamp_str = datetime.fromtimestamp(entry.timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    action_str = entry.action.upper()
    boundary_str = format_boundary_display(entry.boundary)
    return timestamp_str, action_str, boundary_str


def write_stage2_messages(f: TextIO, messages: list[str]) -> None:
    """Write Stage 2 messages to file, extracting message parts if needed.

    Args:
        f: File object to write to
        messages: List of message strings, possibly with "[Stage 2]" markers
    """
    for message in messages:
        # Extract just the message part after the typo marker
        if "[Stage 2]" in message:
            msg_part = message.split("[Stage 2]", 1)[1].strip()
            f.write(f"  {msg_part}\n")
        else:
            f.write(f"  {message}\n")
    f.write("\n")


def iterate_by_iteration_and_pass(
    entries: Union[
        list["CorrectionHistoryEntry"],
        list["PatternHistoryEntry"],
        list["GraveyardHistoryEntry"],
    ],
    f: TextIO,
    write_entry: Callable[
        [TextIO, Union["CorrectionHistoryEntry", "PatternHistoryEntry", "GraveyardHistoryEntry"]],
        None,
    ],
) -> None:
    """Iterate over entries grouped by iteration and pass.

    This helper function handles the common pattern of grouping entries by iteration,
    then by pass within each iteration, and writing them in chronological order.

    Args:
        entries: List of entries with 'iteration' and 'pass_name' attributes
        f: File object to write to
        write_entry: Callback function to write each entry
    """
    # Group by iteration
    EntryType = Union["CorrectionHistoryEntry", "PatternHistoryEntry", "GraveyardHistoryEntry"]
    by_iteration: dict[int, list[EntryType]] = {}
    for entry in entries:
        if entry.iteration not in by_iteration:
            by_iteration[entry.iteration] = []
        by_iteration[entry.iteration].append(entry)

    # Sort iterations
    for iteration in sorted(by_iteration.keys()):
        f.write(f"--- Iteration {iteration} ---\n")
        iteration_entries = by_iteration[iteration]

        # Group by pass within iteration
        by_pass: dict[str, list[EntryType]] = {}
        for entry in iteration_entries:
            if entry.pass_name not in by_pass:
                by_pass[entry.pass_name] = []
            by_pass[entry.pass_name].append(entry)

        # Sort passes by timestamp (chronological order)
        # Sort items directly to avoid closure issues
        sorted_pass_items = sorted(
            by_pass.items(), key=lambda item: min(e.timestamp for e in item[1])
        )
        for pass_name, pass_entries_list in sorted_pass_items:
            f.write(f"  [{pass_name}]\n")
            pass_entries = sorted(pass_entries_list, key=lambda e: e.timestamp)

            for entry in pass_entries:
                write_entry(f, entry)

        f.write("\n")
