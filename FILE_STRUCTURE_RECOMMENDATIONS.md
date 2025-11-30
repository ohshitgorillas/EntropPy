# File Structure Recommendations for EntropPy

## Current Issues

1. **Root directory clutter** - Output directories mixed with source code
2. **Flat package structure** - Too many modules at `entroppy/` root level
3. **Naming inconsistencies** - `conflict_resolution.py` vs `collision_resolution.py`
4. **Mixed abstraction levels** - Core logic, utilities, and infrastructure mixed together
5. **Redundant directories** - `examples/` and `settings/` serve similar purposes
6. **Generic module names** - `utils.py`, `processing.py` are too vague

## Recommended Structure

```
typogen_espanso/
├── README.md
├── CHANGELOG.md
├── LICENSE
├── requirements.txt
├── requirements-testing.txt
├── pyproject.toml (or setup.py)
│
├── entroppy/                    # Main package
│   ├── __init__.py
│   ├── __main__.py
│   │
│   ├── cli/                     # CLI interface
│   │   ├── __init__.py
│   │   └── parser.py            # (renamed from cli.py)
│   │
│   ├── core/                    # Core domain logic
│   │   ├── __init__.py
│   │   ├── config.py            # Configuration models
│   │   ├── boundaries.py        # Boundary detection logic
│   │   ├── typos.py             # Typo generation algorithms
│   │   └── patterns.py          # Pattern matching and generalization
│   │
│   ├── processing/              # Processing pipeline stages
│   │   ├── __init__.py
│   │   ├── pipeline.py          # Main orchestration
│   │   ├── stages/              # Individual pipeline stages
│   │   │   ├── __init__.py
│   │   │   ├── data_models.py
│   │   │   ├── dictionary_loading.py
│   │   │   ├── typo_generation.py
│   │   │   ├── collision_resolution.py
│   │   │   ├── pattern_generalization.py
│   │   │   ├── conflict_removal.py
│   │   │   └── worker_context.py
│   │   └── collision.py         # (renamed from processing.py - collision resolution)
│   │
│   ├── resolution/              # Conflict and collision resolution
│   │   ├── __init__.py
│   │   ├── collisions.py        # Frequency-based collision resolution
│   │   └── conflicts.py         # (renamed from conflict_resolution.py)
│   │
│   ├── matching/                # Pattern and exclusion matching
│   │   ├── __init__.py
│   │   ├── pattern_matcher.py   # (renamed from pattern_matching.py)
│   │   └── exclusions.py        # Exclusion rule matching
│   │
│   ├── platforms/               # Platform backends
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── espanso/
│   │   │   ├── __init__.py
│   │   │   ├── backend.py       # (renamed from espanso.py)
│   │   │   └── reports.py       # (renamed from espanso_report.py)
│   │   └── qmk/
│   │       ├── __init__.py
│   │       ├── backend.py       # (renamed from qmk.py)
│   │       └── reports.py       # (renamed from qmk_report.py)
│   │
│   ├── data/                    # Data loading and management
│   │   ├── __init__.py
│   │   ├── dictionary.py        # Dictionary loading
│   │   └── validation.py        # Word validation utilities
│   │
│   ├── reporting/               # Report generation
│   │   ├── __init__.py
│   │   ├── core.py              # (renamed from reports.py)
│   │   └── formatters.py        # Report formatting utilities
│   │
│   └── utils/                   # General utilities
│       ├── __init__.py
│       ├── logging.py           # (renamed from logger.py)
│       ├── debug.py             # (renamed from debug_utils.py)
│       └── helpers.py           # (renamed from utils.py)
│
├── tests/                       # Test suite
│   ├── unit/
│   ├── integration/
│   └── backends/
│
├── config/                      # Configuration examples (renamed from settings/)
│   ├── config.json
│   ├── config_qmk.json
│   ├── adjacent.txt
│   ├── exclude.txt
│   └── include.txt
│
├── examples/                    # Usage examples (keep separate from config)
│   ├── adjacent.txt
│   ├── config.json
│   ├── exclude.txt
│   └── include.txt
│
└── .gitignore                   # Already properly configured

# Output directories (gitignored, created at runtime)
├── corrections/                 # Generated correction files
├── reports/                     # Generated reports
├── test_qmk/                    # Test outputs
└── test_reports/                # Test report outputs
```

## Key Improvements

### 1. **Organized by Domain/Responsibility**
   - **`core/`**: Core domain logic (boundaries, typos, patterns)
   - **`processing/`**: Pipeline orchestration and stages
   - **`resolution/`**: Collision and conflict resolution algorithms
   - **`matching/`**: Pattern and exclusion matching
   - **`platforms/`**: Platform-specific implementations (further organized by platform)
   - **`data/`**: Data loading and validation
   - **`reporting/`**: Report generation
   - **`utils/`**: General utilities

### 2. **Clearer Naming**
   - `cli.py` → `cli/parser.py` (more descriptive)
   - `conflict_resolution.py` → `resolution/conflicts.py` (clearer purpose)
   - `processing.py` → `processing/collision.py` (more specific)
   - `pattern_matching.py` → `matching/pattern_matcher.py` (consistent with class name)
   - `logger.py` → `utils/logging.py` (more descriptive)
   - `debug_utils.py` → `utils/debug.py` (shorter, clearer)
   - `utils.py` → `utils/helpers.py` (more specific)
   - Platform files: `espanso.py` → `espanso/backend.py` (clearer purpose)

### 3. **Better Platform Organization**
   - Each platform gets its own subdirectory
   - Backend and report logic separated but co-located
   - Easier to add new platforms

### 4. **Consolidated Configuration**
   - `settings/` → `config/` (more standard name)
   - Keep `examples/` separate for usage examples
   - Clear distinction between user configs and examples

### 5. **Logical Grouping**
   - Related functionality grouped together
   - Easier to navigate and understand dependencies
   - Better separation of concerns

## Migration Strategy

### Phase 1: Low-Risk Moves (Non-Breaking)
1. Create new directory structure
2. Move files with import updates
3. Update `__init__.py` files to maintain backward compatibility
4. Run tests to verify

### Phase 2: Rename for Clarity
1. Rename modules with clearer names
2. Update all imports
3. Update documentation

### Phase 3: Consolidate
1. Merge `examples/` and `settings/` logic
2. Clean up any duplicate functionality
3. Final test verification

## Benefits

1. **Easier Navigation**: Related code is grouped together
2. **Clearer Intent**: Module names reflect their purpose
3. **Better Scalability**: Easy to add new platforms, stages, or utilities
4. **Improved Maintainability**: Clear separation of concerns
5. **Professional Structure**: Follows Python packaging best practices

## Alternative: Minimal Refactoring

If a full restructure is too disruptive, consider these minimal changes:

1. **Group related modules**:
   - Move `conflict_resolution.py` → `resolution/conflicts.py`
   - Move `processing.py` → `processing/collision.py`
   - Move `pattern_matching.py` → `matching/pattern_matcher.py`

2. **Rename for clarity**:
   - `utils.py` → `helpers.py`
   - `debug_utils.py` → `debug.py`
   - `logger.py` → `logging.py`

3. **Organize platforms**:
   - Create `platforms/espanso/` and `platforms/qmk/` subdirectories

4. **Consolidate config**:
   - Merge `examples/` into `settings/` or vice versa

This minimal approach provides 80% of the benefits with 20% of the effort.

