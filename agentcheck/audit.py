"""Audit log of every gatekeeper decision (SQLite)."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from agentcheck import config

# Decisions that mean a duplicate agent was NOT built.
PREVENTED = ("use_existing", "extend_existing", "combine_existing")

# Rough effort to build + test one small agent, for the "hours saved" stat.
HOURS_PER_AGENT = 16


def _connect(db: Path = config.AUDIT_DB) -> sqlite3.Connection:
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            requested_name TEXT NOT NULL,
            verdict TEXT NOT NULL,
            coverage REAL,
            matched_agent TEXT,
            decision TEXT NOT NULL,
            justification TEXT
        )"""
    )
    return conn


def log(
    requested_name: str,
    verdict: str,
    coverage: float | None,
    matched_agent: str | None,
    decision: str,
    justification: str = "",
) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO decisions (ts, requested_name, verdict, coverage, matched_agent, decision, justification) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(timespec="seconds"), requested_name, verdict, coverage, matched_agent, decision, justification),
        )


def history() -> List[Dict]:
    with closing(_connect()) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute("SELECT * FROM decisions ORDER BY id DESC")]


def stats() -> Dict[str, int]:
    rows = history()
    prevented = sum(1 for r in rows if r["decision"] in PREVENTED)
    return {
        "checks": len(rows),
        "prevented": prevented,
        "created": sum(1 for r in rows if r["decision"] in ("create_new", "create_anyway")),
        "overrides": sum(1 for r in rows if r["decision"] == "create_anyway"),
        "hours_saved": prevented * HOURS_PER_AGENT,
    }


def clear() -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM decisions")
