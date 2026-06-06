from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from threading import Lock

from app.models.schemas import CaseResult


_DB_LOCK = Lock()


def _db_path() -> Path:
    configured = os.getenv("DECISIONOS_DB_PATH")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "data" / "decisionos.db"


def _connect() -> sqlite3.Connection:
    db_path = _db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with _DB_LOCK:
        conn = _connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cases (
                    case_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    requires_human_review INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cases_review_queue ON cases (requires_human_review, created_at)"
            )
            conn.commit()
        finally:
            conn.close()


def save_case(case: CaseResult) -> None:
    requires_human_review = 1 if case.policy_decision.requires_human_review else 0
    payload_json = case.model_dump_json()

    with _DB_LOCK:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO cases (case_id, status, requires_human_review, payload_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(case_id) DO UPDATE SET
                    status = excluded.status,
                    requires_human_review = excluded.requires_human_review,
                    payload_json = excluded.payload_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (case.case_id, case.status, requires_human_review, payload_json),
            )
            conn.commit()
        finally:
            conn.close()


def get_case(case_id: str) -> CaseResult | None:
    with _DB_LOCK:
        conn = _connect()
        try:
            row = conn.execute("SELECT payload_json FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        finally:
            conn.close()

    if not row:
        return None
    return CaseResult.model_validate_json(row["payload_json"])


def list_cases() -> list[CaseResult]:
    with _DB_LOCK:
        conn = _connect()
        try:
            rows = conn.execute("SELECT payload_json FROM cases ORDER BY created_at DESC").fetchall()
        finally:
            conn.close()

    return [CaseResult.model_validate_json(row["payload_json"]) for row in rows]


def list_review_queue() -> list[CaseResult]:
    with _DB_LOCK:
        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT payload_json FROM cases WHERE requires_human_review = 1 ORDER BY created_at DESC"
            ).fetchall()
        finally:
            conn.close()

    return [CaseResult.model_validate_json(row["payload_json"]) for row in rows]


def list_cases_between(start_ts: str, end_ts: str) -> list[CaseResult]:
    with _DB_LOCK:
        conn = _connect()
        try:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM cases
                WHERE created_at >= ? AND created_at < ?
                ORDER BY created_at DESC
                """,
                (start_ts, end_ts),
            ).fetchall()
        finally:
            conn.close()

    return [CaseResult.model_validate_json(row["payload_json"]) for row in rows]


def case_count() -> int:
    with _DB_LOCK:
        conn = _connect()
        try:
            row = conn.execute("SELECT COUNT(*) AS count FROM cases").fetchone()
        finally:
            conn.close()

    return int(row["count"]) if row else 0


def set_human_decision(case_id: str, decision: str) -> CaseResult | None:
    with _DB_LOCK:
        conn = _connect()
        try:
            row = conn.execute("SELECT payload_json FROM cases WHERE case_id = ?", (case_id,)).fetchone()
            if not row:
                return None

            case = CaseResult.model_validate_json(row["payload_json"])
            case.status = decision

            conn.execute(
                """
                UPDATE cases
                SET status = ?, payload_json = ?, updated_at = CURRENT_TIMESTAMP
                WHERE case_id = ?
                """,
                (decision, case.model_dump_json(), case_id),
            )
            conn.commit()
            return case
        finally:
            conn.close()


def clear_all_cases() -> None:
    with _DB_LOCK:
        conn = _connect()
        try:
            conn.execute("DELETE FROM cases")
            conn.commit()
        finally:
            conn.close()
