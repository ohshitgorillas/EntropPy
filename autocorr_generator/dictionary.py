"""Dictionary and word list loading."""

import itertools
import os
import re
import sys
from english_words import get_english_words_set
from wordfreq import top_n_list

from .config import Config


def load_validation_dictionary(
    exclude_filepath: str | None, verbose: bool = False
) -> set[str]:
    """Load english-words dictionary for validation.

    Removes words from the `exclude` file.
    Handles exact words and wildcard (*) patterns.
    """
    if verbose:
        print("Loading English words dictionary...", file=sys.stderr)

    words = get_english_words_set(["web2", "gcide"], lower=True)

    # Load exclusions from file
    exclusion_patterns = load_exclusions(exclude_filepath)  # No verbose here

    # Separate exact matches from wildcard patterns for efficiency
    # Note: We ignore "->" patterns as they apply to (typo, word) pairs, not single words.
    exact_matches = {p for p in exclusion_patterns if "*" not in p and "->" not in p}
    wildcard_patterns = {p for p in exclusion_patterns if "*" in p and "->" not in p}

    # First, remove exact matches using fast set difference
    validation_set = words - exact_matches
    removed_count = len(words) - len(validation_set)

    # Then, filter the remaining words with wildcard patterns
    if wildcard_patterns:
        compiled_patterns = [
            re.compile(f"^{re.escape(p).replace(r'\\*', '.*')}$")
            for p in wildcard_patterns
        ]
        words_to_remove = set()
        for word in validation_set:
            for pat in compiled_patterns:
                if pat.match(word):
                    words_to_remove.add(word)
                    break
        validation_set -= words_to_remove
        removed_count += len(words_to_remove)

    if verbose:
        print(f"Loaded {len(validation_set)} words for validation", file=sys.stderr)
        if removed_count > 0:
            print(
                f"Removed {removed_count} words based on the exclude file (including wildcards).",
                file=sys.stderr,
            )

    return validation_set


def load_word_list(filepath: str | None, verbose: bool = False) -> list[str]:
    """Load custom word list from file."""
    if not filepath:
        return []

    filepath = os.path.expanduser(filepath)
    words = []
    invalid_count = 0

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip().lower()
            if line and not line.startswith("#"):
                # Basic validation
                if any(c in line for c in ["\n", "\r", "\t", "\\"]):
                    invalid_count += 1
                    continue
                words.append(line)

    if verbose and invalid_count > 0:
        print(f"Skipped {invalid_count} words with invalid characters", file=sys.stderr)

    return words


def load_exclusions(filepath: str | None, verbose: bool = False) -> set[str]:
    """Load exclusion patterns from file."""
    if not filepath:
        return set()

    filepath = os.path.expanduser(filepath)
    exclusions = set()
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                exclusions.add(line)

    if verbose:
        print(f"Loaded {len(exclusions)} exclusion patterns", file=sys.stderr)

    return exclusions


def load_adjacent_letters(
    filepath: str | None, verbose: bool = False
) -> dict[str, str] | None:
    """Load keyboard adjacency map from file."""
    if not filepath:
        return None

    filepath = os.path.expanduser(filepath)
    adjacent_map = {}
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if " -> " in line:
                key, adjacents = line.split(" -> ", 1)
                adjacent_map[key.strip()] = adjacents.strip()

    if verbose:
        print(f"Loaded adjacency mapping for {len(adjacent_map)} keys", file=sys.stderr)

    return adjacent_map


def load_source_words(config: Config, verbose: bool = False) -> list[str]:
    """Get source words from wordfreq."""
    if not config.top_n:
        return []

    if verbose:
        print(f"Loading top {config.top_n} words from wordfreq...", file=sys.stderr)

    # Get words from wordfreq, fetch extra for filtering
    all_words = top_n_list("en", config.top_n * 3)

    # Filter words using a generator expression for efficiency
    max_len = config.max_word_length or float("inf")
    valid_words = (
        word.lower()
        for word in all_words
        if config.min_word_length <= len(word) <= max_len
        and not any(c in word for c in "\n\r\t\\")
    )

    # Take the top N valid words
    filtered = list(itertools.islice(valid_words, config.top_n))


    return filtered
