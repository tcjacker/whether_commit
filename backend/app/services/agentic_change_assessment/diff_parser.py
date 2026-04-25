from __future__ import annotations

import re
from typing import Any, Dict, List

from app.services.agentic_change_assessment.id_utils import fingerprint_for_text


HUNK_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_lines>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_lines>\d+))? @@"
)


def _line_type(raw_line: str) -> str:
    if raw_line.startswith("+"):
        return "add"
    if raw_line.startswith("-"):
        return "remove"
    if raw_line.startswith("@@"):
        return "header"
    return "context"


def _line_content(raw_line: str) -> str:
    if raw_line.startswith(("+", "-", " ")):
        return raw_line[1:]
    return raw_line


def parse_unified_diff_hunks(diff_text: str) -> List[Dict[str, Any]]:
    hunks: List[Dict[str, Any]] = []
    current: Dict[str, Any] | None = None
    raw_hunk_lines: List[str] = []

    def flush() -> None:
        nonlocal current, raw_hunk_lines
        if current is None:
            return
        current["hunk_fingerprint"] = fingerprint_for_text("\n".join(raw_hunk_lines))
        current["hunk_id"] = f"hunk_{len(hunks) + 1:03d}"
        hunks.append(current)
        current = None
        raw_hunk_lines = []

    for raw_line in diff_text.splitlines():
        match = HUNK_RE.match(raw_line)
        if match:
            flush()
            old_lines = int(match.group("old_lines") or "1")
            new_lines = int(match.group("new_lines") or "1")
            current = {
                "hunk_id": "",
                "old_start": int(match.group("old_start")),
                "old_lines": old_lines,
                "new_start": int(match.group("new_start")),
                "new_lines": new_lines,
                "hunk_fingerprint": "",
                "lines": [{"type": "header", "content": raw_line}],
            }
            raw_hunk_lines = [raw_line]
            continue

        if current is None:
            continue
        if raw_line.startswith(("--- ", "+++ ")):
            continue
        raw_hunk_lines.append(raw_line)
        current["lines"].append({"type": _line_type(raw_line), "content": _line_content(raw_line)})

    flush()
    return hunks
