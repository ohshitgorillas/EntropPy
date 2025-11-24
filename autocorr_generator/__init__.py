"""Espanso Autocorrect Dictionary Generator.

Generate mechanical typing error corrections for Espanso text expander.
"""

from .config import BoundaryType, Config, Correction, load_config
from .pipeline import run_pipeline

__version__ = "2.1.0"
__all__ = ["BoundaryType", "Config", "Correction", "load_config", "run_pipeline"]
