"""YAML Config Parser module."""

from typing import List, Dict, Any, Optional
import yaml
from schema_detector.models import ColumnNode


class ConfigParser:
    """Parse YAML config files into structured data."""

    @staticmethod
    def parse_file(file_path: str) -> Dict[str, Any]:
        """Parse YAML file and return dictionary."""
        with open(file_path, "r") as f:
            return yaml.safe_load(f)

    @staticmethod
    def parse_content(content: str) -> Dict[str, Any]:
        """Parse YAML content from string."""
        return yaml.safe_load(content)

    @staticmethod
    def extract_source_columns(config: Dict[str, Any]) -> List[ColumnNode]:
        """Extract source columns from config."""
        columns = []
        source_cols = config.get("dataset", {}).get("source", {}).get("columns", [])

        for idx, col in enumerate(source_cols):
            columns.append(
                ColumnNode(
                    name=col.get("name", ""),
                    dtype=col.get("dtype"),
                    position=idx,
                    description=col.get("description"),
                )
            )

        return columns

    @staticmethod
    def extract_target_columns(config: Dict[str, Any]) -> List[ColumnNode]:
        """Extract target columns from config."""
        columns = []
        target_cols = config.get("dataset", {}).get("target", {}).get("columns", [])

        for idx, col in enumerate(target_cols):
            columns.append(
                ColumnNode(
                    name=col.get("name", ""),
                    dtype=col.get("dtype"),
                    position=idx,
                    standardname=col.get("standardname"),
                    description=col.get("description"),
                    tags=col.get("tags"),
                )
            )

        return columns

    @staticmethod
    def extract_dataset_info(config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract dataset identifier information."""
        identifier = config.get("dataset", {}).get("identifier", {})
        return {
            "datasetname": identifier.get("datasetname"),
            "sourcesystem": identifier.get("sourcesystem"),
            "sourcetablename": identifier.get("sourcetablename"),
            "targettablename": identifier.get("targettablename"),
        }
