"""YAML output generation and RAM estimation."""

import os
import sys
from collections import defaultdict

import yaml

from .config import BoundaryType, Correction


def correction_to_yaml_dict(correction: Correction) -> dict:
    """Convert (typo, word, boundary_type) to Espanso match dict."""
    typo, word, boundary = correction

    match_dict = {"trigger": typo, "replace": word, "propagate_case": True}

    if boundary == BoundaryType.BOTH:
        match_dict["word"] = True
    elif boundary == BoundaryType.LEFT:
        match_dict["left_word"] = True
    elif boundary == BoundaryType.RIGHT:
        match_dict["right_word"] = True

    return match_dict


def organize_by_letter(corrections: list[Correction]) -> dict[str, list[dict]]:
    """Group corrections by first letter of correct word."""
    by_letter = defaultdict(list)

    for correction in corrections:
        _, word, _ = correction

        first_char = word[0].lower() if word else ""

        if first_char.isalpha():
            file_key = first_char
        else:
            file_key = "symbols"

        yaml_dict = correction_to_yaml_dict(correction)
        by_letter[file_key].append(yaml_dict)

    return by_letter


def estimate_ram_usage(
    corrections: list[Correction], verbose: bool = False
) -> dict[str, float]:
    """
    Estimate RAM usage of generated corrections.

    Returns dict with:
        - per_entry_bytes: Average bytes per correction
        - total_kb: Total estimated KB
        - total_mb: Total estimated MB
    """
    # Estimate bytes per correction entry
    # Based on YAML structure:
    # - trigger: ~10 chars = 10 bytes
    # - replace: ~10 chars = 10 bytes
    # - propagate_case: true = 20 bytes
    # - word/left_word/right_word = 15 bytes
    # - YAML overhead (spaces, newlines) = 25 bytes
    # Total: ~80 bytes per entry on average

    avg_trigger_len = (
        sum(len(c[0]) for c in corrections) / len(corrections) if corrections else 0
    )
    avg_replace_len = (
        sum(len(c[1]) for c in corrections) / len(corrections) if corrections else 0
    )

    # Actual calculation
    per_entry_bytes = (
        avg_trigger_len  # trigger string
        + avg_replace_len  # replace string
        + 20  # "propagate_case: true"
        + 15  # boundary property if present
        + 25  # YAML formatting overhead
    )

    total_bytes = per_entry_bytes * len(corrections)
    total_kb = total_bytes / 1024
    total_mb = total_kb / 1024

    estimate = {
        "entries": len(corrections),
        "avg_trigger_len": round(avg_trigger_len, 1),
        "avg_replace_len": round(avg_replace_len, 1),
        "per_entry_bytes": round(per_entry_bytes, 1),
        "total_bytes": round(total_bytes, 1),
        "total_kb": round(total_kb, 2),
        "total_mb": round(total_mb, 3),
    }

    if verbose:
        print(f"\n# RAM Usage Estimate:", file=sys.stderr)
        print(f"#   {estimate['entries']} corrections", file=sys.stderr)
        print(
            f"#   ~{estimate['per_entry_bytes']:.0f} bytes per entry", file=sys.stderr
        )
        print(
            f"#   Total: {estimate['total_kb']:.1f} KB ({estimate['total_mb']:.2f} MB)",
            file=sys.stderr,
        )
        print(f"#   (Espanso runtime overhead not included)", file=sys.stderr)

    return estimate


def write_yaml_files(
    corrections_by_letter: dict[str, list[dict]], output_dir: str, verbose: bool
) -> None:
    """Write typos_X.yml files."""
    output_dir = os.path.expanduser(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    total_entries = 0
    for letter, matches in sorted(corrections_by_letter.items()):
        if letter == "symbols":
            filename = os.path.join(output_dir, "typos_symbols.yml")
        else:
            filename = os.path.join(output_dir, f"typos_{letter}.yml")

        yaml_output = {"matches": matches}

        with open(filename, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                yaml_output,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
                width=float("inf"),
            )

        total_entries += len(matches)
        if verbose:
            print(f"Wrote {len(matches)} corrections to {filename}", file=sys.stderr)

    if verbose:
        print(
            f"\nTotal: {total_entries} corrections across {len(corrections_by_letter)} files",
            file=sys.stderr,
        )


def generate_espanso_yaml(
    corrections: list[Correction], output: str | None, verbose: bool
) -> None:
    """Generate Espanso YAML output."""
    sorted_corrections = sorted(corrections, key=lambda c: (c[1], c[0]))

    # Estimate RAM usage
    estimate_ram_usage(sorted_corrections, verbose)

    if output:
        corrections_by_letter = organize_by_letter(sorted_corrections)
        write_yaml_files(corrections_by_letter, output, verbose)
    else:
        yaml_dicts = [correction_to_yaml_dict(c) for c in sorted_corrections]
        yaml_output = {"matches": yaml_dicts}
        yaml.safe_dump(
            yaml_output,
            sys.stdout,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=float("inf"),
        )
