"""Collision and conflict resolution for EntropPy."""

from .collision import (
    process_word,
    resolve_collisions,
    choose_strictest_boundary,
    remove_substring_conflicts,
)
from .conflicts import (
    ConflictDetector,
    get_detector_for_boundary,
    resolve_conflicts_for_group,
)

__all__ = [
    "process_word",
    "resolve_collisions",
    "choose_strictest_boundary",
    "remove_substring_conflicts",
    "ConflictDetector",
    "get_detector_for_boundary",
    "resolve_conflicts_for_group",
]

