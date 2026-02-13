"""Core Schema Change Detection Algorithm."""

from typing import List, Dict, Set, Tuple, Optional, Any
from collections import defaultdict
from schema_detector.models import (
    ColumnNode,
    ChangeEvent,
    ChangeType,
    ImpactLevel,
    MappingValidation,
    SchemaDiffReport,
)


class SchemaChangeDetector:
    """Detect schema changes between old and new configurations."""

    def __init__(self, old_config: Dict[str, Any], new_config: Dict[str, Any]):
        self.old_config = old_config
        self.new_config = new_config
        self.report = SchemaDiffReport()

    def detect_changes(self) -> SchemaDiffReport:
        """Run full change detection and return report."""
        from .parser import ConfigParser

        # Extract columns from both configs
        old_source = ConfigParser.extract_source_columns(self.old_config)
        new_source = ConfigParser.extract_source_columns(self.new_config)
        old_target = ConfigParser.extract_target_columns(self.old_config)
        new_target = ConfigParser.extract_target_columns(self.new_config)

        # Detect changes in source section
        self.report.source_changes = self._detect_section_changes(
            old_source, new_source, "source"
        )

        # Detect changes in target section
        self.report.target_changes = self._detect_section_changes(
            old_target, new_target, "target"
        )

        # Validate mappings
        self.report.mapping_validations = self._validate_mappings(
            new_source, new_target
        )

        return self.report

    def _detect_section_changes(
        self, old_cols: List[ColumnNode], new_cols: List[ColumnNode], section: str
    ) -> List[ChangeEvent]:
        """Detect all changes within a section (source or target)."""
        changes = []

        # Build fingerprint mappings
        old_by_fingerprint = {col.fingerprint: col for col in old_cols}
        new_by_fingerprint = {col.fingerprint: col for col in new_cols}

        old_by_name = {col.name: col for col in old_cols}
        new_by_name = {col.name: col for col in new_cols}

        # Track matched columns
        old_matched = set()
        new_matched = set()

        # Step 1: Find exact matches (no change)
        for fp, old_col in old_by_fingerprint.items():
            if fp in new_by_fingerprint:
                new_col = new_by_fingerprint[fp]
                old_matched.add(old_col.name)
                new_matched.add(new_col.name)

                # Check for reordering
                if old_col.position != new_col.position:
                    changes.append(
                        self._create_reorder_event(section, old_col, new_col)
                    )

                # Check for standardname changes (target section only)
                if section == "target":
                    if old_col.standardname != new_col.standardname:
                        changes.append(
                            self._create_standardname_change_event(old_col, new_col)
                        )

        # Step 2: Find renames (same type, different name, same position)
        for old_col in old_cols:
            if old_col.name in old_matched:
                continue

            # Look for column with same type at same or similar position
            for new_col in new_cols:
                if new_col.name in new_matched:
                    continue

                if (
                    old_col.dtype == new_col.dtype
                    and abs(old_col.position - new_col.position) <= 1
                ):
                    changes.append(self._create_rename_event(section, old_col, new_col))
                    old_matched.add(old_col.name)
                    new_matched.add(new_col.name)
                    break

        # Step 3: Find type changes (same name, different type)
        for old_col in old_cols:
            if old_col.name in old_matched:
                continue

            if old_col.name in new_by_name:
                new_col = new_by_name[old_col.name]
                if new_col.name not in new_matched:
                    changes.append(
                        self._create_type_change_event(section, old_col, new_col)
                    )
                    old_matched.add(old_col.name)
                    new_matched.add(new_col.name)

        # Step 4: Remaining columns are additions or removals
        for old_col in old_cols:
            if old_col.name not in old_matched:
                changes.append(self._create_removal_event(section, old_col))

        for new_col in new_cols:
            if new_col.name not in new_matched:
                changes.append(self._create_addition_event(section, new_col))

        # Step 5: Detect compound changes
        changes = self._detect_compound_changes(changes, old_cols, new_cols, section)

        return sorted(changes, key=lambda x: x.column_name)

    def _detect_compound_changes(
        self,
        changes: List[ChangeEvent],
        old_cols: List[ColumnNode],
        new_cols: List[ColumnNode],
        section: str,
    ) -> List[ChangeEvent]:
        """Detect and merge compound changes."""
        # Group changes by related columns
        removal_names = {
            c.column_name for c in changes if c.change_type == ChangeType.REMOVAL
        }
        addition_names = {
            c.column_name for c in changes if c.change_type == ChangeType.ADDITION
        }

        compound_changes = []
        processed = set()

        for removal in [c for c in changes if c.change_type == ChangeType.REMOVAL]:
            # Look for a nearby addition that might be a compound change
            old_col = next((c for c in old_cols if c.name == removal.column_name), None)

            for addition in [
                c for c in changes if c.change_type == ChangeType.ADDITION
            ]:
                if addition.column_name in processed:
                    continue

                new_col = next(
                    (c for c in new_cols if c.name == addition.column_name), None
                )

                # Check if position is similar (indicates possible rename+type change)
                if old_col and new_col:
                    pos_diff = abs(old_col.position - new_col.position)

                    if pos_diff <= 1:
                        # This is likely a compound change (rename + type change)
                        compound_changes.append(
                            ChangeEvent(
                                change_type=ChangeType.COMPOUND,
                                section=section,
                                column_name=f"{removal.column_name} -> {addition.column_name}",
                                old_value={
                                    "name": removal.column_name,
                                    "dtype": removal.old_value.get("dtype")
                                    if removal.old_value
                                    else None,
                                    "position": old_col.position,
                                },
                                new_value={
                                    "name": addition.column_name,
                                    "dtype": addition.new_value.get("dtype")
                                    if addition.new_value
                                    else None,
                                    "position": new_col.position,
                                },
                                impact=ImpactLevel.BREAKING,
                                details=f"Column '{removal.column_name}' appears to have been renamed to "
                                f"'{addition.column_name}' with type change from "
                                f"{removal.old_value.get('dtype') if removal.old_value else 'unknown'} to "
                                f"{addition.new_value.get('dtype') if addition.new_value else 'unknown'}",
                            )
                        )
                        processed.add(addition.column_name)
                        processed.add(removal.column_name)
                        break

        # Filter out individual changes that were merged into compound changes
        filtered_changes = [
            c
            for c in changes
            if c.column_name not in processed
            or c.change_type not in [ChangeType.REMOVAL, ChangeType.ADDITION]
        ]

        return filtered_changes + compound_changes

    def _create_addition_event(self, section: str, col: ColumnNode) -> ChangeEvent:
        """Create addition change event."""
        return ChangeEvent(
            change_type=ChangeType.ADDITION,
            section=section,
            column_name=col.name,
            new_value={
                "name": col.name,
                "dtype": col.dtype,
                "position": col.position,
                "standardname": col.standardname,
            },
            impact=ImpactLevel.COMPATIBLE,
            details=f"New column '{col.name}' added at position {col.position}",
        )

    def _create_removal_event(self, section: str, col: ColumnNode) -> ChangeEvent:
        """Create removal change event."""
        impact = ImpactLevel.BREAKING if section == "source" else ImpactLevel.WARNING
        return ChangeEvent(
            change_type=ChangeType.REMOVAL,
            section=section,
            column_name=col.name,
            old_value={
                "name": col.name,
                "dtype": col.dtype,
                "position": col.position,
                "standardname": col.standardname,
            },
            impact=impact,
            details=f"Column '{col.name}' removed",
        )

    def _create_rename_event(
        self, section: str, old_col: ColumnNode, new_col: ColumnNode
    ) -> ChangeEvent:
        """Create rename change event."""
        return ChangeEvent(
            change_type=ChangeType.RENAME,
            section=section,
            column_name=new_col.name,
            old_value={"name": old_col.name},
            new_value={"name": new_col.name},
            impact=ImpactLevel.WARNING,
            details=f"Column renamed from '{old_col.name}' to '{new_col.name}'",
        )

    def _create_type_change_event(
        self, section: str, old_col: ColumnNode, new_col: ColumnNode
    ) -> ChangeEvent:
        """Create type change event."""
        impact = ImpactLevel.BREAKING if section == "target" else ImpactLevel.WARNING
        return ChangeEvent(
            change_type=ChangeType.TYPE_CHANGE,
            section=section,
            column_name=new_col.name,
            old_value={"dtype": old_col.dtype},
            new_value={"dtype": new_col.dtype},
            impact=impact,
            details=f"Type changed from '{old_col.dtype}' to '{new_col.dtype}'",
        )

    def _create_reorder_event(
        self, section: str, old_col: ColumnNode, new_col: ColumnNode
    ) -> ChangeEvent:
        """Create reorder change event."""
        return ChangeEvent(
            change_type=ChangeType.REORDER,
            section=section,
            column_name=new_col.name,
            old_value={"position": old_col.position},
            new_value={"position": new_col.position},
            impact=ImpactLevel.WARNING,
            details=f"Position changed from {old_col.position} to {new_col.position}",
        )

    def _create_standardname_change_event(
        self, old_col: ColumnNode, new_col: ColumnNode
    ) -> ChangeEvent:
        """Create standardname change event for target section."""
        return ChangeEvent(
            change_type=ChangeType.RENAME,
            section="target",
            column_name=new_col.name,
            old_value={"standardname": old_col.standardname},
            new_value={"standardname": new_col.standardname},
            impact=ImpactLevel.WARNING,
            details=f"Silver column name (standardname) changed from '{old_col.standardname}' to '{new_col.standardname}' for source column '{new_col.name}'",
        )

    def _validate_mappings(
        self, source_cols: List[ColumnNode], target_cols: List[ColumnNode]
    ) -> List[MappingValidation]:
        """Validate that source-to-target mappings are still valid."""
        validations = []
        source_by_name = {col.name: col for col in source_cols}

        for target_col in target_cols:
            # Target 'name' field maps to source column
            source_col_name = target_col.name

            if source_col_name not in source_by_name:
                validations.append(
                    MappingValidation(
                        valid=False,
                        source_column=source_col_name,
                        target_column=target_col.effective_name,
                        issue=f"Source column '{source_col_name}' not found but mapped to target",
                        severity=ImpactLevel.BREAKING,
                    )
                )
            else:
                validations.append(
                    MappingValidation(
                        valid=True,
                        source_column=source_col_name,
                        target_column=target_col.effective_name,
                    )
                )

        return validations
