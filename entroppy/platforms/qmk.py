"""QMK platform backend implementation (skeleton)."""

from .base import (
    PlatformBackend,
    PlatformConstraints,
    MatchDirection,
)
from ..config import Correction, Config


class QMKBackend(PlatformBackend):
    """
    Backend for QMK firmware autocorrect.

    Characteristics:
    - Matches right-to-left
    - Limited corrections (~1500 typical)
    - Alphas + apostrophe only
    - Compile-time validation (rejects overlapping patterns)
    - C header output format

    Status: Not yet implemented
    """

    # QMK character constraints
    ALLOWED_CHARS = set("abcdefghijklmnopqrstuvwxyz'")

    def get_constraints(self) -> PlatformConstraints:
        """Return QMK constraints."""
        return PlatformConstraints(
            max_corrections=6000,  # Typical limit (user-configurable)
            max_typo_length=62,  # QMK string length limit
            max_word_length=62,
            allowed_chars=self.ALLOWED_CHARS,
            supports_boundaries=True,  # Via ':' notation
            supports_case_propagation=True,
            supports_regex=False,
            match_direction=MatchDirection.RIGHT_TO_LEFT,
            output_format="text",
        )

    def filter_corrections(
        self, corrections: list[Correction], config: Config
    ) -> tuple[list[Correction], dict]:
        """
        Apply QMK-specific filtering.

        Should implement:
        - Character set validation (only alphas + apostrophe)
        - Suffix conflict detection (RTL matching)
        - Boundary compatibility checks

        Not yet implemented.
        """
        raise NotImplementedError(
            "QMK filtering not yet implemented. "
            "Will include: character set validation, suffix conflict detection."
        )

    def rank_corrections(
        self,
        corrections: list[Correction],
        patterns: list[Correction],
        pattern_replacements: dict,
        user_words: set[str],
    ) -> list[Correction]:
        """
        Rank corrections by QMK-specific usefulness.

        Should implement 3-tier system:
        1. User words (infinite priority)
        2. Patterns (scored by usefulness)
        3. Direct corrections (scored by word frequency)

        Not yet implemented.
        """
        raise NotImplementedError(
            "QMK ranking not yet implemented. "
            "Will use 3-tier system: user words, patterns, direct corrections."
        )

    def generate_output(
        self, corrections: list[Correction], output_path: str | None, config: Config
    ) -> None:
        """
        Generate QMK text output.

        Should generate autocorrect.txt with text output:
        typo -> correct_word
        :typo -> correct_word
        typo: -> correct_word:
        :typo: -> correct_word:
        """
        with open(output_path, "w", encoding="utf-8") as f:
            for correction in corrections:
                f.write(f"{correction[0]} -> {correction[1]}\n")
