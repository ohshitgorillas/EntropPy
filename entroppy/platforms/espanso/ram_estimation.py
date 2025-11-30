"""Espanso RAM usage estimation."""

from loguru import logger

from entroppy.core import Correction


def estimate_ram_usage(corrections: list[Correction], verbose: bool = False) -> dict[str, float]:
    """Estimate RAM usage of generated corrections."""
    avg_trigger_len = sum(len(c[0]) for c in corrections) / len(corrections) if corrections else 0
    avg_replace_len = sum(len(c[1]) for c in corrections) / len(corrections) if corrections else 0

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
        logger.info("\n# RAM Usage Estimate:")
        logger.info(f"#   {estimate['entries']} corrections")
        logger.info(f"#   ~{estimate['per_entry_bytes']:.0f} bytes per entry")
        logger.info(f"#   Total: {estimate['total_kb']:.1f} KB ({estimate['total_mb']:.2f} MB)")
        logger.info("#   (Espanso runtime overhead not included)")

    return estimate
