"""Platform substring conflict detection and resolution."""

from entroppy.resolution.platform_conflicts.detection import (
    build_length_buckets,
    check_bucket_conflicts,
    is_substring,
)
from entroppy.resolution.platform_conflicts.resolution import (
    BOUNDARY_PRIORITY,
    process_conflict_pair,
    should_remove_shorter,
)

__all__ = [
    "BOUNDARY_PRIORITY",
    "build_length_buckets",
    "check_bucket_conflicts",
    "is_substring",
    "process_conflict_pair",
    "should_remove_shorter",
]
