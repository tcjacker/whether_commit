from __future__ import annotations

import hashlib


def stable_hash(value: str, length: int = 12) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def file_id_for_path(path: str, old_path: str | None = None) -> str:
    identity = f"{old_path or ''}->{path}"
    return f"cf_{stable_hash(identity, 8)}"


def fingerprint_for_text(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"
