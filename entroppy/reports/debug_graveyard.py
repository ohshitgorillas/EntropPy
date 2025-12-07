"""Graveyard debug report generation."""

from datetime import datetime
from pathlib import Path
from typing import TextIO

from entroppy.core import format_boundary_display
from entroppy.reports.helpers import iterate_by_iteration_and_pass, write_report_header
from entroppy.resolution.state import DictionaryState
from entroppy.utils.helpers import write_file_safely


def generate_graveyard_debug_report(state: DictionaryState, report_dir: Path) -> None:
    """Generate comprehensive graveyard debug report.

    Args:
        state: Dictionary state with graveyard history
        report_dir: Directory to write report to
    """
    filepath = report_dir / "debug_graveyard.txt"

    def write_content(f: TextIO) -> None:
        write_report_header(f, "GRAVEYARD DEBUG REPORT")

        total_entries = len(state.graveyard_history)
        f.write(f"Total graveyard entries: {total_entries:,}\n\n")

        if not state.graveyard_history:
            f.write("No graveyard entries tracked.\n")
            return

        def write_entry(f: TextIO, entry) -> None:
            timestamp_str = datetime.fromtimestamp(entry.timestamp).strftime(
                "%Y-%m-%d %H:%M:%S.%f"
            )[:-3]
            boundary_str = format_boundary_display(entry.boundary)
            f.write(
                f'    typo: "{entry.typo}" → word: "{entry.word}" ' f"(boundary: {boundary_str})\n"
            )
            f.write(f"      Reason: {entry.reason.value}\n")
            if entry.blocker:
                f.write(f"      Blocker: {entry.blocker}\n")
            f.write(f"      Added at: {timestamp_str}\n")
            f.write("\n")

        iterate_by_iteration_and_pass(state.graveyard_history, f, write_entry)

    write_file_safely(filepath, write_content, "writing graveyard debug report")
