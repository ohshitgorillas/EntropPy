"""QMK boundary formatting utilities."""

from entroppy.core import BoundaryType


def format_boundary_markers(typo: str, boundary: BoundaryType) -> str:
    """Format typo with QMK boundary markers (reverse of parse_boundary_markers).

    QMK uses colon notation for boundaries:
    - :typo: -> BOTH boundaries
    - :typo -> LEFT boundary
    - typo: -> RIGHT boundary
    - typo -> NONE

    Args:
        typo: The typo string
        boundary: The boundary type

    Returns:
        Typo string with QMK boundary markers
    """
    if boundary == BoundaryType.BOTH:
        return f":{typo}:"
    if boundary == BoundaryType.LEFT:
        return f":{typo}"
    if boundary == BoundaryType.RIGHT:
        return f"{typo}:"
    # NONE
    return typo
