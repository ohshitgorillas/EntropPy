"""Data collection helpers for pattern processing.

This module provides functions to create structured debug data objects
for pattern extraction and validation, separate from logging concerns.
"""

from typing import TYPE_CHECKING

from entroppy.core.boundaries import BoundaryType
from entroppy.core.patterns.data_models import (
    PatternExtraction,
    PatternValidation,
    TypoAcceptedEvent,
    TypoGeneratedEvent,
    WordProcessingEvent,
)
from entroppy.core.types import Correction

if TYPE_CHECKING:
    from entroppy.resolution.state import DictionaryState


def record_pattern_extraction(
    typo_pattern: str,
    word_pattern: str,
    boundary: BoundaryType,
    unique_matches: list[tuple[str, str, BoundaryType]],
    state: "DictionaryState | None" = None,
) -> None:
    """Record a pattern extraction event in structured format.

    Args:
        typo_pattern: The extracted typo pattern
        word_pattern: The extracted word pattern
        boundary: The boundary type
        unique_matches: List of (typo, word, original_boundary) matches
        state: Optional dictionary state for storing structured debug data
    """
    if state is None:
        return

    occurrences = [
        (typo, word, orig_boundary.value) for typo, word, orig_boundary in unique_matches
    ]
    extraction = PatternExtraction(
        typo_pattern=typo_pattern,
        word_pattern=word_pattern,
        boundary=boundary.value,
        occurrence_count=len(unique_matches),
        occurrences=occurrences,
        iteration=state.current_iteration,
    )
    state.pattern_extractions.append(extraction)


def record_pattern_validation_accepted(
    typo_pattern: str,
    word_pattern: str,
    boundary: BoundaryType,
    occurrences: list[tuple[str, str, BoundaryType]],
    state: "DictionaryState | None" = None,
) -> None:
    """Record an accepted pattern validation event in structured format.

    Args:
        typo_pattern: The accepted typo pattern
        word_pattern: The accepted word pattern
        boundary: The boundary type
        occurrences: List of corrections this pattern replaces
        state: Optional dictionary state for storing structured debug data
    """
    if state is None:
        return

    replaces = [(typo, word) for typo, word, _ in occurrences]
    validation = PatternValidation(
        typo_pattern=typo_pattern,
        word_pattern=word_pattern,
        boundary=boundary.value,
        status="ACCEPTED",
        replaces_count=len(occurrences),
        replaces=replaces,
        iteration=state.current_iteration,
    )
    state.pattern_validations.append(validation)


def record_pattern_validation_rejected(
    typo_pattern: str,
    word_pattern: str,
    boundary: BoundaryType,
    reason: str,
    occurrences: list[Correction],
    state: "DictionaryState | None" = None,
) -> None:
    """Record a rejected pattern validation event in structured format.

    Args:
        typo_pattern: The rejected typo pattern
        word_pattern: The rejected word pattern
        boundary: The boundary type
        reason: Reason for rejection
        occurrences: List of occurrences for this pattern
        state: Optional dictionary state for storing structured debug data
    """
    if state is None:
        return

    occ_list = [(typo, word) for typo, word, _ in occurrences]
    validation = PatternValidation(
        typo_pattern=typo_pattern,
        word_pattern=word_pattern,
        boundary=boundary.value,
        status="REJECTED",
        reason=reason,
        occurrences=occ_list if occ_list else None,
        iteration=state.current_iteration,
    )
    state.pattern_validations.append(validation)


def record_word_processing_start(
    word: str,
    state: "DictionaryState | None" = None,
) -> None:
    """Record a word processing start event in structured format.

    Args:
        word: The word being processed
        state: Optional dictionary state for storing structured debug data
    """
    if state is None:
        return

    event = WordProcessingEvent(
        word=word,
        event_type="processing_start",
        iteration=0,
    )
    state.stage2_word_events.append(event)


def record_typo_generated(
    word: str,
    typo: str,
    matched_patterns: list[str] | None,
    state: "DictionaryState | None" = None,
) -> None:
    """Record a typo generated event in structured format.

    Args:
        word: The word being processed
        typo: The typo that was generated
        matched_patterns: Optional list of matched debug typo patterns
        state: Optional dictionary state for storing structured debug data
    """
    if state is None:
        return

    event = TypoGeneratedEvent(
        word=word,
        event_type="typo_generated",
        typo=typo,
        matched_patterns=matched_patterns,
        iteration=0,
    )
    state.stage2_word_events.append(event)


def record_typo_accepted(
    word: str,
    typo: str,
    boundary: BoundaryType,
    state: "DictionaryState | None" = None,
) -> None:
    """Record a typo accepted event in structured format.

    Args:
        word: The word being processed
        typo: The typo that was accepted
        boundary: The boundary type
        state: Optional dictionary state for storing structured debug data
    """
    if state is None:
        return

    event = TypoAcceptedEvent(
        word=word,
        event_type="typo_accepted",
        typo=typo,
        boundary=boundary.value,
        iteration=0,
    )
    state.stage2_word_events.append(event)
