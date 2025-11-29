"""Base classes and types for platform abstraction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from ..config import Correction, Config


class MatchDirection(Enum):
    """Direction in which platform scans for matches."""

    LEFT_TO_RIGHT = "ltr"  # Espanso
    RIGHT_TO_LEFT = "rtl"  # QMK


@dataclass
class PlatformConstraints:
    """Platform-specific constraints and capabilities."""

    # Limits
    max_corrections: int | None  # None = unlimited
    max_typo_length: int | None
    max_word_length: int | None

    # Character support
    allowed_chars: set[str] | None  # None = all characters allowed

    # Features
    supports_boundaries: bool
    supports_case_propagation: bool
    supports_regex: bool

    # Behavior
    match_direction: MatchDirection
    output_format: str  # "yaml", "c_array", "json", etc.


class PlatformBackend(ABC):
    """Abstract base class for platform-specific behavior."""

    @abstractmethod
    def get_constraints(self) -> PlatformConstraints:
        """Return platform-specific constraints and capabilities."""

    @abstractmethod
    def filter_corrections(
        self, corrections: list[Correction], config: Config
    ) -> tuple[list[Correction], dict]:
        """
        Apply platform-specific filtering.

        Args:
            corrections: List of corrections to filter
            config: Configuration object

        Returns:
            (filtered_corrections, metadata)
            metadata: dict with filtering statistics and removed items
        """

    @abstractmethod
    def rank_corrections(
        self,
        corrections: list[Correction],
        patterns: list[Correction],
        pattern_replacements: dict,
        user_words: set[str],
    ) -> list[Correction]:
        """
        Rank corrections by platform-specific usefulness.

        Args:
            corrections: All corrections (direct + patterns)
            patterns: Pattern corrections only
            pattern_replacements: Map of pattern -> list of corrections it replaces
            user_words: User-specified words (high priority)

        Returns:
            Ordered list of corrections (most to least useful)
        """

    @abstractmethod
    def generate_output(
        self, corrections: list[Correction], output_path: str | None, config: Config
    ) -> None:
        """
        Generate platform-specific output format.

        Args:
            corrections: Final list of corrections to output
            output_path: Output directory/file path (None = stdout)
            config: Configuration object
        """

    def get_name(self) -> str:
        """Return platform name for display."""
        return self.__class__.__name__.replace("Backend", "").lower()
