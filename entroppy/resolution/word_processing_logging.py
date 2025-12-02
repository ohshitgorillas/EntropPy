"""Debug logging functions for word processing and typo generation."""

from typing import TYPE_CHECKING

from entroppy.core import BoundaryType
from entroppy.utils.debug import is_debug_word

if TYPE_CHECKING:
    from entroppy.utils.debug import DebugTypoMatcher


def add_debug_message(
    debug_messages: list[str],
    is_debug: bool,
    typo_debug_check: bool,
    word: str,
    typo: str,
    message_word: str,
    message_typo: str,
    debug_typo_matcher: "DebugTypoMatcher | None" = None,
) -> None:
    """Add debug messages for both word and typo debugging.

    Args:
        debug_messages: List to append messages to
        is_debug: Whether the word is being debugged
        typo_debug_check: Whether the typo is being debugged
        word: The word being processed
        typo: The typo being processed
        message_word: Message to add for word debugging
        message_typo: Message to add for typo debugging
        debug_typo_matcher: Optional matcher to get matched patterns for typo
    """
    if is_debug:
        debug_messages.append(f"[DEBUG WORD: '{word}'] [Stage 2] {message_word}")
    if typo_debug_check:
        # Get matched patterns if matcher is available
        if debug_typo_matcher:
            matched_patterns = debug_typo_matcher.get_matching_patterns(typo, BoundaryType.NONE)
            if matched_patterns:
                patterns_str = ", ".join(matched_patterns)
                debug_messages.append(
                    f"[DEBUG TYPO: '{typo}' (matched: {patterns_str})] [Stage 2] {message_typo}"
                )
            else:
                debug_messages.append(f"[DEBUG TYPO: '{typo}'] [Stage 2] {message_typo}")
        else:
            debug_messages.append(f"[DEBUG TYPO: '{typo}'] [Stage 2] {message_typo}")


def log_word_processing_start(
    debug_messages: list[str],
    word: str,
    debug_words: frozenset[str],
) -> None:
    """Log the start of word processing for debug words.

    Args:
        debug_messages: List to append messages to
        word: The word being processed
        debug_words: Set of words to debug
    """
    if is_debug_word(word, debug_words):
        debug_messages.append(f"[DEBUG WORD: '{word}'] [Stage 2] Generating typos for debug word")


def log_typo_generated(
    debug_messages: list[str],
    word: str,
    typo: str,
    debug_words: frozenset[str],
) -> None:
    """Log when a typo is generated for debug words.

    Args:
        debug_messages: List to append messages to
        word: The word being processed
        typo: The typo that was generated
        debug_words: Set of words to debug
    """
    if is_debug_word(word, debug_words):
        debug_messages.append(f"[DEBUG WORD: '{word}'] [Stage 2] Generated typo: {typo}")


def log_typo_pattern_match(
    debug_messages: list[str],
    typo: str,
    word: str,
    debug_typo_matcher: "DebugTypoMatcher | None",
) -> None:
    """Log when a typo matches a debug pattern.

    Args:
        debug_messages: List to append messages to
        typo: The typo that matched
        word: The source word
        debug_typo_matcher: Matcher for debug typos
    """
    if debug_typo_matcher:
        matched_patterns = debug_typo_matcher.get_matching_patterns(typo, BoundaryType.NONE)
        if matched_patterns:
            patterns_str = ", ".join(matched_patterns)
            debug_messages.append(
                f"[DEBUG TYPO: '{typo}' (matched: {patterns_str})] "
                f"[Stage 2] Generated from word: {word}"
            )


def log_typo_accepted(
    debug_messages: list[str],
    word: str,
    typo: str,
    debug_words: frozenset[str],
) -> None:
    """Log when a typo is accepted (added to corrections).

    Args:
        debug_messages: List to append messages to
        word: The word being processed
        typo: The typo that was accepted
        debug_words: Set of words to debug
    """
    if is_debug_word(word, debug_words):
        debug_messages.append(f"[DEBUG WORD: '{word}'] [Stage 2] Generated typo: {typo} → {word}")
