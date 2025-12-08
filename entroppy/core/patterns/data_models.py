"""Structured data models for debug report generation."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PatternExtraction(BaseModel):
    """Structured data for pattern extraction events."""

    typo_pattern: str
    word_pattern: str
    boundary: str
    occurrence_count: int
    occurrences: list[tuple[str, str, str]] = Field(default_factory=list)
    iteration: int | None = None
    timestamp: str | None = None


class PatternValidation(BaseModel):
    """Structured data for pattern validation events."""

    typo_pattern: str
    word_pattern: str
    boundary: str
    status: str  # "ACCEPTED" | "REJECTED"
    reason: str | None = None
    occurrences: list[tuple[str, str]] | None = None
    replaces_count: int | None = None
    replaces: list[tuple[str, str]] | None = None
    iteration: int | None = None
    timestamp: str | None = None


class PlatformConflict(BaseModel):
    """Structured data for platform conflict checks."""

    typo: str
    word: str
    boundary: str
    conflict_type: str  # "boundary_comparison" | "false_trigger_check"
    details: str
    result: str  # "SAFE" | "UNSAFE" | comparison result
    iteration: int | None = None
    timestamp: str | None = None


class RankingInfo(BaseModel):
    """Structured data for ranking information."""

    typo: str
    word: str
    classification: str  # "Pattern" | "Direct Correction" | "User"
    tier: int
    score: float | None = None
    overall_position: int | None = None
    tier_position: int | None = None
    final_status: str | None = None  # "Made the cut" | "Cut off"
    limit: int | None = None
    timestamp: str | None = None


class IterationData(BaseModel):
    """Data for a single iteration."""

    iteration: int
    solver_events: list = Field(default_factory=list)  # DebugTraceEntry
    pattern_extractions: list[PatternExtraction] = Field(default_factory=list)
    pattern_validations: list[PatternValidation] = Field(default_factory=list)
    platform_conflicts: list[PlatformConflict] = Field(default_factory=list)
    other_messages: list[str] = Field(default_factory=list)


class FinalSummary(BaseModel):
    """Final summary information for a typo."""

    final_status: str
    final_pattern: str | None = None
    final_boundary: str | None = None
    total_iterations: int = 0
    final_rank: int | None = None
    corrections: list[tuple[str, str, str]] = Field(default_factory=list)
    patterns: list[tuple[str, str, str]] = Field(default_factory=list)


class TypoLifecycle(BaseModel):
    """Complete lifecycle data for a typo across all iterations."""

    typo: str
    matched_patterns: list[str] = Field(default_factory=list)
    target_word: str | None = None
    stage2_events: list[str] = Field(default_factory=list)
    iterations: dict[int, IterationData] = Field(default_factory=dict)
    stage7_events: list[RankingInfo] = Field(default_factory=list)
    final_summary: FinalSummary | None = None


class WordProcessingEvent(BaseModel):
    """Base model for Stage 2 word processing events."""

    word: str
    event_type: str  # "processing_start", "typo_generated", "typo_accepted"
    timestamp: str | None = None
    iteration: int = 0  # Stage 2 is iteration 0


class TypoGeneratedEvent(WordProcessingEvent):
    """Event when a typo is generated for a word."""

    typo: str
    matched_patterns: list[str] | None = None


class TypoAcceptedEvent(WordProcessingEvent):
    """Event when a typo is accepted (added to corrections)."""

    typo: str
    boundary: str
