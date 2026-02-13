"""Report generation module for schema changes."""

import json
from typing import Dict, Any
from schema_detector.models import (
    SchemaDiffReport,
    ChangeEvent,
    ChangeType,
    ImpactLevel,
)


class ReportGenerator:
    """Generate reports in various formats."""

    @staticmethod
    def generate_json_report(report: SchemaDiffReport) -> str:
        """Generate JSON report."""
        return json.dumps(report.to_dict(), indent=2)

    @staticmethod
    def generate_text_report(report: SchemaDiffReport) -> str:
        """
        Generate plain text report with schema changes only.

        Returns:
            "NO schema changes detected" if no changes found
            Otherwise returns only the schema changes without headers or summaries
        """
        # If no changes, return simple message
        if report.total_changes == 0:
            return "NO schema changes detected"

        lines = []

        # Source Changes only
        if report.source_changes:
            for change in report.source_changes:
                impact_label = {
                    ImpactLevel.BREAKING: "BREAKING",
                    ImpactLevel.WARNING: "WARNING",
                    ImpactLevel.COMPATIBLE: "COMPATIBLE",
                }.get(change.impact, "UNKNOWN")

                lines.append(f"Change: {change.change_type.value.upper()}")
                lines.append(f"  Section: source")
                lines.append(f"  Column: {change.column_name}")
                lines.append(f"  Impact: {impact_label}")
                if change.details:
                    lines.append(f"  Details: {change.details}")
                if change.old_value:
                    lines.append(f"  Old: {change.old_value}")
                if change.new_value:
                    lines.append(f"  New: {change.new_value}")
                lines.append("")

        # Target Changes only
        if report.target_changes:
            for change in report.target_changes:
                impact_label = {
                    ImpactLevel.BREAKING: "BREAKING",
                    ImpactLevel.WARNING: "WARNING",
                    ImpactLevel.COMPATIBLE: "COMPATIBLE",
                }.get(change.impact, "UNKNOWN")

                lines.append(f"Change: {change.change_type.value.upper()}")
                lines.append(f"  Section: target")
                lines.append(f"  Column: {change.column_name}")
                lines.append(f"  Impact: {impact_label}")
                if change.details:
                    lines.append(f"  Details: {change.details}")
                if change.old_value:
                    lines.append(f"  Old: {change.old_value}")
                if change.new_value:
                    lines.append(f"  New: {change.new_value}")
                lines.append("")

        return "\n".join(lines).strip()

    @staticmethod
    def _generate_recommendations(report: SchemaDiffReport) -> list:
        """Generate actionable recommendations."""
        recommendations = []

        if report.breaking_changes > 0:
            breaking = [
                c
                for c in report.source_changes + report.target_changes
                if c.impact == ImpactLevel.BREAKING
            ]

            # Group by section
            source_breaking = [c for c in breaking if c.section == "source"]
            target_breaking = [c for c in breaking if c.section == "target"]

            if source_breaking:
                cols = [c.column_name for c in source_breaking]
                recommendations.append(
                    f"CRITICAL: Breaking changes in source schema for columns: {', '.join(cols)}. "
                    "Review and update source-to-target mappings before deployment."
                )

            if target_breaking:
                cols = [c.column_name for c in target_breaking]
                recommendations.append(
                    f"CRITICAL: Breaking changes in target schema for columns: {', '.join(cols)}. "
                    "Update downstream consumers and ETL logic before deployment."
                )

        # Check for invalid mappings
        invalid_mappings = [v for v in report.mapping_validations if not v.valid]
        if invalid_mappings:
            recommendations.append(
                f"ACTION REQUIRED: {len(invalid_mappings)} source-to-target mappings are invalid. "
                "Update target.column 'name' fields to reference existing source columns."
            )

        # Check for renames
        renames = [
            c
            for c in report.source_changes + report.target_changes
            if c.change_type == ChangeType.RENAME
        ]
        if renames:
            recommendations.append(
                f"NOTE: {len(renames)} column(s) renamed. Ensure all downstream references and documentation are updated."
            )

        if not recommendations:
            recommendations.append("No action required. All changes are compatible.")

        return recommendations
