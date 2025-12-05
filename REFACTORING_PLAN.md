# Refactoring Plan

## Issues

**Large files (>500 lines):**
- `core/pattern_validation_runner.py` (733 lines)
- `resolution/platform_substring_conflict_detection.py` (675 lines)
- `resolution/correction_processing.py` (652 lines)
- `core/pattern_extraction.py` (624 lines)
- `platforms/qmk/ranking.py` (527 lines)
- `resolution/passes/candidate_selection.py` (495 lines)
- `resolution/solver.py` (487 lines)

**Scattered related code:**
- Pattern functionality: 7 files in `core/` (extraction, validation, conflicts, indexes, logging)
- Platform substring conflicts: 4 files in `resolution/` (detection, debug, logging, pass)
- Boundary code: split between `core/boundaries.py` and `resolution/boundary_*.py`

## Refactoring Actions

### 1. Consolidate Pattern Code
Move pattern-related files into `core/patterns/`:
```
core/patterns/
  ├── __init__.py
  ├── extraction.py          # From pattern_extraction.py (split if needed)
  ├── validation/
  │   ├── __init__.py
  │   ├── runner.py          # From pattern_validation_runner.py (split)
  │   ├── worker.py          # From pattern_validation_worker.py
  │   ├── validator.py       # From pattern_validation.py
  │   └── conflicts.py      # From pattern_conflicts.py
  ├── indexes.py             # From pattern_indexes.py
  └── logging.py             # From pattern_logging.py
```

Split `pattern_validation_runner.py` (733 lines) into runner, coordinator, and batch_processor.

### 2. Consolidate Platform Conflicts
Move platform substring conflict files into `resolution/platform_conflicts/`:
```
resolution/platform_conflicts/
  ├── __init__.py
  ├── detection.py           # Core detection from platform_substring_conflict_detection.py
  ├── resolution.py          # Resolution logic (split from detection.py)
  ├── debug.py               # From platform_substring_conflict_debug.py
  ├── logging.py             # From platform_substring_conflict_logging.py
  └── pass.py                # From passes/platform_substring_conflicts.py
```

Split `platform_substring_conflict_detection.py` (675 lines) into detection and resolution modules.

### 3. Organize Boundaries
Split `core/boundaries.py` and group resolution boundary code:
```
core/boundaries/
  ├── __init__.py
  ├── types.py               # BoundaryType, BoundaryIndex
  ├── detection.py           # determine_boundaries, would_trigger_at_end
  ├── formatting.py          # format_boundary_* functions
  └── parsing.py             # parse_boundary_markers

resolution/boundaries/
  ├── __init__.py
  ├── selection.py           # From boundary_selection.py
  ├── utils.py               # From boundary_utils.py
  └── logging.py             # From boundary_logging.py
```

### 4. Split Remaining Large Files
- `correction_processing.py` (652) → `resolution/processing/correction_processor.py` + `graveyard.py` + `helpers.py`
- `pattern_extraction.py` (624) → `core/patterns/extraction/finder.py` + `matcher.py` + `filters.py`
- `qmk/ranking.py` (527) → `qmk/ranking/scorer.py` + `sorter.py` + `tiers.py`
- `candidate_selection.py` (495) → `resolution/passes/candidate_selection/selector.py` + `filters.py` + `helpers.py`
- `solver.py` (487) → `resolution/solver/iterative_solver.py` + `pass_context.py` + `convergence.py`

## Implementation Order

1. **Patterns consolidation** - Affects most imports, do first
2. **Platform conflicts** - Self-contained, medium effort
3. **Boundaries** - Low risk, straightforward
4. **Split remaining large files** - Can be done incrementally

## Notes

- Keep logging modules co-located with their code (don't centralize)
- Maintain public APIs via `__init__.py` exports
- Run full test suite after each major change
- Update imports incrementally, verify with grep
