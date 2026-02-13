"""Simple API for schema change detection - optimized for programmatic use.

This module provides convenient one-liner functions for detecting schema changes
without CLI overhead. Output is optimized for LLM consumption and programmatic use.
"""

from pathlib import Path
from typing import Union, Dict, Any
import json

from schema_detector.parser import ConfigParser
from schema_detector.detector import SchemaChangeDetector
from schema_detector.reporter import ReportGenerator
from schema_detector.models import SchemaDiffReport


def detect_schema_changes(
    old_config: Union[str, Path, Dict[str, Any]],
    new_config: Union[str, Path, Dict[str, Any]],
    output_format: str = "dict",
) -> Union[Dict[str, Any], str]:
    """
    Detect schema changes between two YAML configurations.

    Args:
        old_config: Path to YAML file, YAML content string, or dict
        new_config: Path to YAML file, YAML content string, or dict
        output_format: "dict" (default) or "json" or "text"
            - "dict": Returns Python dictionary
            - "json": Returns JSON string
            - "text": Returns LLM-optimized plain text summary

    Returns:
        Schema change report in requested format

    Raises:
        FileNotFoundError: If file path does not exist
        ValueError: If invalid YAML or unsupported output format
        Exception: For parsing or detection errors

    Examples:
        >>> # From file paths
        >>> result = detect_schema_changes("old.yml", "new.yml")

        >>> # From YAML strings
        >>> result = detect_schema_changes(yaml_string_old, yaml_string_new, output_format="json")

        >>> # From dicts
        >>> result = detect_schema_changes(config_dict_old, config_dict_new, output_format="text")
    """
    # Parse configurations
    old_parsed = _parse_input(old_config)
    new_parsed = _parse_input(new_config)

    # Detect changes
    detector = SchemaChangeDetector(old_parsed, new_parsed)
    report = detector.detect_changes()

    # Return in requested format
    if output_format == "dict":
        return report.to_dict()
    elif output_format == "json":
        return json.dumps(report.to_dict(), indent=2)
    elif output_format == "text":
        return ReportGenerator.generate_text_report(report)
    else:
        raise ValueError(
            f"Unsupported output_format: {output_format}. Use 'dict', 'json', or 'text'"
        )


def compare_yaml_files(
    old_file: Union[str, Path], new_file: Union[str, Path], output_format: str = "dict"
) -> Union[Dict[str, Any], str]:
    """
    Compare two YAML files and return schema differences.

    This is a convenience wrapper specifically for file-based comparison.

    Args:
        old_file: Path to old YAML configuration file
        new_file: Path to new YAML configuration file
        output_format: "dict" (default), "json", or "text"

    Returns:
        Schema change report in requested format

    Raises:
        FileNotFoundError: If either file does not exist
        ValueError: If invalid YAML content
    """
    old_path = Path(old_file)
    new_path = Path(new_file)

    if not old_path.exists():
        raise FileNotFoundError(f"Old config file not found: {old_file}")
    if not new_path.exists():
        raise FileNotFoundError(f"New config file not found: {new_file}")

    return detect_schema_changes(old_path, new_path, output_format)


def _parse_input(config_input: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Parse input which can be file path, YAML string, or dict.

    Args:
        config_input: File path, YAML string, or dict

    Returns:
        Parsed configuration dictionary

    Raises:
        FileNotFoundError: If file path does not exist
        ValueError: If cannot parse as YAML or dict
    """
    # If it's already a dict, return as-is
    if isinstance(config_input, dict):
        return config_input

    # If it's a Path or string that looks like a file path
    if isinstance(config_input, Path):
        if not config_input.exists():
            raise FileNotFoundError(f"Config file not found: {config_input}")
        return ConfigParser.parse_file(str(config_input))

    if isinstance(config_input, str):
        # Check if it's a file path (ends with .yml/.yaml or exists as a file)
        path = Path(config_input)
        is_likely_file = path.suffix in [".yml", ".yaml"] or (
            "\n" not in config_input and len(config_input) < 500
        )

        if is_likely_file:
            if not path.exists():
                raise FileNotFoundError(f"Config file not found: {config_input}")
            return ConfigParser.parse_file(str(path))

        # Otherwise treat as YAML content
        try:
            return ConfigParser.parse_content(config_input)
        except Exception as e:
            raise ValueError(f"Invalid YAML content: {e}")

    raise ValueError(
        f"Unsupported input type: {type(config_input)}. Use file path, YAML string, or dict"
    )
