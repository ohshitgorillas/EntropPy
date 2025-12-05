"""Helper functions for candidate selection."""

from entroppy.core import BoundaryType


def _get_boundary_order(natural_boundary: BoundaryType) -> list[BoundaryType]:
    """Get the order of boundaries to try, starting with the natural one.

    This implements self-healing: if a less strict boundary fails,
    we automatically try stricter ones in subsequent iterations.

    Args:
        natural_boundary: The naturally determined boundary

    Returns:
        List of boundaries to try in order
    """
    # Order: try natural first, then stricter alternatives
    if natural_boundary == BoundaryType.NONE:
        # NONE is least strict - try all others if it fails
        return [
            BoundaryType.NONE,
            BoundaryType.LEFT,
            BoundaryType.RIGHT,
            BoundaryType.BOTH,
        ]
    if natural_boundary == BoundaryType.LEFT:
        return [BoundaryType.LEFT, BoundaryType.BOTH]
    if natural_boundary == BoundaryType.RIGHT:
        return [BoundaryType.RIGHT, BoundaryType.BOTH]
    # BOTH is most strict - only try it
    return [BoundaryType.BOTH]
