"""Typo generation algorithms."""


def generate_transpositions(word: str) -> list[str]:
    """Generate all possible adjacent character transpositions."""
    typos = []
    for i in range(len(word) - 1):
        typo = word[:i] + word[i + 1] + word[i] + word[i + 2 :]
        typos.append(typo)
    return typos


def generate_deletions(word: str) -> list[str]:
    """Generate single character deletions (only for words with 4+ characters)."""
    if len(word) < 4:
        return []

    typos = []
    for i in range(len(word)):
        typo = word[:i] + word[i + 1 :]
        typos.append(typo)
    return typos


def generate_extra_letters(word: str, extra_map: dict[str, str]) -> list[str]:
    """Generate typos by inserting extra letters."""
    if not extra_map:
        return []

    typos = []
    for i, char in enumerate(word):
        if char in extra_map:
            for extra in extra_map[char]:
                typos.append(word[: i + 1] + extra + word[i + 1 :])
                typos.append(word[:i] + extra + word[i:])

    return typos


def generate_replacements(word: str, extra_map: dict[str, str]) -> list[str]:
    """Generate typos by replacing characters with adjacent keys."""
    if not extra_map:
        return []

    typos = []
    for i, char in enumerate(word):
        if char in extra_map:
            for replacement in extra_map[char]:
                typos.append(word[:i] + replacement + word[i + 1 :])

    return typos


def generate_all_typos(
    word: str, extra_letters_map: dict[str, str] | None = None
) -> list[str]:
    """Generate all types of typos for a word."""
    typos = generate_transpositions(word) + generate_deletions(word)

    if extra_letters_map:
        typos.extend(generate_extra_letters(word, extra_letters_map))
        typos.extend(generate_replacements(word, extra_letters_map))

    return typos
