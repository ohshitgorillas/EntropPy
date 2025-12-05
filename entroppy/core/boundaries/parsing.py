"""Boundary marker parsing."""

from entroppy.core.boundaries.types import BoundaryType
from entroppy.utils.constants import Constants


def parse_boundary_markers(pattern: str) -> tuple[str, BoundaryType | None]:
    """Parse boundary markers from a pattern string.

    Supports the following formats:
    - :pattern: -> (pattern, BoundaryType.BOTH)
    - :pattern -> (pattern, BoundaryType.LEFT)
    - pattern: -> (pattern, BoundaryType.RIGHT)
    - pattern -> (pattern, None)

    Args:
        pattern: The pattern string with optional boundary markers

    Returns:
        Tuple of (core_pattern, boundary_type)
    """
    if not pattern:
        return pattern, None

    starts_with_colon = pattern.startswith(Constants.BOUNDARY_MARKER)
    ends_with_colon = pattern.endswith(Constants.BOUNDARY_MARKER)

    # Determine boundary type
    if starts_with_colon and ends_with_colon:
        boundary_type = BoundaryType.BOTH
        core_pattern = pattern[1:-1]
    elif starts_with_colon:
        boundary_type = BoundaryType.LEFT
        core_pattern = pattern[1:]
    elif ends_with_colon:
        boundary_type = BoundaryType.RIGHT
        core_pattern = pattern[:-1]
    else:
        boundary_type = None
        core_pattern = pattern

    return core_pattern, boundary_type
