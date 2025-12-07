"""Corrections debug report generation."""

from pathlib import Path
from typing import TextIO

from entroppy.reports.helpers import (
    format_entry_header,
    iterate_by_iteration_and_pass,
    write_report_header,
)
from entroppy.resolution.state import DictionaryState
from entroppy.utils.helpers import write_file_safely


def generate_corrections_debug_report(state: DictionaryState, report_dir: Path) -> None:
    """Generate comprehensive corrections debug report.

    Args:
        state: Dictionary state with correction history
        report_dir: Directory to write report to
    """
    filepath = report_dir / "debug_corrections.txt"

    def write_content(f: TextIO) -> None:
        write_report_header(f, "CORRECTIONS DEBUG REPORT")

        total_events = len(state.correction_history)
        f.write(f"Total correction events: {total_events:,}\n\n")

        if not state.correction_history:
            f.write("No correction events tracked.\n")
            return

        def write_entry(f: TextIO, entry) -> None:
            # pylint: disable=duplicate-code
            # Acceptable pattern: This is simple string formatting for report output.
            # The similar code in debug_patterns.py has additional logic for pattern
            # replacements, making extraction complex. The base formatting similarity is
            # inherent to the report structure, not actual logic duplication.
            timestamp_str, action_str, boundary_str = format_entry_header(entry)
            f.write(
                f'    {action_str}: "{entry.typo}" → "{entry.word}" '
                f"(boundary: {boundary_str})\n"
            )
            f.write(f"      {action_str.capitalize()} at: {timestamp_str}\n")
            if entry.reason:
                f.write(f"      Reason: {entry.reason}\n")
            f.write("\n")

        iterate_by_iteration_and_pass(state.correction_history, f, write_entry)

    write_file_safely(filepath, write_content, "writing corrections debug report")
