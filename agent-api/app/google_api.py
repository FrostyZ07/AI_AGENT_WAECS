"""The only module that talks to Google (Gmail, Calendar, Tasks).

Meetings keep the app's `day` offset + "HH:MM" shape; conversion to real datetimes happens here,
using the `timezone` setting.
"""

import base64
import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import parseaddr, parsedate_to_datetime
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request as GRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app import store

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/tasks",
]
TASKLIST_TITLE = "EA Follow-ups"
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MEETING_WORDS = re.compile(r"\b(meet|meeting|call|catch.?up|schedule|slot|sync|demo)\b", re.I)


class NotConnected(RuntimeError):
    pass


def _tz() -> ZoneInfo:
    return ZoneInfo(store.get_settings()["timezone"])


# ---- OAuth ------------------------------------------------------------------


def _client_config() -> dict:
    cid, secret = os.getenv("GOOGLE_CLIENT_ID"), os.getenv("GOOGLE_CLIENT_SECRET")
    if not cid or not secret:
        raise RuntimeError("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET are not set in agent-api/.env")
    return {"web": {"client_id": cid, "client_secret": secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"}}


def _redirect_uri() -> str:
    return os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/oauth/google/callback")


def _flow(state: str | None = None) -> Flow:
    return Flow.from_client_config(_client_config(), scopes=SCOPES, redirect_uri=_redirect_uri(), state=state)


# The code verifier from start() is needed again in the callback (PKCE). Single principal, so one slot is enough.
_pending: dict = {}


def auth_url() -> str:
    flow = _flow()
    url, state = flow.authorization_url(access_type="offline", prompt="consent", include_granted_scopes="true")
    _pending[state] = flow.code_verifier
    return url


def finish_auth(code: str, state: str) -> str:
    """Exchange the code, store the refresh token, return the principal's email."""
    if state not in _pending:
        raise ValueError("Unknown OAuth state. Start the connection again from Settings.")
    flow = _flow(state)
    flow.code_verifier = _pending.pop(state)
    flow.fetch_token(code=code)
    c = flow.credentials
    if not c.refresh_token:
        raise ValueError("Google did not return a refresh token. Remove the app at myaccount.google.com/permissions and retry.")
    email = build("gmail", "v1", credentials=c, cache_discovery=False).users().getProfile(userId="me").execute()["emailAddress"]
    store.save_token(json.loads(c.to_json()), email)
    store.log("google_connected", email=email)
    return email


def creds() -> Credentials:
    row = store.get_token()
    if not row:
        raise NotConnected("Connect Google in Settings first.")
    c = Credentials.from_authorized_user_info(row["token"], SCOPES)
    if not c.valid:
        c.refresh(GRequest())
        store.save_token(json.loads(c.to_json()))
    return c


def status() -> dict:
    row = store.get_token()
    return {"connected": bool(row), "email": row["email"] if row else None}


def principal_email() -> str:
    row = store.get_token()
    if not row:
        raise NotConnected("Connect Google in Settings first.")
    return row["email"]


def _svc(name: str, version: str):
    return build(name, version, credentials=creds(), cache_discovery=False)


# ---- Gmail ------------------------------------------------------------------


def _header(payload: dict, name: str) -> str:
    return next((h["value"] for h in payload.get("headers", []) if h["name"].lower() == name.lower()), "")


def _text_body(payload: dict) -> str:
    """Best-effort text/plain extraction from a Gmail message payload."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", "replace")
    for part in payload.get("parts", []) or []:
        text = _text_body(part)
        if text:
            return text
    return ""


def fetch_new_mail(max_results: int = 20) -> int:
    """Pull recent inbox mail into the requests table. Read-only: never modifies the mailbox. Returns count added."""
    gmail = _svc("gmail", "v1")
    me = principal_email().lower()
    refs = gmail.users().messages().list(userId="me", q="in:inbox newer_than:2d -from:me", maxResults=max_results).execute()
    added = 0
    for ref in refs.get("messages", []):
        if store.request_exists(ref["id"]):
            continue
        msg = gmail.users().messages().get(userId="me", id=ref["id"], format="full").execute()
        p = msg["payload"]
        sender = parseaddr(_header(p, "From"))[1]
        if sender.lower() == me:
            continue
        subject = _header(p, "Subject")
        body = _text_body(p).strip()[:4000]
        try:
            received = parsedate_to_datetime(_header(p, "Date")).astimezone(timezone.utc)
        except (TypeError, ValueError):
            received = datetime.fromtimestamp(int(msg["internalDate"]) / 1000, timezone.utc)
        kind = "meeting" if _MEETING_WORDS.search(f"{subject} {body}") else "mail"
        store.upsert_request(msg["id"], msg["threadId"], _header(p, "Message-ID"), sender, subject, body, received, kind)
        added += 1
    if added:
        store.log("mail_fetched", count=added)
    return added


def _send(msg: EmailMessage, thread_id: str | None = None) -> str:
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    body = {"raw": raw, **({"threadId": thread_id} if thread_id else {})}
    return _svc("gmail", "v1").users().messages().send(userId="me", body=body).execute()["id"]


def send_reply(request: dict, body: str) -> str:
    """Send an approved reply in the original thread. Returns the Gmail message id."""
    msg = EmailMessage()
    msg["To"] = request["from"]
    subj = request["subject"] or ""
    msg["Subject"] = subj if subj.lower().startswith("re:") else f"Re: {subj}"
    if request.get("messageId"):
        msg["In-Reply-To"] = request["messageId"]
        msg["References"] = request["messageId"]
    msg.set_content(body)
    return _send(msg, request.get("threadId"))


def send_to_self(subject: str, text: str) -> str:
    """Email the principal their own brief. No third party involved."""
    msg = EmailMessage()
    msg["To"] = principal_email()
    msg["Subject"] = subject
    msg.set_content(text)
    return _send(msg)


# ---- Calendar ---------------------------------------------------------------


def _day_bounds(day: int) -> datetime:
    tz = _tz()
    d = datetime.now(tz).date() + timedelta(days=day)
    return datetime(d.year, d.month, d.day, tzinfo=tz)


def list_meetings(from_day: int, to_day: int) -> list[dict]:
    """Calendar events as app meetings: {id, title, day, start, end, attendees, prepNote, allDay}."""
    tz = _tz()
    today = datetime.now(tz).date()
    res = _svc("calendar", "v3").events().list(
        calendarId="primary", timeMin=_day_bounds(from_day).isoformat(), timeMax=_day_bounds(to_day + 1).isoformat(),
        singleEvents=True, orderBy="startTime", maxResults=250,
    ).execute()
    out = []
    for e in res.get("items", []):
        if e.get("status") == "cancelled":
            continue
        s, en = e["start"], e["end"]
        all_day = "date" in s
        if all_day:
            start_d = date.fromisoformat(s["date"])
            start_t, end_t = "00:00", "23:59"
        else:
            sdt = datetime.fromisoformat(s["dateTime"]).astimezone(tz)
            edt = datetime.fromisoformat(en["dateTime"]).astimezone(tz)
            start_d, start_t = sdt.date(), sdt.strftime("%H:%M")
            end_t = edt.strftime("%H:%M") if edt.date() == sdt.date() else "23:59"
        m = {
            "id": e["id"], "title": e.get("summary", "(no title)"), "day": (start_d - today).days,
            "start": start_t, "end": end_t,
            "attendees": [a.get("displayName") or a["email"] for a in e.get("attendees", [])] or ["Just you"],
            "allDay": all_day,
        }
        if e.get("description"):
            m["prepNote"] = e["description"].strip()[:200]
        out.append(m)
    return out


def create_event(title: str, day: int, start: str, end: str, attendees: list[str]) -> str:
    """Create an event and invite attendees. Returns the event id. Only called after the principal approves."""
    tz = _tz()
    base = _day_bounds(day)

    def at(hhmm: str) -> str:
        h, m = hhmm.split(":")
        return base.replace(hour=int(h), minute=int(m)).isoformat()

    emails = [a for a in attendees if _EMAIL.match(a)]
    others = [a for a in attendees if not _EMAIL.match(a)]
    event = {
        "summary": title,
        "start": {"dateTime": at(start), "timeZone": tz.key},
        "end": {"dateTime": at(end), "timeZone": tz.key},
        "attendees": [{"email": a} for a in emails],
    }
    if others:
        event["description"] = "With: " + ", ".join(others)
    created = _svc("calendar", "v3").events().insert(calendarId="primary", body=event, sendUpdates="all").execute()
    return created["id"]


# ---- Tasks (follow-ups) -----------------------------------------------------

_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _tasklist_id() -> str:
    tasks = _svc("tasks", "v1")
    for tl in tasks.tasklists().list(maxResults=100).execute().get("items", []):
        if tl["title"] == TASKLIST_TITLE:
            return tl["id"]
    return tasks.tasklists().insert(body={"title": TASKLIST_TITLE}).execute()["id"]


def _due_date(due: str) -> date | None:
    today = datetime.now(_tz()).date()
    word = due.strip().lower()
    if word == "today":
        return today
    if word == "tomorrow":
        return today + timedelta(days=1)
    if word in _WEEKDAYS:
        return today + timedelta(days=(_WEEKDAYS.index(word) - today.weekday()) % 7 or 7)
    try:
        return date.fromisoformat(due.strip())
    except ValueError:
        return None


def add_task(task: str, owner: str, due: str) -> str:
    d = _due_date(due)
    body = {"title": task, "notes": f"Owner: {owner}\nDue: {due}"}
    if d:
        body["due"] = f"{d.isoformat()}T00:00:00.000Z"
    return _svc("tasks", "v1").tasks().insert(tasklist=_tasklist_id(), body=body).execute()["id"]


def list_follow_ups() -> list[dict]:
    items = _svc("tasks", "v1").tasks().list(tasklist=_tasklist_id(), showCompleted=True, showHidden=True, maxResults=100).execute().get("items", [])
    out = []
    for t in items:
        notes = t.get("notes", "")
        owner = re.search(r"Owner: (.+)", notes)
        due = re.search(r"Due: (.+)", notes)
        out.append({
            "id": t["id"], "task": t.get("title", ""), "owner": owner.group(1) if owner else "Assistant",
            "due": due.group(1) if due else (t["due"][:10] if t.get("due") else "No date"),
            "done": t.get("status") == "completed",
        })
    return out
