"""Espanso platform backend implementation."""

from .base import (
    PlatformBackend,
    PlatformConstraints,
    MatchDirection,
)
from ..config import Correction, Config
from ..output import generate_espanso_yaml


class EspansoBackend(PlatformBackend):
    """
    Backend for Espanso text expander.

    Characteristics:
    - Matches left-to-right
    - Unlimited corrections
    - Full Unicode support
    - Runtime conflict handling
    - YAML output format
    """

    def get_constraints(self) -> PlatformConstraints:
        """Return Espanso constraints (minimal - very permissive)."""
        return PlatformConstraints(
            max_corrections=None,  # Unlimited
            max_typo_length=None,  # No limit
            max_word_length=None,  # No limit
            allowed_chars=None,  # All characters allowed
            supports_boundaries=True,
            supports_case_propagation=True,
            supports_regex=True,
            match_direction=MatchDirection.LEFT_TO_RIGHT,
            output_format="yaml",
        )

    def filter_corrections(
        self, corrections: list[Correction], config: Config
    ) -> tuple[list[Correction], dict]:
        """
        Espanso filtering (minimal - accepts everything).

        Espanso has no character set restrictions or compile-time validation,
        so all corrections pass through.
        """
        metadata = {
            "total_input": len(corrections),
            "total_output": len(corrections),
            "filtered_count": 0,
            "filter_reasons": {},
        }

        return corrections, metadata

    def rank_corrections(
        self,
        corrections: list[Correction],
        patterns: list[Correction],
        pattern_replacements: dict,
        user_words: set[str],
    ) -> list[Correction]:
        """
        Espanso ranking (passthrough - no prioritization needed).

        Since Espanso has unlimited space, we don't need to rank or select.
        Just return corrections in their current order.
        """
        return corrections

    def generate_output(
        self, corrections: list[Correction], output_path: str | None, config: Config
    ) -> None:
        """
        Generate Espanso YAML output.

        Delegates to existing generate_espanso_yaml function.
        """
        generate_espanso_yaml(
            corrections,
            output_path,
            config.verbose,
            config.max_entries_per_file,
            config.jobs,
        )
