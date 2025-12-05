"""Boundary formatting functions."""

from entroppy.core.boundaries.types import BoundaryType


def format_boundary_name(boundary: BoundaryType) -> str:
    """Format boundary type as a name (e.g., 'NONE', 'LEFT', 'RIGHT', 'BOTH').

    Args:
        boundary: The boundary type to format

    Returns:
        Formatted boundary name
    """
    if boundary == BoundaryType.NONE:
        return "NONE"
    if boundary == BoundaryType.LEFT:
        return "LEFT"
    if boundary == BoundaryType.RIGHT:
        return "RIGHT"
    if boundary == BoundaryType.BOTH:
        return "BOTH"
    raise ValueError(f"Invalid boundary type: {boundary}")


def format_boundary_display(boundary: BoundaryType) -> str:
    """Format boundary type for display in reports (e.g., '(LEFT boundary)' or empty string).

    Args:
        boundary: The boundary type to format

    Returns:
        Formatted boundary display string, empty string for NONE
    """
    if boundary == BoundaryType.NONE:
        return ""
    if boundary == BoundaryType.LEFT:
        return "(LEFT boundary)"
    if boundary == BoundaryType.RIGHT:
        return "(RIGHT boundary)"
    if boundary == BoundaryType.BOTH:
        return "(BOTH boundaries)"
    raise ValueError(f"Invalid boundary type: {boundary}")
