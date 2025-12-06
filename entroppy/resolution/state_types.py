"""Type definitions for DictionaryState.

This module contains dataclasses used by DictionaryState to avoid circular imports.
"""

from dataclasses import dataclass

from entroppy.core.boundaries import BoundaryType
from entroppy.resolution.history import RejectionReason


@dataclass
class GraveyardEntry:
    """A rejected correction with context."""

    typo: str
    word: str
    boundary: BoundaryType
    reason: RejectionReason
    blocker: str | None = None  # What blocked this (e.g., conflicting typo/word)
    iteration: int = 0


@dataclass
class DebugTraceEntry:
    """A log entry for debug tracing."""

    iteration: int
    pass_name: str
    action: str  # "added", "removed", "promoted_to_pattern", etc.
    typo: str
    word: str
    boundary: BoundaryType
    reason: str | None = None
