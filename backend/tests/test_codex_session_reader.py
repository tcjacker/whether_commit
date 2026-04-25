import json
from pathlib import Path

from app.services.agent_records.codex_sessions import CodexSessionReader


class FakeConversationCompressor:
    def __init__(self, result: dict | None) -> None:
        self.result = result
        self.seen_payload = None

    def compress(self, payload: dict) -> dict | None:
        self.seen_payload = payload
        return self.result


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_codex_session_reader_collects_workspace_messages_since_commit(tmp_path):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    codex_home = tmp_path / "codex"
    session_path = codex_home / "sessions" / "2026" / "04" / "25" / "rollout.jsonl"
    other_session_path = codex_home / "sessions" / "2026" / "04" / "25" / "other.jsonl"

    _write_jsonl(
        session_path,
        [
            {
                "timestamp": "2026-04-25T09:59:00Z",
                "type": "session_meta",
                "payload": {"id": "sess_1", "cwd": str(workspace)},
            },
            {
                "timestamp": "2026-04-25T09:59:30Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "旧消息不应该进入摘要"}],
                },
            },
            {
                "timestamp": "2026-04-25T10:01:00Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "我要把 overview 重构成 Agentic Change Assessment，以 diff 文件审阅为中心。",
                        }
                    ],
                },
            },
            {
                "timestamp": "2026-04-25T10:02:00Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "我会新增 manifest summary，并接入 Codex session JSONL 作为解释层证据。",
                        }
                    ],
                },
            },
            {
                "timestamp": "2026-04-25T10:03:00Z",
                "type": "response_item",
                "payload": {"type": "function_call", "name": "exec_command"},
            },
        ],
    )
    _write_jsonl(
        other_session_path,
        [
            {
                "timestamp": "2026-04-25T10:01:00Z",
                "type": "session_meta",
                "payload": {"id": "sess_2", "cwd": str(tmp_path / "other")},
            },
            {
                "timestamp": "2026-04-25T10:02:00Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "其他 workspace 的消息"}],
                },
            },
        ],
    )

    evidence = CodexSessionReader(codex_home=codex_home).collect(
        workspace_path=str(workspace),
        since_timestamp=1777111200,
    )

    assert evidence["source"] == "codex_session_jsonl"
    assert evidence["session_count"] == 1
    assert evidence["message_count"] == 2
    assert evidence["session_ids"] == ["sess_1"]
    assert "overview 重构成 Agentic Change Assessment" in evidence["user_messages"][0]
    assert "manifest summary" in evidence["assistant_messages"][0]
    assert all("旧消息" not in text for text in evidence["user_messages"])
    assert all("其他 workspace" not in text for text in evidence["user_messages"])


def test_codex_session_reader_prefers_latest_messages_inside_window(tmp_path):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    codex_home = tmp_path / "codex"
    session_path = codex_home / "sessions" / "2026" / "04" / "25" / "rollout.jsonl"

    rows = [
        {
            "timestamp": "2026-04-25T10:00:00Z",
            "type": "session_meta",
            "payload": {"id": "sess_1", "cwd": str(workspace)},
        }
    ]
    for index in range(6):
        rows.append(
            {
                "timestamp": f"2026-04-25T10:0{index}:10Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": f"第 {index} 条用户目标"}],
                },
            }
        )
    _write_jsonl(session_path, rows)

    evidence = CodexSessionReader(codex_home=codex_home).collect(
        workspace_path=str(workspace),
        since_timestamp=1777111200,
        max_messages=3,
    )

    assert evidence["message_count"] == 3
    assert evidence["user_messages"] == ["第 3 条用户目标", "第 4 条用户目标", "第 5 条用户目标"]


def test_codex_session_reader_chunks_and_classifies_long_conversation(tmp_path):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    codex_home = tmp_path / "codex"
    session_path = codex_home / "sessions" / "2026" / "04" / "25" / "rollout.jsonl"
    rows = [
        {
            "timestamp": "2026-04-25T10:00:00Z",
            "type": "session_meta",
            "payload": {"id": "sess_1", "cwd": str(workspace)},
        },
        {
            "timestamp": "2026-04-25T10:01:00Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "目标是把长对话做分段压缩，并按目标、决策、实现动作分类。"}],
            },
        },
        {
            "timestamp": "2026-04-25T10:02:00Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "我会先写测试，再新增 conversation chunker 和 classified summary。"}],
            },
        },
        {
            "timestamp": "2026-04-25T10:03:00Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "决定先不调用 LLM，保持 rebuild 稳定。"}],
            },
        },
        {
            "timestamp": "2026-04-25T10:04:00Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "已实现 reader 分类，并运行 pytest backend/tests/test_codex_session_reader.py。"}],
            },
        },
    ]
    _write_jsonl(session_path, rows)

    evidence = CodexSessionReader(codex_home=codex_home).collect(
        workspace_path=str(workspace),
        since_timestamp=1777111200,
        max_messages=8,
        chunk_size=2,
    )

    assert len(evidence["conversation_chunks"]) == 2
    assert evidence["conversation_chunks"][0]["message_count"] == 2
    summary = evidence["classified_summary"]
    assert any("分段压缩" in item for item in summary["goals"])
    assert any("不调用 LLM" in item for item in summary["decisions"])
    assert any("conversation chunker" in item for item in summary["implementation_actions"])
    assert any("pytest backend/tests/test_codex_session_reader.py" in item for item in summary["tests_and_verification"])


def test_codex_session_reader_uses_llm_compressor_after_rule_classification(tmp_path):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    codex_home = tmp_path / "codex"
    session_path = codex_home / "sessions" / "2026" / "04" / "25" / "rollout.jsonl"
    _write_jsonl(
        session_path,
        [
            {
                "timestamp": "2026-04-25T10:00:00Z",
                "type": "session_meta",
                "payload": {"id": "sess_1", "cwd": str(workspace)},
            },
            {
                "timestamp": "2026-04-25T10:01:00Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "目标是用 Codex 做二次压缩。"}],
                },
            },
        ],
    )
    compressor = FakeConversationCompressor(
        {
            "goals": ["LLM refined goal"],
            "decisions": ["LLM refined decision"],
            "implementation_actions": ["LLM refined action"],
            "tests_and_verification": ["LLM refined test"],
        }
    )

    evidence = CodexSessionReader(
        codex_home=codex_home,
        llm_compressor=compressor,
    ).collect(
        workspace_path=str(workspace),
        since_timestamp=1777111200,
    )

    assert compressor.seen_payload["rule_summary"]["goals"]
    assert evidence["classified_summary"]["goals"] == ["LLM refined goal"]
    assert evidence["classified_summary_source"] == "codex_llm"


def test_codex_session_reader_falls_back_when_llm_compressor_fails(tmp_path):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    codex_home = tmp_path / "codex"
    session_path = codex_home / "sessions" / "2026" / "04" / "25" / "rollout.jsonl"
    _write_jsonl(
        session_path,
        [
            {
                "timestamp": "2026-04-25T10:00:00Z",
                "type": "session_meta",
                "payload": {"id": "sess_1", "cwd": str(workspace)},
            },
            {
                "timestamp": "2026-04-25T10:01:00Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "目标是保留规则 fallback。"}],
                },
            },
        ],
    )

    evidence = CodexSessionReader(
        codex_home=codex_home,
        llm_compressor=FakeConversationCompressor(None),
    ).collect(
        workspace_path=str(workspace),
        since_timestamp=1777111200,
    )

    assert any("规则 fallback" in item for item in evidence["classified_summary"]["goals"])
    assert evidence["classified_summary_source"] == "rules"
