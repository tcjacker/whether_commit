from __future__ import annotations

from typing import Any, Dict, List


class GitDiffOnlyAdapter:
    def build(self, *, workspace_snapshot_id: str, changed_files: List[str]) -> Dict[str, Any]:
        files_touched = list(dict.fromkeys(changed_files))
        return {
            "record_id": f"acr_git_diff_{workspace_snapshot_id}",
            "source": "git_diff",
            "capture_level": "diff_only",
            "evidence_sources": ["git_diff", "git_status"],
            "confidence": {
                "files_touched": "high",
                "commands_run": "low",
                "reasoning_summary": "low",
                "tests_run": "low",
            },
            "task_summary": "Workspace contains uncommitted git changes.",
            "declared_intent": "",
            "reasoning_summary": "",
            "files_touched": files_touched,
            "commands_run": [],
            "tests_run": [],
            "known_limitations": ["No structured coding-agent log was available."],
            "raw_log_ref": "",
        }
