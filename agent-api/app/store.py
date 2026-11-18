"""Postgres (Supabase) store. Returned dicts use the camelCase keys the UI expects.

Meetings and follow-ups are NOT stored here: Google Calendar / Tasks are the source of truth.
"""

import json
import os
import threading

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()

_conn: psycopg.Connection | None = None
_lock = threading.RLock()  # one shared connection; the scheduler thread and request threads take turns


def _db() -> psycopg.Connection:
    global _conn
    if _conn is None or _conn.closed:
        url = os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL is not set. Add it to agent-api/.env (Supabase connection string).")
        _conn = psycopg.connect(url, row_factory=dict_row, autocommit=True)
    return _conn


def _q(sql: str, params: tuple | dict = (), one: bool = False, write: bool = False):
    """Run a query. Reconnects once if the connection dropped."""
    with _lock:
        for attempt in (0, 1):
            try:
                cur = _db().execute(sql, params)
                if write and cur.description is None:
                    return None
                rows = cur.fetchall() if cur.description else []
                return (rows[0] if rows else None) if one else rows
            except psycopg.OperationalError:
                global _conn
                _conn = None
                if attempt:
                    raise


# ---- requests ---------------------------------------------------------------

_REQ_COLS = (
    'id, thread_id AS "threadId", message_id AS "messageId", from_addr AS "from", subject, body, '
    'to_char(received_at AT TIME ZONE %(tz)s, \'HH24:MI\') AS "receivedAt", kind, triage, processed'
)


def _tz() -> str:
    return get_settings().get("timezone", "Asia/Kolkata")


def list_requests() -> list[dict]:
    return _q(f"SELECT {_REQ_COLS} FROM requests ORDER BY received_at", {"tz": _tz()})


def get_request(request_id: str) -> dict | None:
    return _q(f"SELECT {_REQ_COLS} FROM requests WHERE id = %(id)s", {"tz": _tz(), "id": request_id}, one=True)


def request_exists(request_id: str) -> bool:
    return _q("SELECT 1 AS x FROM requests WHERE id = %s", (request_id,), one=True) is not None


def upsert_request(id: str, thread_id: str, message_id: str, from_addr: str, subject: str, body: str,
                   received_at, kind: str) -> None:
    _q(
        "INSERT INTO requests (id, thread_id, message_id, from_addr, subject, body, received_at, kind) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
        (id, thread_id, message_id, from_addr, subject, body, received_at, kind), write=True,
    )


_REQ_FIELDS = {"triage", "processed"}


def update_request(request_id: str, **fields) -> None:
    bad = set(fields) - _REQ_FIELDS
    if bad:
        raise ValueError(f"cannot update request fields {bad}")
    sets = ", ".join(f"{k} = %({k})s" for k in fields)
    _q(f"UPDATE requests SET {sets} WHERE id = %(id)s", {**fields, "id": request_id}, write=True)


# ---- approvals --------------------------------------------------------------

_APR_COLS = 'id::text AS id, type, summary, draft, status, request_id AS "requestId", title, day, start, "end", attendees, google_ref AS "googleRef"'


def list_approvals() -> list[dict]:
    return _q(f"SELECT {_APR_COLS} FROM approvals ORDER BY id")


def get_approval(approval_id: str) -> dict | None:
    if not str(approval_id).isdigit():
        return None
    return _q(f"SELECT {_APR_COLS} FROM approvals WHERE id = %s", (int(approval_id),), one=True)


_APR_FIELDS = {"status": "status", "googleRef": "google_ref"}


def update_approval(approval_id: str, **fields) -> None:
    sets = ", ".join(f"{_APR_FIELDS[k]} = %({k})s" for k in fields)  # KeyError on unknown field = bug, fail loud
    _q(f"UPDATE approvals SET {sets} WHERE id = %(id)s", {**fields, "id": int(approval_id)}, write=True)


def add_approval(type_: str, summary: str, request_id: str | None = None, draft: str | None = None,
                 title: str | None = None, day: int | None = None, start: str | None = None,
                 end: str | None = None, attendees: list[str] | None = None) -> dict:
    row = _q(
        "INSERT INTO approvals (type, summary, draft, request_id, title, day, start, \"end\", attendees) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
        (type_, summary, draft, request_id, title, day, start, end, json.dumps(attendees) if attendees is not None else None),
        one=True,
    )
    log("approval_created", approvalId=str(row["id"]), type=type_, requestId=request_id)
    return get_approval(str(row["id"]))


# ---- settings / brief / token / log ----------------------------------------

DEFAULT_SETTINGS = {"timezone": "Asia/Kolkata", "briefTime": "08:00", "pollMinutes": 10}


def get_settings() -> dict:
    row = _q("SELECT data FROM settings WHERE id = 1", one=True)
    return {**DEFAULT_SETTINGS, **(row["data"] if row else {})}


def save_settings(data: dict) -> dict:
    _q("INSERT INTO settings (id, data) VALUES (1, %s) ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data",
       (json.dumps(data),), write=True)
    return get_settings()


def get_brief() -> dict | None:
    return _q('SELECT text, to_char(generated_at, \'YYYY-MM-DD"T"HH24:MI:SS\') AS "generatedAt" FROM brief WHERE id = 1', one=True)


def save_brief(text: str) -> dict:
    _q("INSERT INTO brief (id, text, generated_at) VALUES (1, %s, now()) "
       "ON CONFLICT (id) DO UPDATE SET text = EXCLUDED.text, generated_at = now()", (text,), write=True)
    return get_brief()


def get_token() -> dict | None:
    return _q("SELECT token, email FROM oauth_token WHERE id = 1", one=True)


def save_token(token: dict, email: str | None = None) -> None:
    _q("INSERT INTO oauth_token (id, token, email) VALUES (1, %s, %s) "
       "ON CONFLICT (id) DO UPDATE SET token = EXCLUDED.token, email = COALESCE(EXCLUDED.email, oauth_token.email)",
       (json.dumps(token), email), write=True)


def log(event: str, **details) -> None:
    _q("INSERT INTO audit_log (event, details) VALUES (%s, %s)", (event, json.dumps(details, default=str)), write=True)
