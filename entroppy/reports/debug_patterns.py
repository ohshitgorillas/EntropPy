"""Patterns debug report generation."""

from pathlib import Path
from typing import TextIO

from entroppy.reports.helpers import (
    format_entry_header,
    iterate_by_iteration_and_pass,
    write_report_header,
)
from entroppy.resolution.state import DictionaryState
from entroppy.utils.helpers import write_file_safely


def generate_patterns_debug_report(state: DictionaryState, report_dir: Path) -> None:
    """Generate comprehensive patterns debug report.

    Args:
        state: Dictionary state with pattern history
        report_dir: Directory to write report to
    """
    filepath = report_dir / "debug_patterns.txt"

    def write_content(f: TextIO) -> None:
        write_report_header(f, "PATTERNS DEBUG REPORT")

        total_events = len(state.pattern_history)
        f.write(f"Total pattern events: {total_events:,}\n\n")

        if not state.pattern_history:
            f.write("No pattern events tracked.\n")
            return

        # Track which corrections were replaced by patterns
        pattern_replacements = state.pattern_replacements

        def write_entry(f: TextIO, entry) -> None:
            # pylint: disable=duplicate-code
            # Acceptable pattern: This is simple string formatting for report output.
            # The similar code in debug_corrections.py has different logic for handling
            # reasons. The base formatting similarity is inherent to the report structure,
            # and extracting would require complex conditionals that reduce clarity.
            timestamp_str, action_str, boundary_str = format_entry_header(entry)
            f.write(
                f'    {action_str}: "{entry.typo}" → "{entry.word}" '
                f"(boundary: {boundary_str})\n"
            )
            f.write(f"      {action_str.capitalize()} at: {timestamp_str}\n")

            if entry.action == "added":
                # Show which corrections were replaced
                pattern_key = (entry.typo, entry.word, entry.boundary)
                if pattern_key in pattern_replacements:
                    replacements = pattern_replacements[pattern_key]
                    f.write(f"      Replaces {len(replacements)} corrections:\n")
                    for typo, word, _ in replacements[:15]:  # Show first 15
                        f.write(f'        - "{typo}" → "{word}"\n')
                    if len(replacements) > 15:
                        f.write(f"        ... and {len(replacements) - 15} more\n")
            elif entry.reason:
                f.write(f"      Reason: {entry.reason}\n")

            f.write("\n")

        iterate_by_iteration_and_pass(state.pattern_history, f, write_entry)

    write_file_safely(filepath, write_content, "writing patterns debug report")
