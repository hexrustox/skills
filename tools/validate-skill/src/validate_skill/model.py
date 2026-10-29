from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import NewType


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


Rule = NewType("Rule", str)
Location = NewType("Location", str)


@dataclass(frozen=True)
class Finding:
    rule: Rule
    severity: Severity
    message: str
    location: Location

    @classmethod
    def error(cls, rule: str, message: str, location: str) -> "Finding":
        return cls(Rule(rule), Severity.ERROR, message, Location(location))

    @classmethod
    def warning(cls, rule: str, message: str, location: str) -> "Finding":
        return cls(Rule(rule), Severity.WARNING, message, Location(location))


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


@dataclass(frozen=True)
class TargetFailure:
    path: Path
    message: str


@dataclass(frozen=True)
class Run:
    results: tuple[SkillResult, ...] = field(default_factory=tuple)
    failures: tuple[TargetFailure, ...] = field(default_factory=tuple)

    @property
    def exit_code(self) -> int:
        if self.failures:
            return 2
        return 1 if any(result.error_count for result in self.results) else 0
