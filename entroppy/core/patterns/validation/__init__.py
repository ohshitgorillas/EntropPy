"""Pattern validation functionality."""

from entroppy.core.patterns.validation.batch_processor import (
    run_parallel_validation,
    run_single_threaded_validation,
)
from entroppy.core.patterns.validation.conflicts import (
    check_pattern_redundant_with_other_patterns,
    check_pattern_would_incorrectly_match_other_corrections,
)
from entroppy.core.patterns.validation.coordinator import (
    build_validation_indexes,
    extract_and_merge_patterns,
    extract_debug_typos,
)
from entroppy.core.patterns.validation.validator import (
    check_pattern_conflicts,
    validate_pattern_for_all_occurrences,
)
from entroppy.core.patterns.validation.worker import (
    PatternValidationContext,
    _validate_single_pattern_worker,
    init_pattern_validation_worker,
)

__all__ = [
    "build_validation_indexes",
    "check_pattern_conflicts",
    "check_pattern_redundant_with_other_patterns",
    "check_pattern_would_incorrectly_match_other_corrections",
    "extract_and_merge_patterns",
    "extract_debug_typos",
    "PatternValidationContext",
    "run_parallel_validation",
    "run_single_threaded_validation",
    "validate_pattern_for_all_occurrences",
    "_validate_single_pattern_worker",
    "init_pattern_validation_worker",
]
