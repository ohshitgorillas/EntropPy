# EntropPy: Complete Algorithm Documentation

This document explains how EntropPy works, from loading dictionaries to generating the final autocorrect output.

---

## Overview: The Complete Pipeline

EntropPy processes words through eight main stages:

1. **Dictionary Loading** - Loads source words and validation dictionaries
2. **Typo Generation** - Creates typos from each word using five error types
3-6. **Iterative Solver** - Runs multiple passes iteratively until convergence:
   - **Stage 3: Candidate Selection** - Resolves collisions and selects corrections
   - **Stage 4: Pattern Generalization** - Finds common patterns to reduce dictionary size
   - **Stage 5: Conflict Removal** - Removes corrections that would interfere with each other
   - **Stage 5.5: Platform Substring Conflict Detection** - Detects cross-boundary conflicts
   - **Stage 6: Platform Constraints** - Applies platform-specific constraints (character set, length limits)
7. **Platform Ranking** - Ranks and selects the best corrections for the platform
8. **Output Generation** - Generates platform-specific output files
9. **Report Generation** (optional) - Generates detailed reports if `--reports` is specified

The iterative solver (stages 3-6) runs multiple passes in a loop until no changes occur (convergence) or the maximum iteration limit is reached. This allows the system to self-heal: when conflicts are detected, corrections are added to a "graveyard" and retried with stricter boundaries on the next iteration.

Let's walk through each stage in detail.

---

## Stage 1: Dictionary Loading

### What Happens

EntropPy loads three types of data:

1. **Source Words** - The words to generate typos from
2. **Validation Dictionary** - Words that are considered "valid" (typos shouldn't match these)
3. **Configuration** - Adjacent key mappings, exclusions, etc.

### Source Words

Source words come from two places:

- **Top-N from wordfreq**: The most common English words (e.g., `--top-n 5000`)
- **Include file**: Custom words you specify (e.g., `--include my_words.txt`)
- **Full dictionary (with `--hurtmycpu`)**: When `--hurtmycpu` is enabled, ALL words from the `english-words` dictionary are used as source words (minus exclusions and length filters). This enables comprehensive pattern discovery but takes significantly longer to process. The `--top-n` argument still controls final dictionary selection/ranking.

### Validation Dictionary

The validation dictionary is built from:

- **English words database** (`english-words` package with web2 and gcide)
- **Include file words** (added to validation set)
- **Exclude file patterns** (removed from validation set)

### Adjacent Key Mapping

If provided, this maps each key to its adjacent keys on the keyboard. This is used to generate realistic typos based on keyboard layout.

### Exclusion Patterns

Exclusions can filter out:
- **Words** from the validation dictionary (using wildcard patterns like `*teh*`)
- **Corrections** from being generated (using `typo -> word` syntax)

---

## Stage 2: Typo Generation

### What Happens

For each source word, EntropPy generates typos using five algorithms:

1. **Transpositions** - Swapped adjacent characters
2. **Omissions** - Missing characters
3. **Duplications** - Doubled characters
4. **Replacements** - Wrong characters (requires adjacent key map)
5. **Insertions** - Extra characters (requires adjacent key map)

### Algorithm Details

#### 1. Transpositions

Swaps each pair of adjacent characters. For a word of length n, generates n-1 typos.

**Example**: "have" → `ahve`, `hvae`, `haev`

#### 2. Omissions

Removes each character (only for words with 4+ characters). For a word of length n, generates n typos.

**Example**: "have" → `ave`, `hve`, `hae`, `hav` (some filtered if valid words)

#### 3. Duplications

Doubles each character. For a word of length n, generates n typos.

**Example**: "have" → `hhave`, `haave`, `havve`, `havee`

#### 4. Replacements

Replaces each character with adjacent keys (requires adjacent key map). For each character that has adjacent keys mapped, generates one typo per adjacent key.

**Example**: "have" (h→g,j; a→s,w,q; v→c,b,f,g) → `gave`, `jave`, `hsve`, `hwve`, `hqve`, `hace`, `habe`, `hafe`, `hage`

#### 5. Insertions

Inserts adjacent keys before or after each character (requires adjacent key map). For each character that has adjacent keys mapped, generates two typos per adjacent key: one inserted after, one before.

**Example**: "have" (v→w,r) → `havew`, `havwe`, `haver` (filtered), `havre`

### Filtering Generated Typos

Not all generated typos are kept. Each typo is filtered if it:
1. Is the original word
2. Is a source word
3. Is in the validation dictionary
4. Is explicitly excluded
5. Exceeds frequency threshold (too common, likely a real word)

Some typos map to multiple words - this is a **collision** that needs resolution in the next stage.

---

## Stage 3: Candidate Selection (Collision Resolution)

**Note**: This is the first pass in the iterative solver (stages 3-6). The solver runs all passes in sequence, then checks for convergence. If changes occurred, it runs another iteration.

### What Happens

When multiple words map to the same typo, EntropPy must decide which correction to use (or skip it entirely).

### Resolution Algorithm

The key insight is that **boundaries fundamentally change whether corrections conflict**. For example, "nto" with BOTH boundary → "not" doesn't conflict with "nto" with NONE boundary → "onto" because they match in different contexts.

**New Algorithm (Boundary-First Approach):**

1. **Determine boundaries for all competing words** - For each word competing for the same typo, determine the least restrictive boundary that prevents false triggers
2. **Group words by boundary type** - Separate competing words into groups based on their boundary type (NONE, LEFT, RIGHT, BOTH)
3. **Resolve collisions within each boundary group** - For each boundary group:
   - If only one word in the group → accept it (no collision for this boundary)
   - If multiple words in the group → apply frequency-based resolution:
     - Calculate word frequencies using `wordfreq`
     - Compare frequencies - if one word is much more common (ratio > threshold), use it
     - If ratio is too low, skip this boundary group (ambiguous for this boundary)
4. **Validate** - Check length, exclusions, etc. for each accepted correction
5. **Return multiple corrections** - One correction per valid boundary group

**Result**: The same typo can produce multiple corrections with different boundaries, as long as they don't conflict within the same boundary group. For example, "nto" can map to:
- "nto" (BOTH) → "not" (standalone word only)
- "nto" (NONE) → "onto" (matches anywhere)

**Examples**: Ambiguous collisions (skipped due to similar frequencies):
- `theree` → `['there', 'three']` (ratio 1.00) - skipped
- `fel` → `['feel', 'felt', 'fell', 'fuel']` (ratio 1.00) - skipped
- `businesss` → `['business', 'businesses']` (ratio 1.00) - skipped

**Note**: User words (from include file) are included in collision resolution like any other words. They receive special priority treatment during QMK ranking (Stage 6), not during collision resolution.

### Boundary Selection

For each typo, EntropPy selects the **least restrictive boundary** that doesn't cause false triggers (garbage corrections).

**Selection Algorithm:**

1. **Determine boundary order to try** based on typo's relationship to target word:
   - If typo is suffix of target → Try: NONE, RIGHT, BOTH (skip LEFT - incompatible)
   - If typo is prefix of target → Try: NONE, LEFT, BOTH (skip RIGHT - incompatible)
   - If typo is middle substring of target → Try: NONE, BOTH (skip LEFT and RIGHT - both incompatible)
   - If no relationship detected → Try: NONE, LEFT, RIGHT, BOTH (try all)

2. **For each boundary in order**, check if it would cause false triggers (priority: target word → validation words → source words):
   - **Target word check (highest priority)**: Prevents "predictive corrections" (e.g., `alway -> always` with NONE would trigger when typing "always")
   - **Validation words check**: Uses full validation set to catch all garbage corrections
   - **Source words check**: Checks if typo appears in source words
   - **NONE**: False trigger if typo appears as substring anywhere
   - **LEFT**: False trigger if typo appears as prefix
   - **RIGHT**: False trigger if typo appears as suffix
   - **BOTH**: Never causes false triggers (always safe)

3. **Select the first boundary** that doesn't cause false triggers and passes all other checks (length, exclusions)

4. **Graveyard false triggers**: If a boundary would cause false triggers, it is added to the graveyard with `RejectionReason.FALSE_TRIGGER`. This prevents the same unsafe boundary from being retried on subsequent iterations.

5. **Fallback**: If all boundaries would cause false triggers or fail other checks, the correction is **not added** in this iteration. On the next iteration, the graveyard prevents retrying unsafe boundaries, allowing the solver to try safer boundaries (e.g., BOTH instead of NONE) and eventually converge to a safe solution.

**Key Principle**: Select the least restrictive boundary that safely prevents the typo from incorrectly matching the target word, validation words, or source words in unintended contexts. The boundary order is optimized based on the typo's relationship to the target word to avoid testing incompatible boundaries. Target word check takes highest priority to prevent predictive corrections.

---

## Stage 4: Pattern Generalization

**Note**: This is the second pass in the iterative solver. It runs after Candidate Selection on each iteration.

### What Happens

EntropPy looks for common patterns in corrections to reduce dictionary size. Instead of storing many similar corrections, it stores one pattern that matches multiple cases.

### Pattern Types

Patterns are classified using the `PatternType` enum (`PREFIX`, `SUFFIX`, `SUBSTRING`) based on where they appear in words. Patterns are extracted from both the **end** of words (suffix patterns) and the **beginning** (prefix patterns) for all platforms, regardless of matching direction. Both types are useful:
- **Prefix patterns** (`PatternType.PREFIX`): match at start of words (e.g., "teh" → "the")
- **Suffix patterns** (`PatternType.SUFFIX`): match at end of words (e.g., "toin" → "tion")
- **Substring patterns** (`PatternType.SUBSTRING`): appear in the middle of words (true substrings, typically rejected if `NONE` boundary fails)

#### Suffix Patterns

Patterns are extracted from the end of words. The algorithm:
1. Groups corrections by word length (for efficiency)
2. For each correction, extracts all valid pattern candidates at different suffix lengths (2 to max)
3. Groups directly by `(typo_pattern, word_pattern, boundary)` across ALL corrections, regardless of their "other part" (prefix)
4. A pattern is found when 2+ corrections share the same typo suffix and word suffix

**Key improvement**: Patterns are found even when corrections have different prefixes. For example, "action" → "action" and "lection" → "lection" both share the pattern "tion" → "tion".

**Examples**:
- `nnign → nning` replaced 5 corrections: `beginnign`, `plannign`, `stunnign`, `runnign`, `winnign`
- `nibg → ning` replaced 28 corrections: `plannibg`, `minibg`, `meanibg`, `runnibg`, etc.
- `giht → ight` replaced 13 corrections: `flgiht`, `alrgiht`, `kngiht`, `brgiht`, etc.

**Boundary inclusion**: For suffix patterns, corrections with `RIGHT`, `BOTH`, and `NONE` boundaries are included. BOTH is included because it includes RIGHT (matches at word end), and NONE boundary corrections can still have valid suffix patterns.

#### Prefix Patterns

Prefix patterns work similarly but extract from the beginning of words:
1. Groups corrections by word length (for efficiency)
2. For each correction, extracts all valid pattern candidates at different prefix lengths (2 to max)
3. Groups directly by `(typo_pattern, word_pattern, boundary)` across ALL corrections, regardless of their "other part" (suffix)
4. A pattern is found when 2+ corrections share the same typo prefix and word prefix

**Boundary inclusion**: For prefix patterns, corrections with `LEFT`, `BOTH`, and `NONE` boundaries are included. BOTH is included because it includes LEFT (matches at word start), and NONE boundary corrections can still have valid prefix patterns.

**Examples**:
- `prvo → prov` (LEFT) replaced 2: `prvoen`, `prvoed`
- `trsd → trad` (LEFT) replaced 3: `trsditional`, `trsding`, `trsdition`
- `srcu → secu` (LEFT) replaced 3: `srcurity`, `srcured`, `srcurities`

### Pattern Extraction Caching

Pattern extraction results are cached per correction to avoid re-extraction across solver iterations. Patterns are extracted once, then filtered by graveyard state on each iteration. This significantly reduces extraction time when corrections persist across multiple iterations.

### Pattern Boundary Assignment

Patterns are extracted with `NONE` boundary, independent of their source corrections' boundaries. During validation, the solver determines the appropriate boundary based on the pattern type:

- **Prefix patterns** (appear at start of words): Try `NONE` first, then `LEFT` if `NONE` fails
- **Suffix patterns** (appear at end of words): Try `NONE` first, then `RIGHT` if `NONE` fails
- **Substring patterns** (appear in middle of words): Only try `NONE`, reject if it fails

**Important**: Patterns never use `BOTH` boundary, as it makes no sense for patterns which are inherently prefix or suffix transformations.

### Pattern Validation

Not all patterns are valid. Each pattern must pass these checks in order:

1. **Have at least 2 occurrences** - Patterns with only one occurrence are skipped (not worth generalizing)
2. **Meet minimum length** - Pattern must be at least `min_typo_length` characters
3. **Work for all occurrences** - The pattern must correctly transform all matching typos (validates that applying the pattern to each full typo produces the expected full word)
4. **Not conflict with validation words** - Pattern typo must not be a validation word, and must not trigger at the start or end of validation words. The boundary type determines which checks are performed:
   - **RIGHT boundary**: Only checks if pattern would trigger at end (skips start check, since RIGHT only matches at word end)
   - **LEFT boundary**: Only checks if pattern would trigger at start (skips end check, since LEFT only matches at word start)
   - **NONE boundary**: Checks both start and end (NONE matches anywhere)

   **Example**: Pattern `teh → the` (NONE) is rejected because it would trigger at start of validation words like `tehuelet`, `teheran`
5. **Not corrupt target words (highest priority for corruption checks)** - Pattern must not incorrectly transform any target word from corrections that use the pattern (prevents predictive corrections). This check is performed before checking source words.
6. **Not corrupt source words** - Pattern must not incorrectly transform any source word
7. **Not incorrectly match other corrections** - Pattern must not appear as a substring (prefix or suffix) of another correction's typo where applying the pattern would produce a different result. This check applies in both directions regardless of platform or matching direction:
   - **Suffix conflicts**: If pattern appears as suffix of another correction's typo, applying the pattern must produce the same result as the direct correction
   - **Prefix conflicts**: If pattern appears as prefix of another correction's typo, applying the pattern must produce the same result as the direct correction
   - **Examples**: Pattern `toin → tion` is rejected because it would incorrectly match `bictoin → bitcoin` as a suffix, producing `biction` instead of `bitcoin`
8. **Not redundant with already-accepted patterns** - Pattern must not be redundant with shorter patterns that have already been accepted. A pattern is redundant if a shorter pattern would produce the same result when applied to the longer pattern's typo:
   - Checks all positions where the shorter pattern appears in the longer pattern's typo
   - If applying the shorter pattern produces the same result as the longer pattern, the longer pattern is rejected
   - **Example**: If `utoin → ution` is already accepted, then `tutoin → tution` is rejected because applying the shorter pattern produces the same result
   - This check works regardless of matching direction and prevents duplicate patterns in output

### Pattern Collision Resolution

Patterns can also have collisions (multiple words for same pattern typo). These are resolved the same way as regular collisions using frequency ratios. After collision resolution, patterns also undergo substring conflict removal to eliminate redundant patterns (e.g., if pattern "ectiona" exists, pattern "lectiona" would be redundant).

### Cross-Boundary Deduplication

After pattern validation, if a pattern's (typo, word) pair already exists as a direct correction (even with different boundary), the pattern is rejected and the direct corrections that would have been replaced by the pattern are restored to the final corrections list. This is a separate step from pattern validation that ensures patterns don't duplicate existing direct corrections.

---

## Stage 5: Conflict Removal

**Note**: This is the third pass in the iterative solver. It runs after Pattern Generalization on each iteration.

### What Happens

EntropPy removes corrections and patterns where one typo is a substring of another **with the same boundary**. This prevents shorter corrections from blocking longer ones. Both direct corrections and patterns are checked for conflicts, and patterns can conflict with each other or with direct corrections.

### Why Conflicts Matter

When a text expansion tool sees a typo, it triggers on the **first match** (shortest, leftmost). If a shorter typo matches first, a longer one becomes unreachable. Conflicts only occur when corrections share the same boundary type.

### Conflict Detection Algorithm

1. **Combine corrections and patterns** - Both `active_corrections` and `active_patterns` are included in conflict detection, as patterns can conflict with each other and with direct corrections
2. **Group by boundary type** - Process each boundary separately (conflicts only occur within the same boundary type)
3. **Sort by typo length** (shortest first) - Process shorter typos first to identify which longer typos they block
4. **For each shorter typo**, check if it appears as a substring of any longer typo **anywhere** (prefix, suffix, or middle):
   - **For RIGHT boundary**: Finds the last occurrence (right-to-left matching)
   - **For LEFT/NONE/BOTH boundaries**: Finds the first occurrence (left-to-right matching)
5. **Validate the result** - If substring match found, verify that triggering the shorter correction would produce the correct result for the longer typo
6. **If conflict found**, remove the longer typo/pattern (the shorter one blocks it) and add it to the graveyard
7. **Keep the shorter typo** (it blocks the longer one and produces the correct result)

The algorithm uses character-based indexing for efficiency, checking only typos that share the same starting/ending character.

**Example**: For "abandoned", the shorter typo `annd → and` blocks 8 longer typos like `abanndoned`, `abaandoned`, `ababndoned`, etc.

---

## Stage 5.5: Platform Substring Conflict Detection

**Note**: This is the fourth pass in the iterative solver. It runs after Conflict Removal on each iteration.

### What Happens

After within-boundary conflicts are removed (Stage 5), this pass detects **cross-boundary substring conflicts** that occur when the same typo text appears with different boundaries. This is critical for platforms like QMK where boundary markers are part of the formatted string.

### Why This Matters

**QMK (RTL)**: QMK formats boundaries using colon notation:
- `aemr` (NONE boundary) → `"aemr"`
- `aemr` (LEFT boundary) → `":aemr"`

When QMK's compiler sees both `"aemr"` and `":aemr"`, it detects that `"aemr"` is a substring of `":aemr"` and rejects the dictionary with: "Typos may not be substrings of one another, otherwise the longer typo would never trigger".

**Espanso (LTR)**: While boundaries are handled separately in YAML (not part of the trigger string), the same core typo with different boundaries can still cause runtime conflicts depending on matching order.

### Conflict Detection Algorithm

1. **Format typos with platform-specific boundary markers** (parallelized for large datasets):
   - **QMK**: Uses colon notation (`:typo`, `typo:`, `:typo:`, or `typo`)
   - **Espanso**: Uses core typo text (boundaries are separate YAML fields)
   - Results are cached to avoid redundant formatting

2. **Build formatted typo index** - Map each formatted typo to its corrections

3. **Check for substring relationships** using optimized algorithms (bidirectional detection):
   - **Superstring conflicts**: For each formatted typo, find all other typos that contain it as a substring (e.g., querying `"aemr"` finds `":aemr"`)
   - **Substring conflicts**: For each formatted typo, find all other typos that are substrings of it (e.g., querying `":aemr"` finds `"aemr"`)
   - **Rust implementation**: Uses suffix array for superstring detection (O(log N + M)) and hash map lookups for substring detection (O(L²) where L is typo length)
   - **Length bucket processing**: Group by length, only check adjacent buckets
   - **Character-based indexing**: Index shorter typos by first character, reducing comparisons from O(N²) to O(N × K)
   - **Parallel detection** (when `--jobs > 1`): Two-phase approach - parallel detection, sequential resolution (7-8x speedup)
   - **Optimized substring checks**: Use `startswith()`/`endswith()` for prefix/suffix, `in` for middle substrings

4. **Determine which to remove**: Prefer less restrictive boundary (NONE > LEFT/RIGHT > BOTH) if it doesn't cause false triggers

5. **Remove conflicting correction** and add to graveyard

### Example

For QMK with typos `aemr` (NONE) and `aemr` (LEFT):
- Formatted: `"aemr"` and `":aemr"` - conflict detected
- Decision: Remove `":aemr"` (more restrictive), keep `"aemr"` (less restrictive)
- Result: QMK compiler accepts the dictionary


---

## Stage 6: Platform Constraints

**Note**: This is the fifth and final pass in the iterative solver. It runs after Platform Substring Conflict Detection on each iteration.

### What Happens

This pass enforces platform-specific constraints and limits that corrections must satisfy. Corrections that violate constraints are removed and added to the graveyard.

### Platform Constraints

#### Espanso Constraints
- **No character limits** - Supports full Unicode
- **No correction limits** - Can handle hundreds of thousands
- **Supports boundaries** - LEFT, RIGHT, BOTH, NONE
- **Left-to-right matching** - Matches from start of word

#### QMK Constraints
- **Character limits** - Only letters (a-z) and apostrophe (')
- **Correction limits** - Limited by flash memory (typically ~1,100)
- **Supports boundaries** - Via ':' notation (:typo, typo:, :typo:)
- **Right-to-left matching** - Matches from end of word

### Constraint Validation

The Platform Constraints pass checks each correction and pattern against:

1. **Character Set Restrictions** - For QMK, removes corrections containing characters other than a-z and apostrophe. Both typo and word are checked, and both are converted to lowercase.
2. **Length Limits** - Removes corrections where typo or word exceeds platform-specific maximum lengths (if specified).
3. **Boundary Support** - Removes corrections with boundaries if the platform doesn't support them.

**Note**: From actual runs, character set violations are rare (often 0), meaning most corrections pass this filter.

---

## Stage 7: Platform Ranking

### What Happens

After the iterative solver converges, this stage ranks corrections by usefulness for the specific platform. The ranking algorithm varies by platform.

### Platform Ranking

#### QMK Ranking

QMK uses a three-tier ranking system:

1. **User words first** - All corrections for words from include file get infinite priority (always included)
2. **Patterns ranked by coverage** - Patterns are scored by the sum of word frequencies of all corrections they replace. Higher total frequency ranks higher.
3. **Direct corrections ranked by frequency** - Direct corrections are scored by their word frequency. More common words rank higher.

Within each tier, corrections are sorted by score (descending). The final ranked list is: user corrections + sorted patterns + sorted direct corrections.

**Example** (from actual QMK run):
- User words: 282 (28.2%) - always included first (e.g., `fiurmware → firmware`, `keybnoard → keyboard`)
- Patterns: 718 (71.8%) - ranked by sum of word frequencies of replaced corrections (e.g., `nibg → ning` replaced 28 corrections)
- Direct corrections: 0 (0.0%) - none made it into top 1,000 (patterns were more valuable)

#### Espanso Ranking

Espanso uses no ranking - corrections are passed through in their original order (passthrough). They are sorted alphabetically by word, then by typo, for output organization only.

---

## Stage 8: Output Generation

### What Happens

This stage applies platform limits (if any) and generates platform-specific output files.

### Applying Limits

If the platform has a `max_corrections` limit, truncate the ranked list to that limit. For QMK with a limit of 1,000, only the top-ranked corrections are selected (user words always included first).

### Output Generation

#### Espanso Output

Generates YAML files with corrections, including boundary markers (`:` for boundaries) and splitting into multiple files if needed.

#### QMK Output

Generates a text file with corrections in the format `typo word`, one per line.

---

## Stage 9: Report Generation (Optional)

### What Happens

If `--reports` is specified, this stage generates detailed reports including:
- Summary statistics (word counts, typo counts, correction counts)
- Collision resolution details
- Pattern information and replacements
- Conflict detection results
- Platform-specific analysis
- Graveyard entries (rejected corrections with reasons)
- Debug traces (if debug options were enabled)

Reports are written to the specified reports directory and organized by report type.

---

## Conclusion

EntropPy's pipeline transforms a list of words into an optimized autocorrect dictionary through eight carefully designed stages. Each stage addresses specific challenges:

- **Stage 1** loads dictionaries and configuration
- **Stage 2** generates realistic typos
- **Stages 3-6** (Iterative Solver) work together to resolve ambiguities, find patterns, remove conflicts, and apply constraints through multiple iterations until convergence
- **Stage 7** ranks corrections by usefulness
- **Stage 8** generates platform-specific output
- **Stage 9** (optional) generates detailed reports

The iterative solver (stages 3-6) is key to the system's self-healing capability: when conflicts are detected, corrections are added to a graveyard and retried with stricter boundaries on subsequent iterations, allowing the system to converge to an optimal solution.

The result is a high-quality autocorrect dictionary tailored to your platform's capabilities and constraints.
