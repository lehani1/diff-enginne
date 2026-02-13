# Schema Change Detector

A Python module for detecting and reporting schema changes in YAML configuration files used for Databricks data ingestion pipelines.

## Features

- **Simple API** - One-liner functions to detect changes
- **Flexible Input** - Accept file paths, YAML strings, or Python dicts
- **Multiple Output Formats** - Dict, JSON string, or LLM-friendly text
- **Comprehensive Detection:**
  - Column additions
  - Column removals  
  - Column renames
  - Column reordering
  - Data type changes
  - Compound changes (multiple simultaneous changes)
- **Impact Analysis** - Categorizes as BREAKING, WARNING, or COMPATIBLE
- **Mapping Validation** - Validates source-to-target column mappings

## Installation

```bash
pip install -e .
```

## Quick Start

```python
from schema_detector import detect_schema_changes

# Simple one-liner - returns dict
result = detect_schema_changes("old.yml", "new.yml")
print(f"Breaking changes: {result['summary']['breaking_changes']}")

# Get JSON string
json_result = detect_schema_changes("old.yml", "new.yml", output_format="json")

# Get LLM-friendly text
text_result = detect_schema_changes("old.yml", "new.yml", output_format="text")
```

## API Reference

### `detect_schema_changes(old_config, new_config, output_format="dict")`

Detect schema changes between two YAML configurations.

**Parameters:**
- `old_config`: Path to YAML file, YAML content string, or dict
- `new_config`: Path to YAML file, YAML content string, or dict  
- `output_format`: `"dict"` (default), `"json"`, or `"text"`

**Returns:**
- `"dict"`: Python dictionary with report data
- `"json"`: JSON formatted string
- `"text"`: LLM-optimized plain text summary

**Raises:**
- `FileNotFoundError`: If file path does not exist
- `ValueError`: If invalid YAML or unsupported output format

**Examples:**

```python
from schema_detector import detect_schema_changes

# From file paths
result = detect_schema_changes("old.yml", "new.yml")

# From YAML strings
yaml_str = """
dataset:
  source:
    columns:
    - name: col1
      dtype: StringType
"""
result = detect_schema_changes(yaml_str_old, yaml_str_new, output_format="json")

# From dicts
result = detect_schema_changes(config_dict_old, config_dict_new, output_format="text")
```

### `compare_yaml_files(old_file, new_file, output_format="dict")`

Convenience wrapper specifically for file-based comparison.

**Parameters:**
- `old_file`: Path to old YAML file
- `new_file`: Path to new YAML file
- `output_format`: `"dict"` (default), `"json"`, or `"text"`

**Example:**

```python
from schema_detector import compare_yaml_files

result = compare_yaml_files("configs/old.yml", "configs/new.yml")
```

## Output Format

### Dict Format

```python
{
    "summary": {
        "total_changes": 5,
        "breaking_changes": 1,
        "warnings": 2,
        "compatible_changes": 2
    },
    "source_changes": [
        {
            "change_type": "addition",
            "section": "source",
            "column_name": "new_col",
            "impact": "compatible",
            "details": "New column 'new_col' added at position 3",
            "old_value": None,
            "new_value": {"name": "new_col", "dtype": "StringType", "position": 3}
        }
    ],
    "target_changes": [...],
    "mapping_validations": [
        {
            "valid": True,
            "source_column": "col1",
            "target_column": "col1",
            "issue": None,
            "severity": "compatible"
        }
    ]
}
```

### Text Format (Simplified)

**No changes detected:**
```
NO schema changes detected
```

**With changes (returns only changes, no headers/summaries):**
```
Change: REMOVAL
  Section: source
  Column: deprecated_col
  Impact: BREAKING
  Details: Column 'deprecated_col' removed
  Old: {'name': 'deprecated_col', 'dtype': 'StringType', 'position': 2}

Change: ADDITION
  Section: target
  Column: new_col
  Impact: COMPATIBLE
  Details: New column 'new_col' added at position 3
  New: {'name': 'new_col', 'dtype': 'StringType', 'position': 3, 'standardname': 'new_col'}
```

## Change Types

| Type | Description | Impact |
|------|-------------|--------|
| **ADDITION** | New column added | Compatible |
| **REMOVAL** | Column removed | Breaking (source), Warning (target) |
| **RENAME** | Column name changed | Warning |
| **TYPE_CHANGE** | Data type changed | Breaking (target), Warning (source) |
| **REORDER** | Column position changed | Warning |
| **COMPOUND** | Multiple simultaneous changes | Breaking |

## Advanced Usage

### Using the Core Classes Directly

For more control, you can use the underlying classes:

```python
from schema_detector import ConfigParser, SchemaChangeDetector, SchemaDiffReport

# Parse configurations
old_config = ConfigParser.parse_file("old.yml")
new_config = ConfigParser.parse_file("new.yml")

# Detect changes
detector = SchemaChangeDetector(old_config, new_config)
report = detector.detect_changes()

# Access report data programmatically
print(f"Total: {report.total_changes}")
print(f"Breaking: {report.breaking_changes}")

for change in report.source_changes:
    print(f"  {change.column_name}: {change.change_type.value}")
    
for validation in report.mapping_validations:
    if not validation.valid:
        print(f"Invalid mapping: {validation.issue}")
```

### Error Handling

```python
from schema_detector import detect_schema_changes

try:
    result = detect_schema_changes("old.yml", "new.yml")
except FileNotFoundError as e:
    print(f"File not found: {e}")
except ValueError as e:
    print(f"Invalid configuration: {e}")
```

## Testing

```bash
python -m pytest tests/ -v
```

All 26 tests pass, covering:
- Model validation
- YAML parsing (files, strings, dicts)
- All 6 change types
- Compound change detection
- Mapping validations
- Report generation (JSON, text)
- Integration tests
- New API functions

## Configuration File Structure

The detector expects YAML files with this structure:

```yaml
dataset:
  source:
    columns:
    - name: Column_1
      dtype: StringType
    - name: Column_2
      dtype: DecimalType
  
  target:
    columns:
    - name: Column_1        # References source column
      standardname: col_1   # Silver table column name
      dtype: StringType
    - name: Column_2
      standardname: col_2
```

## Architecture

### Fingerprint-Based Detection

Uses a 3-pass matching algorithm:
1. **Exact matches** - Same name + type (check for reordering)
2. **Rename detection** - Same type + similar position
3. **Remainder classification** - Type changes, additions, removals

### Complexity

- **Time**: O(n) for n columns
- **Space**: O(n) for fingerprint storage

## License

MIT License
