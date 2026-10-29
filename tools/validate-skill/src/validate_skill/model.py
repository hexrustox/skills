from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: Severity
    message: str
    location: str


@dataclass
class SkillResult:
    path: Path
    findings: list[Finding] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(finding.severity is Severity.ERROR for finding in self.findings)

    @property
    def warning_count(self) -> int:
        return sum(finding.severity is Severity.WARNING for finding in self.findings)
