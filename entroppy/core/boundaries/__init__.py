"""Boundary detection and formatting for typo corrections."""

from entroppy.core.boundaries.detection import (
    batch_determine_boundaries,
    determine_boundaries,
    is_substring_of_any,
    would_trigger_at_end,
    would_trigger_at_start,
)
from entroppy.core.boundaries.formatting import format_boundary_display, format_boundary_name
from entroppy.core.boundaries.parsing import parse_boundary_markers
from entroppy.core.boundaries.types import BoundaryIndex, BoundaryType

__all__ = [
    "BoundaryIndex",
    "BoundaryType",
    "batch_determine_boundaries",
    "determine_boundaries",
    "format_boundary_display",
    "format_boundary_name",
    "is_substring_of_any",
    "parse_boundary_markers",
    "would_trigger_at_end",
    "would_trigger_at_start",
]
