### Fingerprint-Based Detection

Uses a 3-pass matching algorithm:
1. **Exact matches** - Same name + type (check for reordering)
2. **Rename detection** - Same type + similar position
3. **Remainder classification** - Type changes, additions, removals

### Complexity

- **Time**: O(n) for n columns
- **Space**: O(n) for fingerprint storage
