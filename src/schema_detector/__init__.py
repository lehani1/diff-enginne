"""Schema Change Detector for YAML Config Files.

This package provides tools to detect and report schema changes
in YAML configuration files used for Databricks data ingestion.

Quick Start:
    >>> from schema_detector import detect_schema_changes
    >>> result = detect_schema_changes("old.yml", "new.yml")
    >>> print(result)
"""

from .models import (
    ColumnNode,
    ChangeEvent,
    ChangeType,
    ImpactLevel,
    MappingValidation,
    SchemaDiffReport,
)
from .parser import ConfigParser
from .detector import SchemaChangeDetector
from .reporter import ReportGenerator
from .api import detect_schema_changes, compare_yaml_files

__version__ = "1.0.0"
__all__ = [
    "ColumnNode",
    "ChangeEvent",
    "ChangeType",
    "ImpactLevel",
    "MappingValidation",
    "SchemaDiffReport",
    "ConfigParser",
    "SchemaChangeDetector",
    "ReportGenerator",
    "detect_schema_changes",
    "compare_yaml_files",
]
