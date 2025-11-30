"""QMK output generation logic."""

import os
import sys

from loguru import logger

from entroppy.core import BoundaryType, Config, Correction
from entroppy.platforms.qmk.formatting import format_boundary_markers


def format_correction_line(typo: str, word: str, boundary: BoundaryType) -> str:
    """Format a single correction line with QMK boundary markers."""
    formatted_typo = format_boundary_markers(typo, boundary)
    return f"{formatted_typo} -> {word}"


def sort_corrections(lines: list[str]) -> list[str]:
    """Sort correction lines alphabetically by correction word."""
    return sorted(lines, key=lambda line: line.split(" -> ")[1])


def determine_output_path(output_path: str | None) -> str | None:
    """Determine final output file path."""
    if not output_path:
        return None

    if os.path.isdir(output_path) or not output_path.endswith(".txt"):
        return os.path.join(output_path, "autocorrect.txt")
    return output_path


def generate_output(corrections: list[Correction], output_path: str | None, config: Config) -> None:
    """
    Generate QMK text output.

    Format:
    typo -> correction
    :typo -> correction
    typo: -> correction
    :typo: -> correction

    Sorted alphabetically by correction word.
    """
    lines = [format_correction_line(typo, word, boundary) for typo, word, boundary in corrections]

    lines = sort_corrections(lines)

    output_file = determine_output_path(output_path)

    if output_file:
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")

        if config.verbose:
            logger.info(f"\nWrote {len(lines)} corrections to {output_file}")
    else:
        for line in lines:
            print(line, file=sys.stdout)
