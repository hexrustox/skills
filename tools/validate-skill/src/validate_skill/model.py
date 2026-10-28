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

    def as_text(self) -> str:
        return (
            f"  {self.severity.value} {self.rule}: {self.message} "
            f"[{self.location}]"
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity.value,
            "rule": self.rule,
            "message": self.message,
            "location": self.location,
        }


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
