"""Postgres (Supabase) store. Returned dicts use the camelCase keys the UI expects.

Meetings and follow-ups are NOT stored here: Google Calendar / Tasks are the source of truth.
"""

import json
import os
import threading
from zoneinfo import ZoneInfo

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
    'to_char(received_at AT TIME ZONE %(tz)s, \'HH24:MI\') AS "receivedAt", '
    'to_char(received_at AT TIME ZONE %(tz)s, \'DD Mon\') AS "receivedOn", '
    'kind, triage, processed, participants, reject_note AS "rejectNote", attachments, automated'
)


def _tz() -> str:
    return get_settings().get("timezone", "Asia/Kolkata")


def list_requests() -> list[dict]:
    """Requests the agent and the UI work with. Skipped bulk mail stays stored (so it is not fetched again) but hidden."""
    return _q(f"SELECT {_REQ_COLS} FROM requests WHERE kind <> 'bulk' ORDER BY received_at", {"tz": _tz()})


def get_request(request_id: str) -> dict | None:
    return _q(f"SELECT {_REQ_COLS} FROM requests WHERE id = %(id)s", {"tz": _tz(), "id": request_id}, one=True)


def request_exists(request_id: str) -> bool:
    return _q("SELECT 1 AS x FROM requests WHERE id = %s", (request_id,), one=True) is not None


def upsert_request(id: str, thread_id: str, message_id: str, from_addr: str, subject: str, body: str,
                   received_at, kind: str, participants: list[str] | None = None,
                   attachments: list[str] | None = None, automated: bool = False) -> None:
    _q(
        "INSERT INTO requests (id, thread_id, message_id, from_addr, subject, body, received_at, kind, participants, "
        "attachments, automated) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
        (id, thread_id, message_id, from_addr, subject, body, received_at, kind,
         json.dumps(participants) if participants is not None else None,
         json.dumps(attachments or []), automated), write=True,
    )


_REQ_FIELDS = {"triage", "processed", "reject_note", "kind"}


def update_request(request_id: str, **fields) -> None:
    bad = set(fields) - _REQ_FIELDS
    if bad:
        raise ValueError(f"cannot update request fields {bad}")
    sets = ", ".join(f"{k} = %({k})s" for k in fields)
    _q(f"UPDATE requests SET {sets} WHERE id = %(id)s", {**fields, "id": request_id}, write=True)


def bump_attempts(request_id: str) -> int:
    """Count one more failed agent run on a request. Returns the new count."""
    row = _q("UPDATE requests SET attempts = attempts + 1 WHERE id = %s RETURNING attempts", (request_id,), one=True)
    return row["attempts"] if row else 0


# ---- approvals --------------------------------------------------------------

# Joined with the original request so the approval card can show who wrote what.
_APR_SELECT = (
    'SELECT a.id::text AS id, a.type, a.summary, a.draft, a.status, a.request_id AS "requestId", a.title, a.day, '
    'a.start, a."end", a.attendees, a.google_ref AS "googleRef", '
    'to_char(a.meeting_date, \'YYYY-MM-DD\') AS "meetingDate", a.edited, a.decision_note AS "decisionNote", '
    'to_char(a.created_at AT TIME ZONE %(tz)s, \'DD Mon HH24:MI\') AS "createdAt", '
    'r.from_addr AS "from", r.subject AS "subject", left(r.body, 1500) AS "body", r.message_id AS "messageId", '
    'to_char(r.received_at AT TIME ZONE %(tz)s, \'DD Mon HH24:MI\') AS "receivedAt" '
    'FROM approvals a LEFT JOIN requests r ON r.id = a.request_id'
)
_OPEN = ("pending", "approving", "approved")


def list_approvals() -> list[dict]:
    return _q(f"{_APR_SELECT} ORDER BY a.id", {"tz": _tz()})


def get_approval(approval_id: str) -> dict | None:
    if not str(approval_id).isdigit():
        return None
    return _q(f"{_APR_SELECT} WHERE a.id = %(id)s", {"tz": _tz(), "id": int(approval_id)}, one=True)


def claim_approval(approval_id: str) -> bool:
    """Atomically move pending -> approving. Only the caller that gets True may perform the side effect."""
    row = _q("UPDATE approvals SET status = 'approving' WHERE id = %s AND status = 'pending' RETURNING id",
             (int(approval_id),), one=True)
    return row is not None


def release_approval(approval_id: str) -> None:
    """The side effect failed: make the item pending again so it can be retried."""
    _q("UPDATE approvals SET status = 'pending' WHERE id = %s AND status = 'approving'", (int(approval_id),), write=True)


def finish_approval(approval_id: str, google_ref: str | None = None, draft: str | None = None,
                    attendees: list[str] | None = None, edited: bool = False,
                    start: str | None = None, end: str | None = None) -> None:
    """The side effect happened: record it. `draft`/`attendees`/`start`/`end` are what was actually sent or booked."""
    _q(
        "UPDATE approvals SET status = 'approved', decided_at = now(), google_ref = COALESCE(%s, google_ref), "
        "draft = COALESCE(%s, draft), attendees = COALESCE(%s::jsonb, attendees), edited = %s, "
        "start = COALESCE(%s, start), \"end\" = COALESCE(%s, \"end\") WHERE id = %s",
        (google_ref, draft, json.dumps(attendees) if attendees is not None else None, edited, start, end, int(approval_id)),
        write=True,
    )


def reject_approval(approval_id: str, note: str | None = None) -> bool:
    row = _q("UPDATE approvals SET status = 'rejected', decided_at = now(), decision_note = %s "
             "WHERE id = %s AND status = 'pending' RETURNING id", (note, int(approval_id)), one=True)
    return row is not None


def add_approval(type_: str, summary: str, request_id: str | None = None, draft: str | None = None,
                 title: str | None = None, day: int | None = None, start: str | None = None,
                 end: str | None = None, attendees: list[str] | None = None,
                 meeting_date: str | None = None) -> dict:
    """Create a pending approval. If an open one already exists for this request+type, return it with duplicate=True."""
    row = _q(
        "INSERT INTO approvals (type, summary, draft, request_id, title, day, start, \"end\", attendees, meeting_date) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING id",
        (type_, summary, draft, request_id, title, day, start, end,
         json.dumps(attendees) if attendees is not None else None, meeting_date),
        one=True,
    )
    if row is None:
        existing = _q("SELECT id FROM approvals WHERE request_id = %s AND type = %s AND status = ANY(%s) ORDER BY id DESC",
                      (request_id, type_, list(_OPEN)), one=True)
        a = get_approval(str(existing["id"]))
        return {**a, "duplicate": True}
    log("approval_created", approvalId=str(row["id"]), type=type_, requestId=request_id)
    return get_approval(str(row["id"]))


# ---- settings / brief / token / log ----------------------------------------

DEFAULT_SETTINGS = {
    "timezone": "Asia/Kolkata", "briefTime": "08:00", "pollMinutes": 10,
    "attendeeAllowDomains": [], "reminderMinutes": 15, "escalationAlerts": True,
    "workingDays": [0, 1, 2, 3, 4], "minNoticeMinutes": 120,  # 0 = Monday
}


def get_settings() -> dict:
    row = _q("SELECT data FROM settings WHERE id = 1", one=True)
    return {**DEFAULT_SETTINGS, **(row["data"] if row else {})}


def save_settings(data: dict) -> dict:
    _q("INSERT INTO settings (id, data) VALUES (1, %s) ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data",
       (json.dumps(data),), write=True)
    return get_settings()


def get_brief() -> dict | None:
    # generated_at is timestamptz: convert to the principal's timezone, or it comes out in the DB session's (UTC).
    return _q('SELECT text, to_char(generated_at AT TIME ZONE %(tz)s, \'YYYY-MM-DD"T"HH24:MI:SS\') AS "generatedAt" '
              "FROM brief WHERE id = 1", {"tz": _tz()}, one=True)


def save_brief(text: str) -> dict:
    _q("INSERT INTO brief (id, text, generated_at) VALUES (1, %s, now()) "
       "ON CONFLICT (id) DO UPDATE SET text = EXCLUDED.text, generated_at = now()", (text,), write=True)
    return get_brief()


def brief_emailed_since(ts) -> bool:
    """Whether a scheduled (emailed) brief went out at or after `ts` (an aware datetime)."""
    return _q("SELECT 1 AS x FROM audit_log WHERE event = 'brief_generated' AND details->>'emailed' = 'true' "
              "AND at >= %s LIMIT 1", (ts,), one=True) is not None


def get_token() -> dict | None:
    return _q("SELECT token, email FROM oauth_token WHERE id = 1", one=True)


def save_token(token: dict, email: str | None = None) -> None:
    _q("INSERT INTO oauth_token (id, token, email) VALUES (1, %s, %s) "
       "ON CONFLICT (id) DO UPDATE SET token = EXCLUDED.token, email = COALESCE(EXCLUDED.email, oauth_token.email)",
       (json.dumps(token), email), write=True)


def delete_token() -> None:
    _q("DELETE FROM oauth_token WHERE id = 1", write=True)


def log(event: str, **details) -> None:
    _q("INSERT INTO audit_log (event, details) VALUES (%s, %s)", (event, json.dumps(details, default=str)), write=True)


# ---- meeting prep (notes + linked docs) -------------------------------------


def get_prep_map() -> dict[str, dict]:
    rows = _q("SELECT event_id, note, docs, to_char(generated_at AT TIME ZONE %(tz)s, 'DD Mon HH24:MI') AS at "
              "FROM meeting_prep WHERE generated_at > now() - interval '3 days'", {"tz": _tz()})
    return {r["event_id"]: {"note": r["note"], "docs": r["docs"], "at": r["at"]} for r in rows}


def prep_is_fresh(event_id: str, hours: int = 12) -> bool:
    return _q("SELECT 1 AS x FROM meeting_prep WHERE event_id = %s AND generated_at > now() - make_interval(hours => %s)",
              (event_id, hours), one=True) is not None


def save_prep(event_id: str, meeting_date: str | None, note: str, docs: list[dict]) -> None:
    _q("INSERT INTO meeting_prep (event_id, meeting_date, note, docs, generated_at) VALUES (%s,%s,%s,%s, now()) "
       "ON CONFLICT (event_id) DO UPDATE SET meeting_date = EXCLUDED.meeting_date, note = EXCLUDED.note, "
       "docs = EXCLUDED.docs, generated_at = now()", (event_id, meeting_date, note, json.dumps(docs)), write=True)


def attach_prep(meetings: list[dict]) -> list[dict]:
    """Add the generated prep note and linked docs to calendar meetings (the note replaces the raw description snippet)."""
    prep = get_prep_map()
    for m in meetings:
        p = prep.get(m["id"])
        if p:
            m["prepNote"], m["docs"], m["prepAt"] = p["note"], p["docs"], p["at"]
        else:
            m.setdefault("docs", [])
    return meetings


# ---- audit log + KPIs --------------------------------------------------------


def list_audit(limit: int = 100, event: str | None = None) -> list[dict]:
    limit = max(1, min(int(limit), 500))
    where = "WHERE event = %(event)s " if event else ""
    return _q(
        "SELECT id, to_char(at AT TIME ZONE %(tz)s, 'YYYY-MM-DD HH24:MI:SS') AS at, event, details "
        f"FROM audit_log {where}ORDER BY id DESC LIMIT %(limit)s",
        {"tz": _tz(), "event": event, "limit": limit},
    )


def audit_events() -> list[str]:
    return [r["event"] for r in _q("SELECT DISTINCT event FROM audit_log ORDER BY event")]


def kpis(days: int = 30) -> dict:
    """The spec's KPIs that live in our own database. Follow-ups closed comes from Google Tasks (see main.py)."""
    days = max(1, min(int(days), 365))
    s = get_settings()
    tz = ZoneInfo(s["timezone"])
    hh, mm = (int(x) for x in s["briefTime"].split(":"))
    due = hh * 60 + mm

    # Brief on time: scheduled (emailed) briefs generated within 15 minutes after the configured time.
    rows = _q("SELECT at, details FROM audit_log WHERE event = 'brief_generated' AND at > now() - make_interval(days => %s)", (days,))
    sent = [r["at"].astimezone(tz) for r in rows if (r["details"] or {}).get("emailed")]
    on_time = sum(1 for t in sent if due <= t.hour * 60 + t.minute <= due + 15)

    # Meetings booked without clashes: approved bookings vs. bookings refused because the calendar changed.
    booked = _q("SELECT count(*) AS n FROM approvals WHERE type = 'meeting' AND status = 'approved' "
                "AND decided_at > now() - make_interval(days => %s)", (days,), one=True)["n"]
    clashes = _q("SELECT count(*) AS n FROM audit_log WHERE event = 'approval_clash' "
                 "AND at > now() - make_interval(days => %s)", (days,), one=True)["n"]

    # Average reply time: mail received -> approved reply sent.
    reply = _q("SELECT avg(extract(epoch FROM (a.decided_at - r.received_at))) / 60 AS mins, count(*) AS n "
               "FROM approvals a JOIN requests r ON r.id = a.request_id "
               "WHERE a.type = 'reply' AND a.status = 'approved' AND a.decided_at > now() - make_interval(days => %s)",
               (days,), one=True)
    return {
        "days": days,
        "briefOnTime": {"onTime": on_time, "total": len(sent)},
        "meetings": {"booked": booked, "clashRefusals": clashes},
        "avgReplyMinutes": round(float(reply["mins"]), 1) if reply["mins"] is not None else None,
        "repliesSent": reply["n"],
    }
