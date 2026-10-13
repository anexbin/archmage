"""Append-only daily audit logging. Logging failure must stop the caller."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import AUDIT_LOG_DIR


class AuditLogError(RuntimeError):
    pass


def log_action(
    command: str,
    decision: str,
    exit_code: int | None,
    output: str = "",
    *,
    audit_dir: Path | str = AUDIT_LOG_DIR,
    network_enabled: bool = False,
) -> Path:
    now = datetime.now().astimezone()
    path = Path(audit_dir) / (now.date().isoformat() + ".log")
    record: dict[str, Any] = {
        "timestamp": now.isoformat(timespec="seconds"),
        "command": command,
        "user_decision": decision,
        "exit_code": exit_code,
        "output_first_500_chars": output[:500],
        "network_enabled": bool(network_enabled),
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise AuditLogError(f"Could not write required audit log {path}: {exc}") from exc
    return path
