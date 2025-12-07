"""History tracking data models for debug reports."""

from enum import Enum

from pydantic import BaseModel

from entroppy.core import BoundaryType


class RejectionReason(Enum):
    """Reasons why a correction was rejected."""

    COLLISION_AMBIGUOUS = "ambiguous_collision"
    TOO_SHORT = "too_short"
    BLOCKED_BY_CONFLICT = "blocked_by_conflict"
    PLATFORM_CONSTRAINT = "platform_constraint"
    PATTERN_VALIDATION_FAILED = "pattern_validation_failed"
    EXCLUDED_BY_PATTERN = "excluded_by_pattern"
    FALSE_TRIGGER = "false_trigger"


class GraveyardHistoryEntry(BaseModel):
    """Complete history of a graveyard entry."""

    iteration: int
    pass_name: str
    typo: str
    word: str
    boundary: BoundaryType
    reason: RejectionReason
    blocker: str | None
    timestamp: float  # For ordering within same iteration/pass


class PatternHistoryEntry(BaseModel):
    """Complete history of pattern lifecycle."""

    # pylint: disable=duplicate-code
    # Acceptable pattern: These are Pydantic model field definitions representing the data model.
    # The similar field structure in CorrectionHistoryEntry and DebugTraceEntry is inherent
    # to the domain model (all track similar lifecycle events). This is structural similarity,
    # not logic duplication. Extracting would require complex inheritance hierarchies that
    # add complexity without benefit.
    iteration: int
    pass_name: str
    action: str  # "added", "removed"
    typo: str
    word: str
    boundary: BoundaryType
    reason: str | None = None  # For removals
    timestamp: float


class CorrectionHistoryEntry(BaseModel):
    """Complete history of correction lifecycle."""

    # pylint: disable=duplicate-code
    # Acceptable pattern: These are Pydantic model field definitions representing
    # the data model. The similar field structure in SolverEventEntry Protocol is
    # inherent to the domain model (both track similar lifecycle events). This is
    # structural similarity, not logic duplication.
    iteration: int
    pass_name: str
    action: str  # "added", "removed"
    typo: str
    word: str
    boundary: BoundaryType
    reason: str | None = None  # For removals
    timestamp: float
