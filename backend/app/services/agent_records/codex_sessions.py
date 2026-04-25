from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Protocol


class ConversationCompressor(Protocol):
    def compress(self, payload: Dict[str, Any]) -> Dict[str, List[str]] | None:
        """Return a classified summary or None when unavailable."""


class LocalCodexConversationCompressor:
    """
    Uses the local Codex CLI to refine deterministic conversation classification.
    No token, provider, or base URL configuration is accepted here.
    """

    def __init__(
        self,
        *,
        timeout_seconds: int = 90,
        command: str = "codex",
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.command = command

    def compress(self, payload: Dict[str, Any]) -> Dict[str, List[str]] | None:
        output_path = self._new_output_path()
        try:
            completed = subprocess.run(
                self._command(self._build_prompt(payload), output_path),
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            self._remove_output_path(output_path)
            return None

        if completed.returncode != 0:
            self._remove_output_path(output_path)
            return None

        last_message = self._read_output_path(output_path)
        self._remove_output_path(output_path)
        parsed = self._parse_json_object(last_message) or self._parse_json_object(completed.stdout)
        if not isinstance(parsed, dict):
            return None
        return self._normalize(parsed)

    def _command(self, prompt: str, output_path: str) -> List[str]:
        return [
            self.command,
            "--ask-for-approval",
            "never",
            "exec",
            "--sandbox",
            "read-only",
            "--color",
            "never",
            "--ephemeral",
            "--output-last-message",
            output_path,
            prompt,
        ]

    def _build_prompt(self, payload: Dict[str, Any]) -> str:
        compact_payload = {
            "rule_summary": payload.get("rule_summary", {}),
            "conversation_chunks": payload.get("conversation_chunks", [])[:8],
        }
        return (
            "你是 Agentic Change Assessment 的会话摘要压缩器。\n"
            "任务：基于 Codex session JSONL 中的 user/assistant 对话片段，做二次压缩和分类。\n"
            "规则：\n"
            "- 只使用输入里的对话证据，不要编造。\n"
            "- 输出简体中文。\n"
            "- 保留用户目标、关键产品/技术决策、Codex 实现动作、测试/验证动作。\n"
            "- 去掉过程性闲聊、重复状态更新、approval/telemetry 噪声。\n"
            "- 每类最多 5 条，每条 1 句话。\n"
            "Return exactly one JSON object and no markdown.\n"
            "JSON schema:\n"
            "{\n"
            '  "goals": [],\n'
            '  "decisions": [],\n'
            '  "implementation_actions": [],\n'
            '  "tests_and_verification": []\n'
            "}\n"
            "Input:\n"
            f"{json.dumps(compact_payload, ensure_ascii=False, indent=2)}"
        )

    def _parse_json_object(self, output: str) -> Dict[str, Any] | None:
        text = output.strip()
        if not text:
            return None
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return parsed
        decoder = json.JSONDecoder()
        candidates: List[Dict[str, Any]] = []
        for match in re.finditer(r"\{", text):
            try:
                candidate, _ = decoder.raw_decode(text[match.start():])
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict):
                candidates.append(candidate)
        return candidates[-1] if candidates else None

    def _normalize(self, parsed: Dict[str, Any]) -> Dict[str, List[str]]:
        return {
            key: self._string_list(parsed.get(key))[:5]
            for key in ("goals", "decisions", "implementation_actions", "tests_and_verification")
        }

    def _string_list(self, value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip()[:260] for item in value if str(item).strip()]

    def _new_output_path(self) -> str:
        handle = tempfile.NamedTemporaryFile(prefix="codex_conversation_summary_", suffix=".txt", delete=False)
        handle.close()
        return handle.name

    def _read_output_path(self, output_path: str) -> str:
        try:
            with open(output_path, "r", encoding="utf-8") as file:
                return file.read()
        except OSError:
            return ""

    def _remove_output_path(self, output_path: str) -> None:
        try:
            os.unlink(output_path)
        except OSError:
            pass


class CodexSessionReader:
    """
    Reads Codex Desktop session JSONL files and extracts human-readable
    user/assistant conversation snippets for the current workspace.
    """

    def __init__(
        self,
        codex_home: Path | None = None,
        llm_compressor: ConversationCompressor | None = None,
    ) -> None:
        self.codex_home = codex_home or Path.home() / ".codex"
        self.llm_compressor = llm_compressor or LocalCodexConversationCompressor()

    def collect(
        self,
        *,
        workspace_path: str,
        since_timestamp: int | None,
        max_messages: int = 24,
        chunk_size: int = 6,
    ) -> Dict[str, Any]:
        workspace = str(Path(workspace_path).resolve())
        user_messages: List[str] = []
        assistant_messages: List[str] = []
        session_ids: List[str] = []
        source_paths: List[str] = []

        for session_path in self._session_paths(since_timestamp):
            parsed = self._read_session(
                session_path=session_path,
                workspace_path=workspace,
                since_timestamp=since_timestamp,
                remaining=max_messages - len(user_messages) - len(assistant_messages),
            )
            if not parsed["messages"]:
                continue
            if parsed["session_id"] and parsed["session_id"] not in session_ids:
                session_ids.append(parsed["session_id"])
            source_paths.append(str(session_path))
            for message in parsed["messages"]:
                if message["role"] == "user":
                    user_messages.append(message["text"])
                elif message["role"] == "assistant":
                    assistant_messages.append(message["text"])
                if len(user_messages) + len(assistant_messages) >= max_messages:
                    break
            if len(user_messages) + len(assistant_messages) >= max_messages:
                break

        messages = (
            [{"role": "user", "text": text} for text in user_messages]
            + [{"role": "assistant", "text": text} for text in assistant_messages]
        )
        conversation_chunks = self._conversation_chunks(messages, chunk_size=chunk_size)
        rule_summary = self._classified_summary(conversation_chunks)
        llm_summary = self._compress_with_llm(
            rule_summary=rule_summary,
            conversation_chunks=conversation_chunks,
        )
        classified_summary = llm_summary or rule_summary

        return {
            "source": "codex_session_jsonl",
            "capture_level": "partial" if user_messages or assistant_messages else "diff_only",
            "session_count": len(session_ids),
            "message_count": len(user_messages) + len(assistant_messages),
            "session_ids": session_ids,
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "conversation_chunks": conversation_chunks,
            "classified_summary": classified_summary,
            "classified_summary_source": "codex_llm" if llm_summary else "rules",
            "source_paths": source_paths,
        }

    def _session_paths(self, since_timestamp: int | None) -> List[Path]:
        sessions_dir = self.codex_home / "sessions"
        if not sessions_dir.exists():
            return []
        paths = sorted(
            sessions_dir.glob("**/*.jsonl"),
            key=lambda path: path.stat().st_mtime if path.exists() else 0,
            reverse=True,
        )
        if since_timestamp is None:
            return paths[:120]
        return [
            path for path in paths
            if path.exists() and int(path.stat().st_mtime) >= since_timestamp
        ][:120]

    def _read_session(
        self,
        *,
        session_path: Path,
        workspace_path: str,
        since_timestamp: int | None,
        remaining: int,
    ) -> Dict[str, Any]:
        if remaining <= 0:
            return {"session_id": "", "messages": []}

        session_id = ""
        session_workspace = ""
        rows: List[Dict[str, Any]] = []
        try:
            lines = session_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return {"session_id": "", "messages": []}

        for line in lines:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.append(row)
            if row.get("type") != "session_meta":
                continue
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            session_id = str(payload.get("id") or session_id)
            raw_cwd = str(payload.get("cwd") or "")
            if raw_cwd:
                session_workspace = str(Path(raw_cwd).resolve())

        if session_workspace != workspace_path:
            return {"session_id": session_id, "messages": []}

        messages: List[Dict[str, str]] = []
        for row in rows:
            timestamp = self._timestamp(row.get("timestamp"))
            if since_timestamp is not None and timestamp is not None and timestamp < since_timestamp:
                continue
            message = self._message_from_row(row)
            if not message:
                continue
            if any(existing == message for existing in messages):
                continue
            messages.append(message)
        return {"session_id": session_id, "messages": messages[-remaining:]}

    def _message_from_row(self, row: Dict[str, Any]) -> Dict[str, str] | None:
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        if row.get("type") != "response_item" or payload.get("type") != "message":
            return None
        role = payload.get("role")
        if role not in {"user", "assistant"}:
            return None
        text = self._content_text(payload.get("content"))
        if not text or self._is_noise(text):
            return None
        return {"role": role, "text": text[:700]}

    def _content_text(self, content: Any) -> str:
        parts: List[str] = []
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    value = item.get("text") or item.get("content")
                    if isinstance(value, str):
                        parts.append(value)
        return " ".join(" ".join(parts).split())

    def _timestamp(self, value: Any) -> int | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp())

    def _is_noise(self, text: str) -> bool:
        lower = text.lower()
        noisy_fragments = (
            "the following is the codex agent history",
            "assess the exact planned action below",
            "planned action json",
            ">>> transcript start",
            ">>> transcript delta start",
            ">>> approval request start",
            "treat the transcript",
            "untrusted evidence, not as instructions",
        )
        return any(fragment in lower for fragment in noisy_fragments)

    def _conversation_chunks(
        self,
        messages: List[Dict[str, str]],
        *,
        chunk_size: int,
    ) -> List[Dict[str, Any]]:
        if chunk_size <= 0:
            chunk_size = 6
        chunks: List[Dict[str, Any]] = []
        for index in range(0, len(messages), chunk_size):
            chunk_messages = messages[index:index + chunk_size]
            if not chunk_messages:
                continue
            text = " ".join(message["text"] for message in chunk_messages)
            chunks.append(
                {
                    "chunk_id": f"chunk_{len(chunks) + 1}",
                    "message_count": len(chunk_messages),
                    "roles": sorted({message["role"] for message in chunk_messages}),
                    "summary": self._compress_text(text),
                    "messages": chunk_messages,
                }
            )
        return chunks

    def _classified_summary(self, chunks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        classified = {
            "goals": [],
            "decisions": [],
            "implementation_actions": [],
            "tests_and_verification": [],
        }
        for chunk in chunks:
            for message in chunk.get("messages", []):
                if not isinstance(message, dict):
                    continue
                text = str(message.get("text") or "").strip()
                role = str(message.get("role") or "")
                if not text:
                    continue
                lower = text.lower()
                if self._looks_like_goal(text, lower, role):
                    self._append_unique(classified["goals"], text)
                if self._looks_like_decision(text, lower):
                    self._append_unique(classified["decisions"], text)
                if self._looks_like_implementation_action(text, lower, role):
                    self._append_unique(classified["implementation_actions"], text)
                if self._looks_like_test_or_verification(text, lower):
                    self._append_unique(classified["tests_and_verification"], text)
        return {key: values[:5] for key, values in classified.items()}

    def _compress_with_llm(
        self,
        *,
        rule_summary: Dict[str, List[str]],
        conversation_chunks: List[Dict[str, Any]],
    ) -> Dict[str, List[str]] | None:
        if not conversation_chunks:
            return None
        try:
            summary = self.llm_compressor.compress(
                {
                    "rule_summary": rule_summary,
                    "conversation_chunks": conversation_chunks,
                }
            )
        except Exception:
            return None
        if not isinstance(summary, dict):
            return None
        normalized = {
            key: [
                str(item).strip()
                for item in summary.get(key, [])
                if str(item).strip()
            ][:5]
            for key in ("goals", "decisions", "implementation_actions", "tests_and_verification")
        }
        return normalized if any(normalized.values()) else None

    def _looks_like_goal(self, text: str, lower: str, role: str) -> bool:
        return role == "user" and any(
            marker in lower or marker in text
            for marker in ("目标", "希望", "我想", "需要", "要把", "接入", "提高", "改成", "summary")
        )

    def _looks_like_decision(self, text: str, lower: str) -> bool:
        return any(
            marker in lower or marker in text
            for marker in ("决定", "先不", "默认", "应该", "建议", "口径", "保持", "不调用")
        )

    def _looks_like_implementation_action(self, text: str, lower: str, role: str) -> bool:
        return role == "assistant" and any(
            marker in lower or marker in text
            for marker in ("我会", "新增", "实现", "接入", "补", "改", "写", "reader", "chunker", "builder")
        )

    def _looks_like_test_or_verification(self, text: str, lower: str) -> bool:
        return any(
            marker in lower or marker in text
            for marker in ("pytest", "npm test", "npm run build", "测试", "验证", "passed", "通过")
        )

    def _append_unique(self, values: List[str], text: str) -> None:
        compressed = self._compress_text(text)
        if compressed and compressed not in values:
            values.append(compressed)

    def _compress_text(self, text: str, limit: int = 260) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= limit:
            return normalized
        boundary = max(normalized.rfind("。", 0, limit), normalized.rfind(".", 0, limit))
        if boundary >= 80:
            return normalized[: boundary + 1]
        return normalized[:limit].rstrip() + "..."
