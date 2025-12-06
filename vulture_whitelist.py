"""Vulture whitelist for false positives.

This file contains code that vulture incorrectly flags as unused
but is actually used by frameworks (Pydantic) that static analysis cannot detect.
"""
# pylint: disable=all
# Pydantic field validator - used by framework via @field_validator decorator
_.parse_string_set  # noqa: F821  # unused method (entroppy/core/config.py:50)

# Pydantic model validator - used by framework via @model_validator decorator
_.validate_cross_fields  # noqa: F821  # unused method (entroppy/core/config.py:62)

# Pydantic model_config class variable - read by framework at class definition time
# Required to allow non-Pydantic types (DebugTypoMatcher) in Config model
model_config  # noqa: F821  # unused variable (entroppy/core/config.py:74)

# Pydantic model_config class variable - read by framework at class definition time
# Required to allow non-Pydantic types (ExclusionMatcher) in DictionaryData model
model_config  # noqa: F821  # unused variable (entroppy/processing/stages/data_models.py:26)

# Functions used via imports - vulture can't detect usage through imports
format_corrections_with_cache  # unused function (entroppy/resolution/platform_conflicts/formatting.py:92)
is_debug_target  # unused function (entroppy/resolution/state_debug.py:34)
create_correction_history_entry  # unused function (entroppy/resolution/state_history.py:17)
create_pattern_history_entry  # unused function (entroppy/resolution/state_history.py:52)
create_debug_trace_entry  # unused function (entroppy/resolution/state_history.py:87)
update_pattern_prefix_index_add  # unused function (entroppy/resolution/state_patterns.py:13)
update_pattern_prefix_index_remove  # unused function (entroppy/resolution/state_patterns.py:28)
