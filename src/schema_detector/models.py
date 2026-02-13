"""Schema Change Detector - Core models and data structures."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class ChangeType(Enum):
    """Types of schema changes."""

    ADDITION = "addition"
    REMOVAL = "removal"
    RENAME = "rename"
    TYPE_CHANGE = "type_change"
    REORDER = "reorder"
    COMPOUND = "compound"


class ImpactLevel(Enum):
    """Impact levels for changes."""

    BREAKING = "breaking"
    WARNING = "warning"
    COMPATIBLE = "compatible"


@dataclass
class ColumnNode:
    """Represents a column in source or target."""

    name: str
    dtype: Optional[str]
    position: int
    standardname: Optional[str] = None
    description: Optional[str] = None
    tags: Any = None

    @property
    def effective_name(self) -> str:
        """Return standardname if exists, otherwise name."""
        return self.standardname if self.standardname else self.name

    @property
    def fingerprint(self) -> str:
        """Generate unique fingerprint based on name and type."""
        return f"{self.name}:{self.dtype or 'unknown'}"

    @property
    def type_fingerprint(self) -> str:
        """Generate fingerprint based on type only."""
        return self.dtype or "unknown"


@dataclass
class ChangeEvent:
    """Represents a single schema change."""

    change_type: ChangeType
    section: str  # 'source' or 'target'
    column_name: str
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    impact: ImpactLevel = ImpactLevel.COMPATIBLE
    details: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "change_type": self.change_type.value,
            "section": self.section,
            "column_name": self.column_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "impact": self.impact.value,
            "details": self.details,
        }


@dataclass
class MappingValidation:
    """Validation result for source-to-target mapping."""

    valid: bool
    source_column: str
    target_column: str
    issue: Optional[str] = None
    severity: ImpactLevel = ImpactLevel.COMPATIBLE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "source_column": self.source_column,
            "target_column": self.target_column,
            "issue": self.issue,
            "severity": self.severity.value,
        }


@dataclass
class SchemaDiffReport:
    """Complete schema difference report."""

    source_changes: List[ChangeEvent] = field(default_factory=list)
    target_changes: List[ChangeEvent] = field(default_factory=list)
    mapping_validations: List[MappingValidation] = field(default_factory=list)

    @property
    def total_changes(self) -> int:
        return len(self.source_changes) + len(self.target_changes)

    @property
    def breaking_changes(self) -> int:
        return sum(
            1
            for c in self.source_changes + self.target_changes
            if c.impact == ImpactLevel.BREAKING
        )

    @property
    def warnings(self) -> int:
        return sum(
            1
            for c in self.source_changes + self.target_changes
            if c.impact == ImpactLevel.WARNING
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "summary": {
                "total_changes": self.total_changes,
                "breaking_changes": self.breaking_changes,
                "warnings": self.warnings,
                "compatible_changes": self.total_changes
                - self.breaking_changes
                - self.warnings,
            },
            "source_changes": [c.to_dict() for c in self.source_changes],
            "target_changes": [c.to_dict() for c in self.target_changes],
            "mapping_validations": [m.to_dict() for m in self.mapping_validations],
        }
