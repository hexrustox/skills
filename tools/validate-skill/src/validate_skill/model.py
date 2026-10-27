from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    message: str
    location: str


@dataclass
class SkillResult:
    path: Path
    findings: list[Finding] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(finding.severity == "error" for finding in self.findings)

    @property
    def warning_count(self) -> int:
        return sum(finding.severity == "warning" for finding in self.findings)
