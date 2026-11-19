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
from email.utils import getaddresses, parseaddr, parsedate_to_datetime
from html.parser import HTMLParser
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
    "https://www.googleapis.com/auth/drive.readonly",  # meeting prep: find and read docs. Needs a one-time reconnect.
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


_VOID = {"br", "img", "hr", "meta", "link", "input", "wbr", "area", "base", "col", "embed", "source", "track"}
_HIDDEN_TAGS = {"script", "style", "head", "title", "template", "noscript"}
# Text a reader never sees is the usual carrier for prompt injection, so it never reaches the model.
_HIDDEN_STYLE = re.compile(
    r"display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0(?:\.0+)?(?:px|pt|em|rem|%)?\s*(?:;|!|$)"
    r"|opacity\s*:\s*0(?:\.0+)?\s*(?:;|!|$)|max-height\s*:\s*0(?:px)?\s*(?:;|!|$)", re.I)
_INVISIBLE_CHARS = re.compile("[​-‏‪-‮⁠-⁤﻿]")


class _HtmlText(HTMLParser):
    """Tiny HTML -> text converter for HTML-only mail (stdlib, no extra dependency). Drops text hidden from the reader."""

    def __init__(self):
        super().__init__()
        self.out: list[str] = []
        self._stack: list[tuple[str, bool]] = []  # (tag, hidden) for every open non-void element

    def _hidden(self) -> bool:
        return bool(self._stack) and self._stack[-1][1]

    def handle_starttag(self, tag, attrs):
        if tag in ("br", "p", "div", "tr", "li"):
            self.out.append("\n")
        if tag in _VOID:
            return
        a = {k.lower(): (v or "") for k, v in attrs}
        hidden = (self._hidden() or tag in _HIDDEN_TAGS or "hidden" in a
                  or a.get("aria-hidden", "").lower() == "true" or bool(_HIDDEN_STYLE.search(a.get("style", ""))))
        self._stack.append((tag, hidden))

    def handle_startendtag(self, tag, attrs):  # <div/>: opens and closes at once, so nothing to push
        if tag in ("br", "p", "div", "tr", "li"):
            self.out.append("\n")

    def handle_endtag(self, tag):
        # Pop up to the matching open tag; a stray closing tag (broken HTML) is ignored.
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                del self._stack[i:]
                return

    def handle_data(self, data):
        if not self._hidden():
            self.out.append(data)


def _find_part(payload: dict, mime: str) -> str:
    if payload.get("mimeType") == mime and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", "replace")
    for part in payload.get("parts", []) or []:
        text = _find_part(part, mime)
        if text:
            return text
    return ""


def _text_body(payload: dict) -> str:
    """Best-effort text extraction from a Gmail message payload: text/plain, else the HTML part with tags stripped.

    Zero-width and bidi control characters are removed either way (they hide or disguise text).
    """
    text = _find_part(payload, "text/plain")
    if not text:
        html = _find_part(payload, "text/html")
        if not html:
            return ""
        parser = _HtmlText()
        parser.feed(html)
        text = re.sub(r"\n\s*\n+", "\n\n", "".join(parser.out))
    return _INVISIBLE_CHARS.sub("", text)


def _attachment_names(payload: dict, out: list[str] | None = None) -> list[str]:
    """File names of all attachments (any depth). An invoice is often only a PDF name, so the guardrail checks these."""
    out = [] if out is None else out
    name = (payload.get("filename") or "").strip()
    if name and len(out) < 10:
        out.append(name[:100])
    for part in payload.get("parts", []) or []:
        _attachment_names(part, out)
    return out


_AUTOMATED_SENDER = re.compile(r"^(?:no[-_.]?reply|do[-_.]?not[-_.]?reply|mailer[-_.]?daemon|notifications?|newsletters?)\b", re.I)


def is_automated(payload: dict, sender: str) -> bool:
    """Newsletters, mailing lists, auto-replies and no-reply senders: mail no person is waiting on an answer to."""
    if _header(payload, "List-Unsubscribe") or _header(payload, "List-Id"):
        return True
    if _header(payload, "Precedence").strip().lower() in ("bulk", "list", "junk"):
        return True
    auto = _header(payload, "Auto-Submitted").strip().lower()
    if auto and auto != "no":
        return True
    return bool(_AUTOMATED_SENDER.match(sender.split("@")[0]))


def fetch_new_mail(max_results: int = 20) -> int:
    """Pull recent inbox mail into the requests table. Read-only: never modifies the mailbox. Returns count added."""
    gmail = _svc("gmail", "v1")
    me = principal_email().lower()
    q = "in:inbox newer_than:2d -from:me -category:promotions -category:social"
    refs = gmail.users().messages().list(userId="me", q=q, maxResults=max_results).execute()
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
        # Everyone on the thread: the only people the agent may invite or mention without the principal adding them.
        participants = sorted({a.lower() for _, a in getaddresses([_header(p, h) for h in ("From", "To", "Cc")]) if a})
        store.upsert_request(msg["id"], msg["threadId"], _header(p, "Message-ID"), sender, subject, body, received, kind,
                             participants, attachments=_attachment_names(p), automated=is_automated(p, sender))
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
            "attendeeEmails": [a["email"] for a in e.get("attendees", []) if a.get("email")],
            "description": (e.get("description") or "").strip()[:1500],
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
    mins = int(store.get_settings().get("reminderMinutes", 15))
    event["reminders"] = {"useDefault": False, "overrides": [{"method": "popup", "minutes": mins}, {"method": "email", "minutes": mins}]}
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
    today = datetime.now(_tz()).date().isoformat()
    out = []
    for t in items:
        notes = t.get("notes", "")
        owner = re.search(r"Owner: (.+)", notes)
        due = re.search(r"Due: (.+)", notes)
        done = t.get("status") == "completed"
        due_date = t["due"][:10] if t.get("due") else None
        out.append({
            "id": t["id"], "task": t.get("title", ""), "owner": owner.group(1) if owner else "Assistant",
            "due": due.group(1) if due else (due_date or "No date"),
            "done": done, "dueDate": due_date, "overdue": bool(not done and due_date and due_date < today),
        })
    return out


def complete_task(task_id: str) -> None:
    """Mark a follow-up done. It is the principal's own task list, so this needs no approval."""
    _svc("tasks", "v1").tasks().patch(tasklist=_tasklist_id(), task=task_id, body={"status": "completed"}).execute()


# ---- Drive (read-only, for meeting prep) -------------------------------------

_STOP_WORDS = {"meeting", "call", "sync", "catch", "with", "discussion", "review", "update", "weekly", "intro",
               "chat", "quick", "about", "from", "this", "that", "next"}
_GDOC = "application/vnd.google-apps.document"


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")


def search_docs(title: str, attendee_emails: list[str], limit: int = 5) -> list[dict]:
    """Recent Drive files whose name/text matches the meeting title, or that an attendee owns. Read-only."""
    try:
        me = principal_email().lower()
    except NotConnected:
        me = ""
    words = [w for w in re.findall(r"[A-Za-z0-9]{4,}", title) if w.lower() not in _STOP_WORDS][:4]
    emails = [e for e in attendee_emails if e.lower() != me][:4]
    clauses = ([f"name contains '{_esc(w)}'" for w in words] + [f"fullText contains '{_esc(w)}'" for w in words]
               + [f"'{_esc(e)}' in owners" for e in emails])
    if not clauses:
        return []
    since = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%S")
    q = (f"trashed = false and modifiedTime > '{since}' and mimeType != 'application/vnd.google-apps.folder' "
         f"and ({' or '.join(clauses)})")
    res = _svc("drive", "v3").files().list(
        q=q, orderBy="modifiedTime desc", pageSize=limit, fields="files(id,name,mimeType,webViewLink,modifiedTime)",
    ).execute()
    return [{"id": f["id"], "name": f["name"], "url": f.get("webViewLink"), "modified": f["modifiedTime"][:10],
             "mimeType": f["mimeType"]} for f in res.get("files", [])]


def doc_text(file: dict, limit: int = 3000) -> str:
    """Plain text of a Google Doc (other file types are linked only). Never leaves the server except to the principal."""
    if file.get("mimeType") != _GDOC:
        return ""
    data = _svc("drive", "v3").files().export(fileId=file["id"], mimeType="text/plain").execute()
    text = data.decode("utf-8", "replace") if isinstance(data, bytes) else str(data)
    return text.strip()[:limit]
