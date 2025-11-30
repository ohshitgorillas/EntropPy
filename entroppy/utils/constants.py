"""Constants used throughout the EntropPy codebase."""


class Constants:
    """Centralized constants to avoid magic numbers and strings."""

    # File limits
    ESPANSO_MAX_ENTRIES_WARNING = 1000
    """Threshold for warning about too many entries per file in Espanso."""

    # Word frequency multiplier
    WORDFREQ_MULTIPLIER = 3
    """Multiplier for fetching extra words from wordfreq for filtering."""

    # String separators
    ADJACENT_MAP_SEPARATOR = " -> "
    """Separator used in adjacent letters map files (key -> value)."""

    EXCLUSION_SEPARATOR = "->"
    """Separator used in exclusion patterns (typo -> word)."""

    QMK_OUTPUT_SEPARATOR = " -> "
    """Separator used in QMK output format (typo -> word)."""

    # Boundary markers
    BOUNDARY_MARKER = ":"
    """Character used to mark word boundaries in patterns."""

    # QMK platform constants
    QMK_MAX_CORRECTIONS = 6000
    """Theoretical maximum number of corrections for QMK."""

    QMK_MAX_STRING_LENGTH = 62
    """Maximum string length for QMK corrections."""
