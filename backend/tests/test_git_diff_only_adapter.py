from app.services.agent_records.git_diff_only import GitDiffOnlyAdapter
from app.services.agentic_change_assessment.diff_parser import parse_unified_diff_hunks
from app.services.agentic_change_assessment.id_utils import file_id_for_path


def test_git_diff_only_adapter_builds_low_fidelity_record():
    adapter = GitDiffOnlyAdapter()
    record = adapter.build(
        workspace_snapshot_id="ws_1",
        changed_files=["backend/app/main.py", "frontend/src/App.tsx"],
    )

    assert record["record_id"] == "acr_git_diff_ws_1"
    assert record["source"] == "git_diff"
    assert record["capture_level"] == "diff_only"
    assert record["evidence_sources"] == ["git_diff", "git_status"]
    assert record["confidence"]["files_touched"] == "high"
    assert record["confidence"]["commands_run"] == "low"
    assert record["files_touched"] == ["backend/app/main.py", "frontend/src/App.tsx"]


def test_file_id_for_path_is_stable_and_path_safe():
    file_id = file_id_for_path("backend/app/main.py")

    assert file_id.startswith("cf_")
    assert "/" not in file_id


def test_parse_unified_diff_hunks_extracts_hunk_metadata_and_lines():
    diff = """diff --git a/backend/app/main.py b/backend/app/main.py
--- a/backend/app/main.py
+++ b/backend/app/main.py
@@ -1,2 +1,3 @@
 old context
-old line
+new line
+another line
"""

    hunks = parse_unified_diff_hunks(diff)

    assert len(hunks) == 1
    assert hunks[0]["old_start"] == 1
    assert hunks[0]["new_lines"] == 3
    assert hunks[0]["lines"][1] == {"type": "context", "content": "old context"}
    assert hunks[0]["lines"][2] == {"type": "remove", "content": "old line"}
    assert hunks[0]["lines"][3] == {"type": "add", "content": "new line"}
