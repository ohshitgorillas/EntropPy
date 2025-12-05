"""Passes for the iterative solver."""

from entroppy.resolution.platform_conflicts.platform_pass import PlatformSubstringConflictPass

from .candidate_selection import CandidateSelectionPass
from .conflict_removal import ConflictRemovalPass
from .pattern_generalization import PatternGeneralizationPass
from .platform_constraints import PlatformConstraintsPass

__all__ = [
    "CandidateSelectionPass",
    "PatternGeneralizationPass",
    "ConflictRemovalPass",
    "PlatformConstraintsPass",
    "PlatformSubstringConflictPass",
]
