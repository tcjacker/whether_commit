from __future__ import annotations

from typing import Any, Dict, List


class AgentLogRecordAdapter:
    """
    Normalizes captured Codex / Claude Code activity evidence into AgentChangeRecord objects.

    The raw log scan happens in ChangeImpactAdapter so assessment building never needs to
    read user-local history directly. This adapter only turns the already matched,
    file-scoped evidence into structured records.
    """

    SOURCE_EVIDENCE = {
        "codex": "codex_jsonl",
        "claude_code": "claude_hooks",
    }

    def build(
        self,
        *,
        workspace_snapshot_id: str,
        changed_files: List[str],
        agent_activity_evidence: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}
        changed_file_set = set(changed_files)

        for item in agent_activity_evidence:
            if not isinstance(item, dict):
                continue
            source = str(item.get("source") or "agent_log")
            summary = " ".join(str(item.get("summary") or "").split())
            related_files = [
                path for path in item.get("related_files", [])
                if isinstance(path, str) and path in changed_file_set
            ]
            if not summary or not related_files:
                continue

            bucket = grouped.setdefault(
                source,
                {
                    "summaries": [],
                    "files": [],
                },
            )
            if summary not in bucket["summaries"]:
                bucket["summaries"].append(summary)
            for path in related_files:
                if path not in bucket["files"]:
                    bucket["files"].append(path)

        records: List[Dict[str, Any]] = []
        for source in sorted(grouped):
            bucket = grouped[source]
            summaries = bucket["summaries"][:5]
            files = bucket["files"]
            evidence_source = self.SOURCE_EVIDENCE.get(source, "agent_log")
            records.append(
                {
                    "record_id": f"acr_{source}_{workspace_snapshot_id}",
                    "source": source,
                    "capture_level": "partial",
                    "evidence_sources": [evidence_source, "agent_activity_evidence"],
                    "confidence": {
                        "files_touched": "high",
                        "commands_run": "low",
                        "reasoning_summary": "medium",
                        "tests_run": "low",
                    },
                    "task_summary": summaries[0],
                    "declared_intent": summaries[0],
                    "reasoning_summary": " | ".join(summaries),
                    "files_touched": files,
                    "commands_run": [],
                    "tests_run": [],
                    "known_limitations": [
                        "Record was inferred from matched local agent log text; command events may be incomplete."
                    ],
                    "raw_log_ref": "",
                }
            )
        return records
