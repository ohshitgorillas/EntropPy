"""Espanso YAML conversion utilities."""

from entroppy.core import BoundaryType, Correction


def correction_to_yaml_dict(correction: Correction) -> dict:
    """Convert correction to Espanso match dict."""
    typo, word, boundary = correction

    match_dict = {"trigger": typo, "replace": word, "propagate_case": True}

    if boundary == BoundaryType.BOTH:
        match_dict["word"] = True
    elif boundary == BoundaryType.LEFT:
        match_dict["left_word"] = True
    elif boundary == BoundaryType.RIGHT:
        match_dict["right_word"] = True

    return match_dict
