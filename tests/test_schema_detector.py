"""Comprehensive tests for schema change detector."""

import pytest
import yaml
from pathlib import Path

from schema_detector import (
    ConfigParser,
    SchemaChangeDetector,
    ReportGenerator,
    ChangeType,
    ImpactLevel,
)


class TestModels:
    """Test core data models."""

    def test_column_node_fingerprint(self):
        """Test ColumnNode fingerprint generation."""
        from schema_detector.models import ColumnNode

        col = ColumnNode(name="test_col", dtype="StringType", position=0)
        assert col.fingerprint == "test_col:StringType"

        col2 = ColumnNode(name="test_col", dtype=None, position=0)
        assert col2.fingerprint == "test_col:unknown"

    def test_column_node_effective_name(self):
        """Test ColumnNode effective_name property."""
        from schema_detector.models import ColumnNode

        col = ColumnNode(
            name="old_name", dtype="StringType", position=0, standardname="new_name"
        )
        assert col.effective_name == "new_name"

        col2 = ColumnNode(name="name_only", dtype="StringType", position=0)
        assert col2.effective_name == "name_only"


class TestParser:
    """Test YAML config parser."""

    def test_parse_file(self):
        """Test parsing YAML file."""
        config_path = Path(__file__).parent.parent / "test_data" / "old_config.yml"
        config = ConfigParser.parse_file(str(config_path))

        assert "dataset" in config
        assert "source" in config["dataset"]
        assert "target" in config["dataset"]

    def test_extract_source_columns(self):
        """Test extracting source columns."""
        yaml_content = """
dataset:
  source:
    columns:
    - name: col1
      dtype: StringType
    - name: col2
      dtype: IntegerType
"""
        config = yaml.safe_load(yaml_content)
        columns = ConfigParser.extract_source_columns(config)

        assert len(columns) == 2
        assert columns[0].name == "col1"
        assert columns[0].dtype == "StringType"
        assert columns[0].position == 0

    def test_extract_target_columns(self):
        """Test extracting target columns with standardname."""
        yaml_content = """
dataset:
  target:
    columns:
    - name: col1
      standardname: col1_standard
      dtype: StringType
    - name: col2
      standardname: col2_standard
"""
        config = yaml.safe_load(yaml_content)
        columns = ConfigParser.extract_target_columns(config)

        assert len(columns) == 2
        assert columns[0].standardname == "col1_standard"
        assert columns[0].effective_name == "col1_standard"


class TestChangeDetection:
    """Test change detection scenarios."""

    def test_no_changes(self):
        """Test detection when no changes present."""
        old_config = {
            "dataset": {
                "source": {"columns": [{"name": "col1", "dtype": "StringType"}]},
                "target": {"columns": [{"name": "col1", "standardname": "col1"}]},
            }
        }

        detector = SchemaChangeDetector(old_config, old_config)
        report = detector.detect_changes()

        assert report.total_changes == 0

    def test_column_addition(self):
        """Test detecting column addition."""
        old_config = {
            "dataset": {
                "source": {"columns": [{"name": "col1", "dtype": "StringType"}]},
                "target": {"columns": [{"name": "col1", "standardname": "col1"}]},
            }
        }
        new_config = {
            "dataset": {
                "source": {
                    "columns": [
                        {"name": "col1", "dtype": "StringType"},
                        {"name": "col2", "dtype": "IntegerType"},
                    ]
                },
                "target": {
                    "columns": [
                        {"name": "col1", "standardname": "col1"},
                        {"name": "col2", "standardname": "col2"},
                    ]
                },
            }
        }

        detector = SchemaChangeDetector(old_config, new_config)
        report = detector.detect_changes()

        assert report.total_changes == 2  # One in source, one in target
        additions = [
            c for c in report.source_changes if c.change_type == ChangeType.ADDITION
        ]
        assert len(additions) == 1
        assert additions[0].column_name == "col2"

    def test_column_removal(self):
        """Test detecting column removal."""
        old_config = {
            "dataset": {
                "source": {
                    "columns": [
                        {"name": "col1", "dtype": "StringType"},
                        {"name": "col2", "dtype": "IntegerType"},
                    ]
                },
                "target": {
                    "columns": [
                        {"name": "col1", "standardname": "col1"},
                        {"name": "col2", "standardname": "col2"},
                    ]
                },
            }
        }
        new_config = {
            "dataset": {
                "source": {"columns": [{"name": "col1", "dtype": "StringType"}]},
                "target": {"columns": [{"name": "col1", "standardname": "col1"}]},
            }
        }

        detector = SchemaChangeDetector(old_config, new_config)
        report = detector.detect_changes()

        removals = [
            c for c in report.source_changes if c.change_type == ChangeType.REMOVAL
        ]
        assert len(removals) == 1
        assert removals[0].column_name == "col2"
        assert removals[0].impact == ImpactLevel.BREAKING

    def test_column_rename(self):
        """Test detecting column rename."""
        old_config = {
            "dataset": {
                "source": {
                    "columns": [
                        {"name": "col1", "dtype": "StringType"},
                        {"name": "col2", "dtype": "IntegerType"},
                    ]
                },
                "target": {
                    "columns": [
                        {"name": "col1", "standardname": "col1"},
                        {"name": "col2", "standardname": "col2"},
                    ]
                },
            }
        }
        new_config = {
            "dataset": {
                "source": {
                    "columns": [
                        {"name": "col1", "dtype": "StringType"},
                        {"name": "new_col2", "dtype": "IntegerType"},
                    ]
                },
                "target": {
                    "columns": [
                        {"name": "col1", "standardname": "col1"},
                        {"name": "new_col2", "standardname": "col2"},
                    ]
                },
            }
        }

        detector = SchemaChangeDetector(old_config, new_config)
        report = detector.detect_changes()

        renames = [
            c for c in report.source_changes if c.change_type == ChangeType.RENAME
        ]
        assert len(renames) == 1
        assert renames[0].old_value["name"] == "col2"
        assert renames[0].new_value["name"] == "new_col2"

    def test_type_change(self):
        """Test detecting type change."""
        old_config = {
            "dataset": {
                "source": {"columns": [{"name": "col1", "dtype": "StringType"}]},
                "target": {
                    "columns": [
                        {"name": "col1", "standardname": "col1", "dtype": "StringType"}
                    ]
                },
            }
        }
        new_config = {
            "dataset": {
                "source": {"columns": [{"name": "col1", "dtype": "IntegerType"}]},
                "target": {
                    "columns": [
                        {"name": "col1", "standardname": "col1", "dtype": "IntegerType"}
                    ]
                },
            }
        }

        detector = SchemaChangeDetector(old_config, new_config)
        report = detector.detect_changes()

        type_changes = [
            c for c in report.source_changes if c.change_type == ChangeType.TYPE_CHANGE
        ]
        assert len(type_changes) == 1
        assert type_changes[0].old_value["dtype"] == "StringType"
        assert type_changes[0].new_value["dtype"] == "IntegerType"

    def test_reordering(self):
        """Test detecting column reordering."""
        old_config = {
            "dataset": {
                "source": {
                    "columns": [
                        {"name": "col1", "dtype": "StringType"},
                        {"name": "col2", "dtype": "IntegerType"},
                        {"name": "col3", "dtype": "BooleanType"},
                    ]
                },
                "target": {
                    "columns": [
                        {"name": "col1", "standardname": "col1"},
                        {"name": "col2", "standardname": "col2"},
                        {"name": "col3", "standardname": "col3"},
                    ]
                },
            }
        }
        new_config = {
            "dataset": {
                "source": {
                    "columns": [
                        {"name": "col1", "dtype": "StringType"},
                        {"name": "col3", "dtype": "BooleanType"},
                        {"name": "col2", "dtype": "IntegerType"},
                    ]
                },
                "target": {
                    "columns": [
                        {"name": "col1", "standardname": "col1"},
                        {"name": "col3", "standardname": "col3"},
                        {"name": "col2", "standardname": "col2"},
                    ]
                },
            }
        }

        detector = SchemaChangeDetector(old_config, new_config)
        report = detector.detect_changes()

        reorders = [
            c for c in report.source_changes if c.change_type == ChangeType.REORDER
        ]
        assert len(reorders) == 2  # col2 and col3 changed positions

    def test_compound_change(self):
        """Test detecting compound change (rename + type change)."""
        old_config = {
            "dataset": {
                "source": {
                    "columns": [
                        {"name": "col1", "dtype": "StringType"},
                        {"name": "col2", "dtype": "StringType"},
                    ]
                },
                "target": {
                    "columns": [
                        {"name": "col1", "standardname": "col1"},
                        {"name": "col2", "standardname": "col2"},
                    ]
                },
            }
        }
        new_config = {
            "dataset": {
                "source": {
                    "columns": [
                        {"name": "col1", "dtype": "StringType"},
                        {"name": "new_col2", "dtype": "IntegerType"},
                    ]
                },
                "target": {
                    "columns": [
                        {"name": "col1", "standardname": "col1"},
                        {"name": "new_col2", "standardname": "new_col2"},
                    ]
                },
            }
        }

        detector = SchemaChangeDetector(old_config, new_config)
        report = detector.detect_changes()

        compounds = [
            c for c in report.source_changes if c.change_type == ChangeType.COMPOUND
        ]
        assert len(compounds) == 1
        assert compounds[0].impact == ImpactLevel.BREAKING

    def test_standardname_change_detection(self):
        """Test detecting standardname change in target section."""
        old_config = {
            "dataset": {
                "source": {
                    "columns": [
                        {"name": "col1", "dtype": "StringType"},
                        {"name": "col2", "dtype": "IntegerType"},
                    ]
                },
                "target": {
                    "columns": [
                        {"name": "col1", "standardname": "col1"},
                        {"name": "col2", "standardname": "col2"},
                    ]
                },
            }
        }
        new_config = {
            "dataset": {
                "source": {
                    "columns": [
                        {"name": "col1", "dtype": "StringType"},
                        {"name": "col2", "dtype": "IntegerType"},
                    ]
                },
                "target": {
                    "columns": [
                        {"name": "col1", "standardname": "col1"},
                        {"name": "col2", "standardname": "col2_renamed"},
                    ]
                },
            }
        }

        detector = SchemaChangeDetector(old_config, new_config)
        report = detector.detect_changes()

        # Should detect standardname change as a RENAME in target section
        stdname_changes = [
            c for c in report.target_changes if c.change_type == ChangeType.RENAME
        ]
        assert len(stdname_changes) == 1
        assert stdname_changes[0].column_name == "col2"
        assert stdname_changes[0].old_value["standardname"] == "col2"
        assert stdname_changes[0].new_value["standardname"] == "col2_renamed"
        assert stdname_changes[0].impact == ImpactLevel.WARNING
        assert "standardname" in stdname_changes[0].details.lower()

    def test_invalid_mapping_detection(self):
        """Test detecting invalid source-to-target mappings."""
        old_config = {
            "dataset": {
                "source": {
                    "columns": [
                        {"name": "col1", "dtype": "StringType"},
                        {"name": "col2", "dtype": "IntegerType"},
                    ]
                },
                "target": {
                    "columns": [
                        {"name": "col1", "standardname": "col1"},
                        {"name": "col2", "standardname": "col2"},
                    ]
                },
            }
        }
        new_config = {
            "dataset": {
                "source": {"columns": [{"name": "col1", "dtype": "StringType"}]},
                "target": {
                    "columns": [
                        {"name": "col1", "standardname": "col1"},
                        {
                            "name": "col2",
                            "standardname": "col2",
                        },  # Maps to non-existent source
                    ]
                },
            }
        }

        detector = SchemaChangeDetector(old_config, new_config)
        report = detector.detect_changes()

        invalid = [v for v in report.mapping_validations if not v.valid]
        assert len(invalid) == 1
        assert invalid[0].source_column == "col2"
        assert invalid[0].severity == ImpactLevel.BREAKING


class TestReportGeneration:
    """Test report generation."""

    def test_json_report(self):
        """Test JSON report generation."""
        old_config = {
            "dataset": {
                "source": {"columns": [{"name": "col1", "dtype": "StringType"}]},
                "target": {"columns": [{"name": "col1", "standardname": "col1"}]},
            }
        }
        new_config = {
            "dataset": {
                "source": {
                    "columns": [
                        {"name": "col1", "dtype": "StringType"},
                        {"name": "col2", "dtype": "IntegerType"},
                    ]
                },
                "target": {
                    "columns": [
                        {"name": "col1", "standardname": "col1"},
                        {"name": "col2", "standardname": "col2"},
                    ]
                },
            }
        }

        detector = SchemaChangeDetector(old_config, new_config)
        report = detector.detect_changes()
        json_output = ReportGenerator.generate_json_report(report)

        # Verify it's valid JSON
        import json

        data = json.loads(json_output)
        assert "summary" in data
        assert "source_changes" in data
        assert "target_changes" in data
        assert data["summary"]["total_changes"] == 2

    def test_text_report_with_changes(self):
        """Test text report generation with changes."""
        old_config = {
            "dataset": {
                "source": {"columns": [{"name": "col1", "dtype": "StringType"}]},
                "target": {"columns": [{"name": "col1", "standardname": "col1"}]},
            }
        }
        new_config = {
            "dataset": {
                "source": {"columns": [{"name": "col1", "dtype": "IntegerType"}]},
                "target": {"columns": [{"name": "col1", "standardname": "col1"}]},
            }
        }

        detector = SchemaChangeDetector(old_config, new_config)
        report = detector.detect_changes()
        text_output = ReportGenerator.generate_text_report(report)

        # Should contain only the change details, no headers
        assert "TYPE_CHANGE" in text_output.upper()
        assert "Section: source" in text_output
        assert "Impact:" in text_output
        # Should NOT have summary or headers
        assert "SCHEMA CHANGE DETECTION REPORT" not in text_output
        assert "SUMMARY:" not in text_output
        assert "NO schema changes detected" not in text_output

    def test_text_report_no_changes(self):
        """Test text report when no changes detected."""
        old_config = {
            "dataset": {
                "source": {"columns": [{"name": "col1", "dtype": "StringType"}]},
                "target": {"columns": [{"name": "col1", "standardname": "col1"}]},
            }
        }
        # Same config = no changes
        detector = SchemaChangeDetector(old_config, old_config)
        report = detector.detect_changes()
        text_output = ReportGenerator.generate_text_report(report)

        assert text_output == "NO schema changes detected"


class TestIntegration:
    """Integration tests with real files."""

    def test_full_workflow_addition(self):
        """Test full workflow with addition scenario."""
        test_dir = Path(__file__).parent.parent / "test_data"

        old_config = ConfigParser.parse_file(str(test_dir / "old_config.yml"))
        new_config = ConfigParser.parse_file(str(test_dir / "new_config_addition.yml"))

        detector = SchemaChangeDetector(old_config, new_config)
        report = detector.detect_changes()

        assert report.total_changes == 2
        assert any(
            c.change_type == ChangeType.ADDITION and c.column_name == "Column_4"
            for c in report.source_changes
        )

    def test_full_workflow_removal(self):
        """Test full workflow with removal scenario."""
        test_dir = Path(__file__).parent.parent / "test_data"

        old_config = ConfigParser.parse_file(str(test_dir / "old_config.yml"))
        new_config = ConfigParser.parse_file(str(test_dir / "new_config_removal.yml"))

        detector = SchemaChangeDetector(old_config, new_config)
        report = detector.detect_changes()

        assert any(
            c.change_type == ChangeType.REMOVAL and c.column_name == "Column_3"
            for c in report.source_changes
        )
        assert report.breaking_changes > 0

    def test_full_workflow_rename(self):
        """Test full workflow with rename scenario."""
        test_dir = Path(__file__).parent.parent / "test_data"

        old_config = ConfigParser.parse_file(str(test_dir / "old_config.yml"))
        new_config = ConfigParser.parse_file(str(test_dir / "new_config_rename.yml"))

        detector = SchemaChangeDetector(old_config, new_config)
        report = detector.detect_changes()

        assert any(c.change_type == ChangeType.RENAME for c in report.source_changes)

    def test_full_workflow_broken_mapping(self):
        """Test full workflow with broken mapping scenario."""
        test_dir = Path(__file__).parent.parent / "test_data"

        old_config = ConfigParser.parse_file(str(test_dir / "old_config.yml"))
        new_config = ConfigParser.parse_file(
            str(test_dir / "new_config_broken_mapping.yml")
        )

        detector = SchemaChangeDetector(old_config, new_config)
        report = detector.detect_changes()

        invalid_mappings = [v for v in report.mapping_validations if not v.valid]
        assert len(invalid_mappings) == 1
        assert invalid_mappings[0].source_column == "Column_3"


class TestAPI:
    """Test the new simplified API."""

    def test_detect_schema_changes_dict_output(self):
        """Test detect_schema_changes with dict output."""
        from schema_detector import detect_schema_changes

        old_config = {
            "dataset": {
                "source": {"columns": [{"name": "col1", "dtype": "StringType"}]},
                "target": {"columns": [{"name": "col1", "standardname": "col1"}]},
            }
        }
        new_config = {
            "dataset": {
                "source": {
                    "columns": [
                        {"name": "col1", "dtype": "StringType"},
                        {"name": "col2", "dtype": "IntegerType"},
                    ]
                },
                "target": {
                    "columns": [
                        {"name": "col1", "standardname": "col1"},
                        {"name": "col2", "standardname": "col2"},
                    ]
                },
            }
        }

        result = detect_schema_changes(old_config, new_config, output_format="dict")

        assert isinstance(result, dict)
        assert "summary" in result
        assert result["summary"]["total_changes"] == 2

    def test_detect_schema_changes_json_output(self):
        """Test detect_schema_changes with JSON output."""
        from schema_detector import detect_schema_changes
        import json

        old_config = {
            "dataset": {
                "source": {"columns": [{"name": "col1", "dtype": "StringType"}]},
                "target": {"columns": [{"name": "col1", "standardname": "col1"}]},
            }
        }
        new_config = {
            "dataset": {
                "source": {"columns": [{"name": "col1", "dtype": "IntegerType"}]},
                "target": {"columns": [{"name": "col1", "standardname": "col1"}]},
            }
        }

        result = detect_schema_changes(old_config, new_config, output_format="json")

        assert isinstance(result, str)
        data = json.loads(result)
        assert "summary" in data

    def test_detect_schema_changes_text_output_with_changes(self):
        """Test detect_schema_changes with text output when changes exist."""
        from schema_detector import detect_schema_changes

        old_config = {
            "dataset": {
                "source": {"columns": [{"name": "col1", "dtype": "StringType"}]},
                "target": {"columns": [{"name": "col1", "standardname": "col1"}]},
            }
        }
        new_config = {
            "dataset": {
                "source": {"columns": [{"name": "col1", "dtype": "IntegerType"}]},
                "target": {"columns": [{"name": "col1", "standardname": "col1"}]},
            }
        }

        result = detect_schema_changes(old_config, new_config, output_format="text")

        assert isinstance(result, str)
        assert "TYPE_CHANGE" in result.upper()
        assert "Section:" in result
        # Should not have headers when changes exist
        assert "SCHEMA CHANGE DETECTION REPORT" not in result
        assert "NO schema changes detected" not in result

    def test_detect_schema_changes_text_output_no_changes(self):
        """Test detect_schema_changes with text output when no changes."""
        from schema_detector import detect_schema_changes

        old_config = {
            "dataset": {
                "source": {"columns": [{"name": "col1", "dtype": "StringType"}]},
                "target": {"columns": [{"name": "col1", "standardname": "col1"}]},
            }
        }
        # Same config = no changes
        result = detect_schema_changes(old_config, old_config, output_format="text")

        assert isinstance(result, str)
        assert result == "NO schema changes detected"

    def test_detect_schema_changes_file_paths(self):
        """Test detect_schema_changes with file paths."""
        from schema_detector import detect_schema_changes

        test_dir = Path(__file__).parent.parent / "test_data"

        result = detect_schema_changes(
            str(test_dir / "old_config.yml"),
            str(test_dir / "new_config_addition.yml"),
            output_format="dict",
        )

        assert isinstance(result, dict)
        assert result["summary"]["total_changes"] == 2

    def test_detect_schema_changes_invalid_format(self):
        """Test detect_schema_changes with invalid format."""
        from schema_detector import detect_schema_changes

        old_config = {"dataset": {"source": {"columns": []}, "target": {"columns": []}}}
        new_config = {"dataset": {"source": {"columns": []}, "target": {"columns": []}}}

        with pytest.raises(ValueError, match="Unsupported output_format"):
            detect_schema_changes(old_config, new_config, output_format="invalid")

    def test_compare_yaml_files(self):
        """Test compare_yaml_files function."""
        from schema_detector import compare_yaml_files

        test_dir = Path(__file__).parent.parent / "test_data"

        result = compare_yaml_files(
            test_dir / "old_config.yml",
            test_dir / "new_config_removal.yml",
            output_format="dict",
        )

        assert isinstance(result, dict)
        assert result["summary"]["breaking_changes"] > 0

    def test_compare_yaml_files_not_found(self):
        """Test compare_yaml_files with non-existent file."""
        from schema_detector import compare_yaml_files

        with pytest.raises(FileNotFoundError):
            compare_yaml_files("nonexistent.yml", "also_nonexistent.yml")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
