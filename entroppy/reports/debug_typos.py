"""Debug typo lifecycle report generation."""

from pathlib import Path
import re
from typing import TextIO

from entroppy.reports.helpers import (
    write_report_header,
    write_solver_events,
    write_stage2_messages,
)
from entroppy.resolution.state import DebugTraceEntry
from entroppy.utils.helpers import write_file_safely


def _sanitize_filename(typo: str) -> str:
    """Sanitize typo for use in filename.

    Args:
        typo: The typo to sanitize

    Returns:
        Safe filename string
    """
    # Replace invalid filename characters with underscores
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", typo)
    # Replace wildcards and boundaries with safe characters
    sanitized = sanitized.replace("*", "_star_").replace(":", "_bound_")
    # Limit length to avoid filesystem issues
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    return sanitized


def _extract_typo_events(debug_messages: list[str]) -> dict[str, list[str]]:
    """Extract typo-specific events from debug messages.

    Args:
        debug_messages: Stage 2 debug messages

    Returns:
        Dictionary mapping typos to their debug messages
    """
    typo_events: dict[str, list[str]] = {}
    for message in debug_messages:
        if "[DEBUG TYPO:" in message:
            # Extract typo from message like "[DEBUG TYPO: 'typo'] [Stage 2] message"
            try:
                start = message.index("[DEBUG TYPO: '") + len("[DEBUG TYPO: '")
                end = message.index("']", start)
                typo = message[start:end]
                if typo not in typo_events:
                    typo_events[typo] = []
                typo_events[typo].append(message)
            except (ValueError, IndexError):
                continue
    return typo_events


def _extract_typo_solver_events(
    debug_trace: list[DebugTraceEntry], typo_events: dict[str, list[str]]
) -> dict[str, list[DebugTraceEntry]]:
    """Extract solver events for debug typos.

    Args:
        debug_trace: Debug trace entries from solver
        typo_events: Dictionary of typo events from Stage 2

    Returns:
        Dictionary mapping typos to their solver events
    """
    typo_solver_events: dict[str, list[DebugTraceEntry]] = {}
    for entry in debug_trace:
        if entry.typo in typo_events:
            if entry.typo not in typo_solver_events:
                typo_solver_events[entry.typo] = []
            typo_solver_events[entry.typo].append(entry)
    return typo_solver_events


def _write_typo_report(
    typo: str,
    matched_patterns: list[str],
    typo_events: list[str],
    typo_solver_events: list[DebugTraceEntry],
    filepath: Path,
) -> None:
    """Write a single typo lifecycle report.

    Args:
        typo: The typo being reported
        matched_patterns: List of matched patterns for this typo
        typo_events: Stage 2 events for this typo
        typo_solver_events: Solver events for this typo
        filepath: Path to write the report to
    """

    def write_content(f: TextIO) -> None:
        pattern_info = f" (matched: {', '.join(matched_patterns)})" if matched_patterns else ""
        write_report_header(f, f"DEBUG TYPO LIFECYCLE REPORT: {typo}{pattern_info}")

        f.write(f'Typo: "{typo}"\n')
        if matched_patterns:
            f.write(f"Matched patterns: {', '.join(matched_patterns)}\n")
        f.write("\n")

        # Stage 2 events
        if typo_events:
            f.write("Stage 2: Typo Generation\n")
            f.write("-" * 70 + "\n")
            write_stage2_messages(f, typo_events)

        # Solver events
        write_solver_events(f, typo_solver_events)

    write_file_safely(filepath, write_content, f"writing debug typo report for {typo}")


def generate_debug_typos_report(
    debug_messages: list[str],
    debug_trace: list[DebugTraceEntry],
    report_dir: Path,
) -> None:
    """Generate debug typo lifecycle reports (one file per typo).

    Args:
        debug_messages: Stage 2 debug messages
        debug_trace: Debug trace entries from solver
        report_dir: Directory to write reports to
    """
    # Extract typo-specific events from debug messages
    typo_events = _extract_typo_events(debug_messages)

    # Extract solver events for debug typos
    typo_solver_events = _extract_typo_solver_events(debug_trace, typo_events)

    # Get all unique typos
    all_typos = sorted(set(list(typo_events.keys()) + list(typo_solver_events.keys())))

    if not all_typos:
        return

    # Generate one report file per typo
    for typo in all_typos:
        # Try to find matched patterns from debug messages
        matched_patterns = []
        for message in typo_events.get(typo, []):
            if "matched:" in message.lower():
                # Extract pattern info if available
                try:
                    pattern_part = message.split("matched:", 1)[1].strip()
                    matched_patterns.append(pattern_part)
                except (ValueError, IndexError):
                    pass

        sanitized_typo = _sanitize_filename(typo)
        filepath = report_dir / f"debug_typo_{sanitized_typo}.txt"

        _write_typo_report(
            typo,
            matched_patterns,
            typo_events.get(typo, []),
            typo_solver_events.get(typo, []),
            filepath,
        )
