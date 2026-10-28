import posixpath
import re
from typing import NamedTuple

_MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]*\]\(((?:[^()\n]|\([^()\n]*\))*)\)")
_MARKDOWN_REFERENCE_PATTERN = re.compile(
    r"^[ \t]{0,3}\[[^\]]+\]:[ \t]*(<[^>]*>|\S+)", re.MULTILINE
)
_INLINE_CODE_PATTERN = re.compile(r"`([^`\n]+)`")
_REFERENCE_DIRECTORIES = frozenset({"scripts", "references", "assets"})
_URL_SCHEME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


class Reference(NamedTuple):
    path: str
    line: int


def _normalize_path(value: str) -> str:
    return posixpath.normpath(value.replace("\\", "/"))


def _reference_path(target: str) -> str | None:
    candidate = target.strip()
    if not candidate:
        return None
    if candidate.startswith("<") and candidate.endswith(">"):
        candidate = candidate[1:-1].strip()
    else:
        parts = candidate.split()
        if not parts:
            return None
        candidate = parts[0]

    candidate = candidate.split("#", 1)[0].split("?", 1)[0].strip()
    if not candidate:
        return None
    if candidate.startswith(("#", "/", "~", "\\")):
        return None
    if _URL_SCHEME_PATTERN.match(candidate):
        return None

    normalized = _normalize_path(candidate)
    first_part = normalized.split("/", 1)[0]
    if first_part not in _REFERENCE_DIRECTORIES:
        return None
    return normalized


def _line_number(body: str, offset: int) -> int:
    return body.count("\n", 0, offset) + 1


def _mask_line(line: str) -> str:
    if line.endswith("\n"):
        return " " * (len(line) - 1) + "\n"
    return " " * len(line)


def _mask_fenced_code(body: str) -> str:
    masked: list[str] = []
    in_fence = False
    for line in body.splitlines(keepends=True):
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            masked.append(_mask_line(line))
        elif in_fence:
            masked.append(_mask_line(line))
        else:
            masked.append(line)
    return "".join(masked)


def scan_references(body: str) -> list[Reference]:
    masked = _mask_fenced_code(body)
    matches: list[tuple[int, str]] = []

    for pattern in (_MARKDOWN_LINK_PATTERN, _MARKDOWN_REFERENCE_PATTERN):
        for match in pattern.finditer(masked):
            normalized = _reference_path(match.group(1))
            if normalized is not None:
                matches.append((match.start(), normalized))

    for match in _INLINE_CODE_PATTERN.finditer(masked):
        for token in match.group(1).split():
            normalized = _reference_path(token)
            if normalized is not None:
                matches.append((match.start(), normalized))

    matches.sort(key=lambda item: item[0])
    return [Reference(path, _line_number(body, offset)) for offset, path in matches]
