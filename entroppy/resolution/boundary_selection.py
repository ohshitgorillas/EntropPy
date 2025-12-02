"""Boundary selection logic for collision resolution."""

from entroppy.core import BoundaryType
from entroppy.core.boundaries import (
    BoundaryIndex,
    is_substring_of_any,
    would_trigger_at_end,
    would_trigger_at_start,
)

from entroppy.utils.debug import (
    DebugTypoMatcher,
    is_debug_typo,
    is_debug_word,
    log_debug_typo,
)


def _check_typo_in_target_word(
    typo: str,
    target_word: str | None,
) -> tuple[bool, bool, bool]:
    """Check if typo appears as prefix, suffix, or substring in target word.

    Args:
        typo: The typo string to check
        target_word: The target word to check against (None if not available)

    Returns:
        Tuple of (is_prefix, is_suffix, is_substring)
    """
    if target_word is None:
        return False, False, False

    # Check if typo is a prefix (excluding exact match)
    is_prefix = target_word.startswith(typo) and typo != target_word

    # Check if typo is a suffix (excluding exact match)
    is_suffix = target_word.endswith(typo) and typo != target_word

    # Check if typo is a substring (excluding exact match and prefix/suffix cases)
    is_substring = typo in target_word and typo != target_word and not is_prefix and not is_suffix

    return is_prefix, is_suffix, is_substring


def _get_example_words_with_prefix(
    typo: str, validation_index: BoundaryIndex, source_index: BoundaryIndex
) -> list[str]:
    """Get example words that have typo as a prefix.

    Args:
        typo: The typo string
        validation_index: Boundary index for validation set
        source_index: Boundary index for source words

    Returns:
        List of example words (up to 3 total, prioritizing validation words)
    """
    examples = []
    # Check validation index first
    if typo in validation_index.prefix_index:
        for word in validation_index.prefix_index[typo]:
            if word != typo and len(examples) < 3:
                examples.append(word)
    # Then check source index if we need more examples
    if len(examples) < 3 and typo in source_index.prefix_index:
        for word in source_index.prefix_index[typo]:
            if word != typo and word not in examples and len(examples) < 3:
                examples.append(word)
    return examples


def _get_example_words_with_suffix(
    typo: str, validation_index: BoundaryIndex, source_index: BoundaryIndex
) -> list[str]:
    """Get example words that have typo as a suffix.

    Args:
        typo: The typo string
        validation_index: Boundary index for validation set
        source_index: Boundary index for source words

    Returns:
        List of example words (up to 3 total, prioritizing validation words)
    """
    examples = []
    # Check validation index first
    if typo in validation_index.suffix_index:
        for word in validation_index.suffix_index[typo]:
            if word != typo and len(examples) < 3:
                examples.append(word)
    # Then check source index if we need more examples
    if len(examples) < 3 and typo in source_index.suffix_index:
        for word in source_index.suffix_index[typo]:
            if word != typo and word not in examples and len(examples) < 3:
                examples.append(word)
    return examples


def _get_example_words_with_substring(
    typo: str, validation_index: BoundaryIndex, source_index: BoundaryIndex
) -> list[str]:
    """Get example words that contain typo as a substring (not prefix/suffix).

    Args:
        typo: The typo string
        validation_index: Boundary index for validation set
        source_index: Boundary index for source words

    Returns:
        List of example words (up to 3 total, prioritizing validation words)
    """
    examples = []
    # Check validation index first
    for word in validation_index.word_set:
        if (
            typo in word
            and word != typo
            and not word.startswith(typo)
            and not word.endswith(typo)
            and len(examples) < 3
        ):
            examples.append(word)
    # Then check source index if we need more examples
    if len(examples) < 3:
        for word in source_index.word_set:
            if (
                typo in word
                and word != typo
                and not word.startswith(typo)
                and not word.endswith(typo)
                and word not in examples
                and len(examples) < 3
            ):
                examples.append(word)
    return examples


def _check_false_trigger_with_details(
    typo: str,
    boundary: BoundaryType,
    validation_index: BoundaryIndex,
    source_index: BoundaryIndex,
    target_word: str | None = None,
) -> tuple[bool, dict[str, bool]]:
    """Check if boundary would cause false triggers and return details.

    This helper function eliminates duplication between boundary_selection.py
    and correction_processing.py by centralizing the call pattern.

    Args:
        typo: The typo string
        boundary: The boundary type to check
        validation_index: Boundary index for validation set
        source_index: Boundary index for source words
        target_word: Optional target word to check against

    Returns:
        Tuple of (would_cause_false_trigger, details_dict)
    """
    return _would_cause_false_trigger(
        typo,
        boundary,
        validation_index,
        source_index,
        target_word=target_word,
        return_details=True,
    )


def _would_cause_false_trigger(
    typo: str,
    boundary: BoundaryType,
    validation_index: BoundaryIndex,
    source_index: BoundaryIndex,
    target_word: str | None = None,
    return_details: bool = False,
) -> bool | tuple[bool, dict[str, bool]]:
    """Check if a boundary would cause false triggers (garbage corrections).

    A false trigger occurs when the typo would match validation/source words incorrectly
    due to the boundary restrictions (or lack thereof).

    Args:
        typo: The typo string
        boundary: The boundary type to check
        validation_index: Boundary index for validation set
        source_index: Boundary index for source words
        target_word: Optional target word to check against (highest priority check)
        return_details: If True, return tuple of (bool, details_dict) instead of just bool

    Returns:
        If return_details is False: True if the boundary would cause false triggers, False otherwise
        If return_details is True: Tuple of (would_cause_false_trigger, details_dict) where
            details_dict contains breakdown of checks performed
    """
    # FIRST: Check target word (highest priority - most critical check)
    # This prevents predictive corrections where typo is prefix/suffix/substring of target
    would_trigger_start_target, would_trigger_end_target, is_substring_target = (
        _check_typo_in_target_word(typo, target_word)
    )

    # Check validation and source words
    would_trigger_start_val = would_trigger_at_start(typo, validation_index)
    would_trigger_end_val = would_trigger_at_end(typo, validation_index)
    is_substring_val = is_substring_of_any(typo, validation_index)

    would_trigger_start_src = would_trigger_at_start(typo, source_index)
    would_trigger_end_src = would_trigger_at_end(typo, source_index)
    is_substring_src = is_substring_of_any(typo, source_index)

    # Combine checks: target word check takes precedence
    would_trigger_start = (
        would_trigger_start_target or would_trigger_start_val or would_trigger_start_src
    )
    would_trigger_end = would_trigger_end_target or would_trigger_end_val or would_trigger_end_src
    is_substring = is_substring_target or is_substring_val or is_substring_src

    # Determine if boundary would cause false triggers
    # Logic: A boundary causes false triggers if it would allow the typo to match
    # validation/source words in positions where it appears.
    #
    # The inverse of determine_boundaries() logic:
    # - If typo appears as prefix only → need RIGHT (not NONE/LEFT)
    # - If typo appears as suffix only → need LEFT (not NONE/RIGHT)
    # - If typo appears in middle only → need BOTH (not NONE/LEFT/RIGHT)
    # - If typo appears as both prefix and suffix → need BOTH
    #
    # So a boundary causes false triggers if it would match where the typo appears:
    if boundary == BoundaryType.NONE:
        # NONE matches anywhere, so false trigger if typo appears anywhere
        would_cause = is_substring
        reason = "typo appears as substring" if is_substring else None
    elif boundary == BoundaryType.LEFT:
        # LEFT matches at word start, so false trigger if typo appears as prefix
        # (LEFT would match words starting with typo, which is incorrect)
        would_cause = (
            would_trigger_start
            or would_trigger_start_target
            or would_trigger_start_val
            or would_trigger_start_src
        )
        reason = "typo appears as prefix" if would_cause else None
    elif boundary == BoundaryType.RIGHT:
        # RIGHT matches at word end, so false trigger if typo appears as suffix
        # (RIGHT would match words ending with typo, which is incorrect)
        would_cause = (
            would_trigger_end
            or would_trigger_end_target
            or would_trigger_end_val
            or would_trigger_end_src
        )
        reason = "typo appears as suffix" if would_cause else None
    elif boundary == BoundaryType.BOTH:
        # BOTH matches as standalone word only, so it would NOT cause false triggers
        # for substrings (because BOTH only matches exact words, not words containing the typo)
        # BOTH is always safe for substring checks (it prevents all substring matches)
        would_cause = False
        reason = None
    else:
        # Unknown boundary type, be conservative
        would_cause = True
        reason = "unknown boundary type"

    if return_details:
        details = {
            "would_cause_false_trigger": would_cause,
            "reason": reason,
            "would_trigger_start": would_trigger_start,
            "would_trigger_end": would_trigger_end,
            "is_substring": is_substring,
            "would_trigger_start_target": would_trigger_start_target,
            "would_trigger_end_target": would_trigger_end_target,
            "is_substring_target": is_substring_target,
            "would_trigger_start_val": would_trigger_start_val,
            "would_trigger_end_val": would_trigger_end_val,
            "is_substring_val": is_substring_val,
            "would_trigger_start_src": would_trigger_start_src,
            "would_trigger_end_src": would_trigger_end_src,
            "is_substring_src": is_substring_src,
        }
        return would_cause, details

    return would_cause


def _should_debug_boundary_selection(
    typo: str,
    word: str | None,
    debug_words: set[str] | None,
    debug_typo_matcher: DebugTypoMatcher | None,
) -> bool:
    """Check if boundary selection should be debugged.

    Args:
        typo: The typo string
        word: Optional word associated with this typo
        debug_words: Set of words to debug (exact matches)
        debug_typo_matcher: Matcher for debug typos (with wildcards/boundaries)

    Returns:
        True if debugging should be enabled, False otherwise
    """
    if word:
        if is_debug_word(word, debug_words or set()):
            return True
    if debug_typo_matcher:
        # Check if typo matches any debug pattern (try with NONE boundary as placeholder)
        return is_debug_typo(typo, BoundaryType.NONE, debug_typo_matcher)
    return False


def _determine_boundary_order(
    typo: str, word: str | None
) -> tuple[list[BoundaryType], tuple[bool, bool, bool]]:
    """Determine the boundary order based on typo's relationship to target word.

    Args:
        typo: The typo string
        word: Optional target word to check relationship against

    Returns:
        Tuple of (boundary_order, relationship) where relationship is
        (is_prefix, is_suffix, is_middle)
    """
    # Check target word relationship first to determine appropriate boundary order
    target_is_prefix, target_is_suffix, target_is_middle = (
        _check_typo_in_target_word(typo, word) if word else (False, False, False)
    )

    # Build boundary order based on target word relationship
    if target_is_suffix:
        # Typo is suffix of target - skip LEFT (doesn't match relationship)
        # LEFT boundary means "match at word start", but typo appears at word end
        # Try: NONE, RIGHT, BOTH
        boundary_order = [BoundaryType.NONE, BoundaryType.RIGHT, BoundaryType.BOTH]
    elif target_is_prefix:
        # Typo is prefix of target - skip RIGHT (doesn't match relationship)
        # RIGHT boundary means "match at word end", but typo appears at word start
        # Try: NONE, LEFT, BOTH
        boundary_order = [BoundaryType.NONE, BoundaryType.LEFT, BoundaryType.BOTH]
    elif target_is_middle:
        # Typo is middle substring - skip LEFT and RIGHT (both incompatible)
        # Neither LEFT nor RIGHT make sense for middle substrings
        # Try: NONE, BOTH
        boundary_order = [BoundaryType.NONE, BoundaryType.BOTH]
    else:
        # Default order: no target word relationship detected
        # Try all boundaries: NONE, LEFT, RIGHT, BOTH
        boundary_order = [
            BoundaryType.NONE,
            BoundaryType.LEFT,
            BoundaryType.RIGHT,
            BoundaryType.BOTH,
        ]

    return boundary_order, (target_is_prefix, target_is_suffix, target_is_middle)


def _log_boundary_order_selection(
    typo: str,
    word: str | None,
    relationship: tuple[bool, bool, bool],
    debug_typo_matcher: DebugTypoMatcher | None,
) -> None:
    """Log the boundary order selection for debugging.

    Args:
        typo: The typo string
        word: Optional word associated with this typo
        relationship: Tuple of (is_prefix, is_suffix, is_middle)
        debug_typo_matcher: Matcher for debug typos (with wildcards/boundaries)
    """
    target_is_prefix, target_is_suffix, target_is_middle = relationship
    word_info = f" (word: {word})" if word else ""

    if target_is_suffix:
        message = (
            f"Boundary selection starting{word_info} - typo is SUFFIX of target, "
            f"skipping LEFT boundary"
        )
    elif target_is_prefix:
        message = (
            f"Boundary selection starting{word_info} - typo is PREFIX of target, "
            f"skipping RIGHT boundary"
        )
    elif target_is_middle:
        message = (
            f"Boundary selection starting{word_info} - typo is MIDDLE substring of target, "
            f"skipping LEFT and RIGHT boundaries"
        )
    else:
        message = f"Boundary selection starting{word_info}"

    log_debug_typo(
        typo,
        message,
        (
            debug_typo_matcher.get_matching_patterns(typo, BoundaryType.NONE)
            if debug_typo_matcher
            else None
        ),
        "Stage 3",
    )


def _format_incorrect_transformation(
    conflict_word: str, typo_str: str, word_str: str
) -> str:
    """Format how the correction would incorrectly apply.

    Args:
        conflict_word: The word that would be incorrectly transformed
        typo_str: The typo string
        word_str: The target word string

    Returns:
        Formatted string showing the incorrect transformation
    """
    if conflict_word.startswith(typo_str):
        # Prefix case
        replacement = conflict_word.replace(typo_str, word_str, 1)
        return (
            f'"{typo_str}" -> "{word_str}" in {conflict_word} -> '
            f"{replacement}  xx INCORRECT"
        )
    if conflict_word.endswith(typo_str):
        # Suffix case
        replacement = conflict_word.rsplit(typo_str, 1)[0] + word_str
        return (
            f'"{typo_str}" -> "{word_str}" in {conflict_word} -> '
            f"{replacement}  xx INCORRECT"
        )
    # Middle substring case
    replacement = conflict_word.replace(typo_str, word_str, 1)
    return (
        f'"{typo_str}" -> "{word_str}" in {conflict_word} -> '
        f"{replacement}  xx INCORRECT"
    )


def _log_boundary_rejection(
    typo: str,
    word: str | None,
    boundary: BoundaryType,
    details: dict[str, bool],
    validation_index: BoundaryIndex,
    source_index: BoundaryIndex,
    debug_typo_matcher: DebugTypoMatcher | None,
) -> None:
    """Log why a boundary was rejected with concrete examples.

    Args:
        typo: The typo string
        word: Optional word associated with this typo
        boundary: The boundary that was rejected
        details: Details dictionary from false trigger check
        validation_index: Boundary index for validation set
        source_index: Boundary index for source words
        debug_typo_matcher: Matcher for debug typos (with wildcards/boundaries)
    """
    word_info = f" (word: {word})" if word else ""
    example_lines = []

    # Get example words for each type of conflict
    # Priority: validation words > source words (exclude target word from examples)
    if boundary == BoundaryType.NONE:
        # NONE boundary would match anywhere, so show substring examples
        if details["is_substring"]:
            # Get examples from validation/source indexes
            examples = _get_example_words_with_substring(
                typo, validation_index, source_index
            )
            if not examples:
                # Fallback: check if it's a prefix or suffix
                if details["would_trigger_start"]:
                    examples = _get_example_words_with_prefix(
                        typo, validation_index, source_index
                    )
                elif details["would_trigger_end"]:
                    examples = _get_example_words_with_suffix(
                        typo, validation_index, source_index
                    )

            if examples:
                example_word = examples[0]
                example_lines.append(
                    f'"{typo}" -> "{word}" with NONE boundary would conflict '
                    f'with source word "{example_word}"'
                )
                example_lines.append(
                    _format_incorrect_transformation(example_word, typo, word or "")
                )
                example_lines.append("NONE BOUNDARY REJECTED")

    elif boundary == BoundaryType.LEFT:
        # LEFT boundary matches at word start, so show prefix examples
        if details["would_trigger_start"]:
            examples = _get_example_words_with_prefix(typo, validation_index, source_index)
            if examples:
                example_word = examples[0]
                example_lines.append(
                    f'"{typo}" -> "{word}" with LEFT boundary would conflict '
                    f'with source word "{example_word}"'
                )
                example_lines.append(
                    _format_incorrect_transformation(example_word, typo, word or "")
                )
                example_lines.append("LEFT BOUNDARY REJECTED")

    elif boundary == BoundaryType.RIGHT:
        # RIGHT boundary matches at word end, so show suffix examples
        if details["would_trigger_end"]:
            examples = _get_example_words_with_suffix(typo, validation_index, source_index)
            if examples:
                example_word = examples[0]
                example_lines.append(
                    f'"{typo}" -> "{word}" with RIGHT boundary would conflict '
                    f'with source word "{example_word}"'
                )
                example_lines.append(
                    _format_incorrect_transformation(example_word, typo, word or "")
                )
                example_lines.append("RIGHT BOUNDARY REJECTED")

    elif boundary == BoundaryType.BOTH:
        # BOTH boundary is always safe (prevents all substring matches)
        # This shouldn't be rejected, but if it is, log it
        example_lines.append(
            "BOTH boundary requires standalone word, prevents all substring matches"
        )

    # Format the message
    if example_lines:
        message = "\n".join(example_lines)
    else:
        # Fallback if no examples found
        reason_parts = []
        if details["would_trigger_start"]:
            reason_parts.append("appears as prefix")
        if details["would_trigger_end"]:
            reason_parts.append("appears as suffix")
        if details["is_substring"] and not (
            details["would_trigger_start"] or details["would_trigger_end"]
        ):
            reason_parts.append("appears as substring")
        reason_str = ", ".join(reason_parts) if reason_parts else "unknown reason"
        message = (
            f"Rejected boundary '{boundary.value}'{word_info} - "
            f"would cause false triggers: {reason_str}"
        )

    log_debug_typo(
        typo,
        message,
        (
            debug_typo_matcher.get_matching_patterns(typo, boundary)
            if debug_typo_matcher
            else None
        ),
        "Stage 3",
    )


def _log_fallback_boundary(
    typo: str,
    word: str | None,
    debug_typo_matcher: DebugTypoMatcher | None,
) -> None:
    """Log when falling back to BOTH boundary.

    Args:
        typo: The typo string
        word: Optional word associated with this typo
        debug_typo_matcher: Matcher for debug typos (with wildcards/boundaries)
    """
    word_info = f" (word: {word})" if word else ""
    log_debug_typo(
        typo,
        f"All boundaries would cause false triggers, using fallback "
        f"'{BoundaryType.BOTH.value}'{word_info}",
        (
            debug_typo_matcher.get_matching_patterns(typo, BoundaryType.BOTH)
            if debug_typo_matcher
            else None
        ),
        "Stage 3",
    )


def choose_boundary_for_typo(
    typo: str,
    validation_index: BoundaryIndex,
    source_index: BoundaryIndex,
    debug_words: set[str] | None = None,
    debug_typo_matcher: DebugTypoMatcher | None = None,
    word: str | None = None,
) -> BoundaryType:
    """Choose the least restrictive boundary that doesn't produce garbage corrections.

    Tries boundaries from least restrictive to most restrictive, but adjusts the order
    based on the typo's relationship to the target word:
    - If typo is a suffix of target word → skip LEFT (incompatible)
    - If typo is a prefix of target word → skip RIGHT (incompatible)
    - If typo is a middle substring → skip LEFT and RIGHT (both incompatible)
    - Otherwise → try all boundaries in default order

    Args:
        typo: The typo string
        validation_index: Boundary index for validation set
        source_index: Boundary index for source words
        debug_words: Set of words to debug (exact matches)
        debug_typo_matcher: Matcher for debug typos (with wildcards/boundaries)
        word: Optional word associated with this typo (for debug logging)

    Returns:
        The chosen boundary type (least restrictive that doesn't cause false triggers)
    """
    # Check if we should debug this boundary selection
    is_debug = _should_debug_boundary_selection(
        typo, word, debug_words, debug_typo_matcher
    )

    # Determine boundary order based on target word relationship
    boundary_order, relationship = _determine_boundary_order(typo, word)

    # Log boundary order selection if debugging
    if is_debug:
        _log_boundary_order_selection(typo, word, relationship, debug_typo_matcher)

    # Check each boundary from least to most restrictive
    for boundary in boundary_order:
        would_cause, details = _check_false_trigger_with_details(
            typo,
            boundary,
            validation_index,
            source_index,
            target_word=word,
        )
        if not would_cause:
            # Boundary selected - logging will be done by log_boundary_selection_details
            # which is called from collision.py after processing
            return boundary

        # Log why this boundary was rejected with concrete examples
        if is_debug:
            _log_boundary_rejection(
                typo,
                word,
                boundary,
                details,
                validation_index,
                source_index,
                debug_typo_matcher,
            )

    # If all boundaries would cause false triggers, return BOTH as safest fallback
    # (most restrictive, least likely to cause issues)
    if is_debug:
        _log_fallback_boundary(typo, word, debug_typo_matcher)
    return BoundaryType.BOTH


def log_boundary_selection_details(
    typo: str,
    word: str | None,
    boundary: BoundaryType,
    details: dict,
    debug_typo_matcher: DebugTypoMatcher | None,
) -> None:
    """Log boundary selection details for debug typos."""
    if not debug_typo_matcher or not is_debug_typo(typo, boundary, debug_typo_matcher):
        return

    word_info = f" (word: {word})" if word else ""
    safety_details = []

    if (
        not details["would_trigger_start"]
        and not details["would_trigger_end"]
        and not details["is_substring"]
    ):
        safety_details.append("typo doesn't appear in validation or source words")
    else:
        if boundary == BoundaryType.NONE:
            safety_details.append(
                "NONE boundary would match anywhere, but typo doesn't appear as substring"
            )
        elif boundary == BoundaryType.LEFT:
            safety_details.append(
                "LEFT boundary requires word start, typo doesn't appear as prefix"
            )
        elif boundary == BoundaryType.RIGHT:
            safety_details.append("RIGHT boundary requires word end, typo doesn't appear as suffix")
        elif boundary == BoundaryType.BOTH:
            safety_details.append(
                "BOTH boundary requires standalone word, prevents all substring matches"
            )

    check_parts = []
    if not details["would_trigger_start"]:
        check_parts.append("not a prefix")
    if not details["would_trigger_end"]:
        check_parts.append("not a suffix")
    if not details["is_substring"]:
        check_parts.append("not a substring")
    if check_parts:
        safety_details.append(f"checks passed: {', '.join(check_parts)}")

    log_debug_typo(
        typo,
        f"Selected boundary '{boundary.value}'{word_info} - {'; '.join(safety_details)}",
        debug_typo_matcher.get_matching_patterns(typo, boundary),
        "Stage 3",
    )
