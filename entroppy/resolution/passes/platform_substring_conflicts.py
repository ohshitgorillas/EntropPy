"""Platform-specific cross-boundary substring conflict detection.

This pass detects substring conflicts that occur when the same typo text
appears with different boundaries, which can cause issues in platform output:

- QMK (RTL): Formatted strings like "aemr" and ":aemr" are substrings of
  each other, causing compiler errors
- Espanso (LTR): Same typo with different boundaries can cause runtime
  conflicts depending on matching order

This pass runs after ConflictRemovalPass to catch cross-boundary conflicts
that weren't detected within boundary groups.
"""

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from tqdm import tqdm

from entroppy.core.boundaries import BoundaryType
from entroppy.core.types import MatchDirection
from entroppy.platforms.qmk.formatting import format_boundary_markers
from entroppy.resolution.platform_substring_conflict_logging import log_platform_substring_conflict
from entroppy.resolution.solver import Pass
from entroppy.resolution.state import RejectionReason

if TYPE_CHECKING:
    from entroppy.resolution.solver import PassContext
    from entroppy.resolution.state import DictionaryState

# Boundary priority mapping: more restrictive boundaries have higher priority
# Used to determine which correction to keep when resolving conflicts
BOUNDARY_PRIORITY = {
    BoundaryType.NONE: 0,
    BoundaryType.LEFT: 1,
    BoundaryType.RIGHT: 1,
    BoundaryType.BOTH: 2,
}


class PlatformSubstringConflictPass(Pass):
    """Detects and removes cross-boundary substring conflicts.

    For platforms that format boundaries as part of the typo string (like QMK),
    this pass checks if formatted strings are substrings of each other and
    removes duplicates based on platform matching direction.

    For QMK (RTL):
    - Formats typos with boundary markers (e.g., "aemr" -> "aemr", ":aemr" -> ":aemr")
    - Checks if formatted strings are substrings
    - With RTL matching, the longer formatted string would match first
    - Removes the shorter one to prevent compiler errors

    For Espanso (LTR):
    - Checks if same typo text exists with different boundaries
    - With LTR matching, boundaries are handled separately in YAML
    - Still checks for substring relationships in the core typo text
    - Removes duplicates preferring less restrictive boundaries
    """

    @property
    def name(self) -> str:
        """Return the name of this pass."""
        return "PlatformSubstringConflicts"

    def run(self, state: "DictionaryState") -> None:
        """Run the platform substring conflict pass.

        Args:
            state: The dictionary state to modify
        """
        if not self.context.platform:
            # No platform specified, skip
            return

        # Get platform constraints
        constraints = self.context.platform.get_constraints()
        match_direction = constraints.match_direction

        # Combine active corrections and patterns
        all_corrections = list(state.active_corrections) + list(state.active_patterns)

        if not all_corrections:
            return

        # Build map of formatted typos to corrections
        # Format: formatted_typo -> list of (correction, core_typo, boundary)
        formatted_to_corrections: dict[str, list[tuple[tuple, str, object]]] = defaultdict(list)

        if self.context.verbose:
            corrections_iter: Any = tqdm(
                all_corrections,
                desc=f"    {self.name}",
                unit="correction",
                leave=False,
            )
        else:
            corrections_iter = all_corrections

        for correction in corrections_iter:
            typo, word, boundary = correction
            formatted_typo = self._format_typo_for_platform(typo, boundary)
            formatted_to_corrections[formatted_typo].append((correction, typo, boundary))

        # Find conflicts by checking if any formatted typo is a substring of another
        corrections_to_remove = []
        processed_pairs = set()

        # Sort formatted typos by length for efficient checking
        sorted_formatted = sorted(formatted_to_corrections.keys(), key=len)

        if self.context.verbose:
            formatted_iter: Any = tqdm(
                enumerate(sorted_formatted),
                desc=f"    {self.name} (checking conflicts)",
                total=len(sorted_formatted),
                unit="typo",
                leave=False,
            )
        else:
            formatted_iter = enumerate(sorted_formatted)

        for i, formatted1 in formatted_iter:
            for formatted2 in sorted_formatted[i + 1 :]:
                # Check if formatted1 is a substring of formatted2
                if self._is_substring(formatted1, formatted2):
                    # Check all combinations of corrections with these formatted strings
                    for correction1, _, boundary1 in formatted_to_corrections[formatted1]:
                        for correction2, _, boundary2 in formatted_to_corrections[formatted2]:
                            # Use frozenset to create unique pair identifier (order doesn't matter)
                            pair_id = frozenset([correction1, correction2])
                            if pair_id in processed_pairs:
                                continue
                            processed_pairs.add(pair_id)

                            # Determine which one to remove based on match direction
                            _, word1, _ = correction1
                            _, word2, _ = correction2

                            if self._should_remove_shorter(
                                match_direction,
                                word1,
                                word2,
                                boundary1,
                                boundary2,
                            ):
                                # Remove the shorter formatted one (formatted1)
                                corrections_to_remove.append(
                                    (
                                        correction1,
                                        f"Cross-boundary substring conflict: '{formatted1}' "
                                        f"is substring of '{formatted2}'",
                                    )
                                )
                            else:
                                # Remove the longer formatted one (formatted2)
                                corrections_to_remove.append(
                                    (
                                        correction2,
                                        f"Cross-boundary substring conflict: '{formatted2}' "
                                        f"contains substring '{formatted1}'",
                                    )
                                )

        # Remove conflicting corrections (deduplicate first)
        seen = set()
        for correction, reason in corrections_to_remove:
            if correction in seen:
                continue
            seen.add(correction)

            typo, word, boundary = correction

            # Find the conflicting correction for debug logging
            conflicting_correction = None
            formatted_removed = self._format_typo_for_platform(typo, boundary)
            formatted_conflicting = None

            # Find the conflicting correction by checking all corrections
            for other_correction in all_corrections:
                other_typo, _, other_boundary = other_correction
                other_formatted = self._format_typo_for_platform(other_typo, other_boundary)

                # Check if this is the conflicting correction
                if other_correction != correction and (
                    self._is_substring(formatted_removed, other_formatted)
                    or self._is_substring(other_formatted, formatted_removed)
                ):
                    conflicting_correction = other_correction
                    formatted_conflicting = other_formatted
                    break

            # Debug logging
            if conflicting_correction:
                log_platform_substring_conflict(
                    correction,
                    conflicting_correction,
                    formatted_removed,
                    formatted_conflicting or "",
                    reason,
                    state.debug_words,
                    state.debug_typo_matcher,
                )

            if correction in state.active_corrections:
                state.remove_correction(typo, word, boundary, self.name, reason)
            elif correction in state.active_patterns:
                state.remove_pattern(typo, word, boundary, self.name, reason)

            # pylint: disable=duplicate-code
            # Intentional duplication: Same graveyard pattern used in multiple passes
            # (platform_constraints.py, platform_substring_conflicts.py) to ensure
            # consistent rejection handling across all platform-specific passes.
            state.add_to_graveyard(
                typo,
                word,
                boundary,
                RejectionReason.PLATFORM_CONSTRAINT,
                reason,
            )

    def _format_typo_for_platform(self, typo: str, boundary) -> str:
        """Format typo with platform-specific boundary markers.

        For QMK, boundaries are part of the formatted string (colon notation).
        For Espanso, boundaries are separate YAML fields, but we still need to
        check for substring conflicts in the core typo text.

        Args:
            typo: The core typo string
            boundary: The boundary type

        Returns:
            Formatted typo string with boundary markers (for QMK) or core typo (for others)
        """
        # For QMK, use colon notation (boundaries are part of the string)
        if self.context.platform.__class__.__name__ == "QMKBackend":
            return format_boundary_markers(typo, boundary)

        # For Espanso and other platforms, boundaries are handled separately
        # in output format, so we just use the core typo for substring checking
        # The same core typo with different boundaries are different matches
        # but we still check if core typos are substrings of each other
        return typo

    def _is_substring(self, shorter: str, longer: str) -> bool:
        """Check if shorter is a substring of longer.

        Args:
            shorter: The shorter string
            longer: The longer string

        Returns:
            True if shorter is a substring of longer
        """
        return shorter in longer and shorter != longer

    def _should_remove_shorter(
        self,
        match_direction: MatchDirection,
        shorter_word: str,
        longer_word: str,
        shorter_boundary,
        longer_boundary,
    ) -> bool:
        """Determine if the shorter formatted typo should be removed.

        Args:
            match_direction: Platform match direction
            shorter_word: Word for shorter typo
            longer_word: Word for longer typo
            shorter_boundary: Boundary type for shorter typo
            longer_boundary: Boundary type for longer typo

        Returns:
            True if shorter should be removed, False if longer should be removed
        """
        # If they map to the same word, prefer the more restrictive boundary
        # (keeps the one that's less likely to cause false triggers)
        if shorter_word == longer_word:
            shorter_priority = BOUNDARY_PRIORITY.get(shorter_boundary, 0)
            longer_priority = BOUNDARY_PRIORITY.get(longer_boundary, 0)

            if longer_priority > shorter_priority:
                return True  # Remove shorter (less restrictive)
            return False  # Remove longer (less restrictive)

        # For RTL (QMK): QMK's compiler rejects ANY substring relationship
        # We prefer to keep the more restrictive boundary
        # (longer formatted usually means more restrictive)
        if match_direction == MatchDirection.RIGHT_TO_LEFT:
            # Keep longer (more restrictive), remove shorter
            return True  # Remove shorter

        # For LTR (Espanso): shorter would match first, so longer never triggers
        # But boundaries are handled separately in YAML, so this is less critical
        # Still, prefer more restrictive boundary
        shorter_priority = BOUNDARY_PRIORITY.get(shorter_boundary, 0)
        longer_priority = BOUNDARY_PRIORITY.get(longer_boundary, 0)

        if longer_priority > shorter_priority:
            return True  # Remove shorter (less restrictive)
        return False  # Remove longer (less restrictive)
