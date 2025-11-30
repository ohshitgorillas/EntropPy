"""Type definitions for EntropPy."""

from entroppy.core.boundaries import BoundaryType

# Type alias for corrections: (typo, correct_word, boundary_type)
Correction = tuple[str, str, BoundaryType]
