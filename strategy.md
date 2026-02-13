1. Fingerprint-Based Matching
Inspiration: Git's diff algorithm and database schema migration tools
- Why: Fast O(1) lookups instead of O(n²) pairwise comparisons
- Benefit: Scales to hundreds of columns efficiently
- Trade-off: Misses "identity-preserving" changes (same column, total transformation)
2. Position-Aware Rename Detection
Inspiration: Levenshtein distance / Edit distance algorithms
- Constraint: abs(pos_diff) <= 1 prevents false positives
- Rationale: Columns rarely move more than 1 position when renamed
- Fallback: If renamed AND moved far → treated as removal + addition
3. Compound Change Detection
Inspiration: Database migration frameworks (Alembic, Flyway)
- Problem: Rename + Type change looks like removal + addition
- Solution: Match removal/addition pairs by proximity
- Impact: Always marked BREAKING (complex transformation)
4. Three-Pass Architecture
Inspiration: Compiler optimization passes / Multi-pass parsers
Pass 1: Exact matches (cheap)
Pass 2: Partial matches (rename by position)
Pass 3: Remainder classification (type changes, additions, removals)
Benefit: Each pass narrows the search space for the next
5. Impact Categorization
Inspiration: SemVer (Semantic Versioning) and API compatibility theory
| Change | Source Impact | Target Impact | Rationale |
|--------|--------------|---------------|-----------|
| Removal | BREAKING | WARNING | Breaks mappings |
| Type Change | WARNING | BREAKING | Affects consumers |
| Rename | WARNING | WARNING | Reference updates needed |
| Addition | COMPATIBLE | COMPATIBLE | Non-breaking |
6. Source-Target Mapping Validation
Inspiration: Foreign key constraints in databases
- Validates referential integrity between bronze → silver
- Detects orphaned target columns early
Why Not Graph-Based?
Considered but rejected:
- Graph isomorphism is NP-hard (slow)
- Overkill for linear column lists
- Current solution: O(n) vs O(n²) or worse
Alternative I considered: Myers' diff algorithm (https://blog.jcoglan.com/2017/02/12/the-myers-diff-algorithm-part-1/) (used in Git)
- Better for line-based text diffs
- Overkill for structured YAML with known schema
Robustness Features
1. Graceful degradation → Unknown changes default to removal+addition
2. Ordered processing → Consistent, deterministic results
3. Fingerprint collision handling → Explicit checks prevent false matches