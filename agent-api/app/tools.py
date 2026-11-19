"""Tools the Gemini agent can call, plus the code-level guardrails.

Every tool only *proposes* something. There is deliberately no send/book/pay tool:
those side effects happen in main.py when the principal approves.
All tools return plain dicts; errors come back as {"error": ...} so the model can correct itself.
"""

import os
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app import google_api, store
from app.store import add_approval, get_request, log

MAX_DAYS_AHEAD = 60
_OPEN = ("pending", "approving", "approved")


def _mins(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _hhmm(mins: int) -> str:
    return f"{mins // 60:02d}:{mins % 60:02d}"


def now() -> datetime:
    """Current time in the principal's timezone. The one clock the guardrails use (tests replace it)."""
    return datetime.now(ZoneInfo(store.get_settings()["timezone"]))


def today() -> date:
    return now().date()


def slot_start(day: date | int, hhmm: str) -> datetime:
    """Absolute start of a slot: a date (or day offset from today) plus "HH:MM", in the principal's timezone."""
    d = today() + timedelta(days=day) if isinstance(day, int) else day
    h, m = hhmm.split(":")
    return datetime(d.year, d.month, d.day, int(h), int(m), tzinfo=now().tzinfo)


def _earliest() -> datetime:
    """The first moment the agent may propose a meeting for: now plus the minimum-notice setting."""
    return now() + timedelta(minutes=int(store.get_settings().get("minNoticeMinutes", 120)))


def _is_working_day(day: int) -> bool:
    days = store.get_settings().get("workingDays", [0, 1, 2, 3, 4])
    return (today() + timedelta(days=day)).weekday() in days


def _busy(day: int) -> list[tuple[int, int]]:
    """Booked meetings plus still-open meeting proposals on a day."""
    target = (today() + timedelta(days=day)).isoformat()
    busy = [(_mins(m["start"]), _mins(m["end"])) for m in google_api.list_meetings(day, day) if not m["allDay"]]
    for a in store.list_approvals():
        if a["type"] == "meeting" and a["status"] in ("pending", "approving"):
            md = a.get("meetingDate")
            if md == target or (md is None and a["day"] == day):
                busy.append((_mins(a["start"]), _mins(a["end"])))
    return busy


def _open_approval(request_id: str, type_: str) -> dict | None:
    return next((a for a in store.list_approvals()
                 if a["requestId"] == request_id and a["type"] == type_ and a["status"] in _OPEN), None)


# ---- code-level guardrail -------------------------------------------------

# "bill"/"receipt" only as document numbers (Bill_0042.pdf, receipt #12): "Hi Bill" or "confirming receipt" are not payments.
_PAYMENT = re.compile(r"invoice|payment|\bpay\b|wire transfer|\bRs\b|₹|\bINR\b|quotation|purchase.?order"
                      r"|\b(?:inv|bill|receipt)[-_ #]*(?:no\.?\s*)?\d", re.I)
_TRAVEL = re.compile(r"flight|hotel|airline|boarding|itinerary|train ticket", re.I)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def classify_sensitive(req: dict) -> str | None:
    """Return 'payment' | 'travel' | 'sensitive' if the request must be escalated, else None.

    Runs in code before the model sees the request, so the model cannot talk its way past it.
    Attachment file names count too: an invoice often arrives as "INV-0042.pdf" under a bland subject.
    """
    text = f"{req['subject']} {req['body']} {' '.join(req.get('attachments') or [])}"
    if _TRAVEL.search(text):
        return "travel"
    if _PAYMENT.search(text):
        return "payment"
    if any(k.lower() in text.lower() for k in store.get_settings()["sensitiveKeywords"]):
        return "sensitive"
    return None


def _principal() -> str | None:
    try:
        return google_api.principal_email().lower()
    except Exception:
        return None


def _known_addresses(req: dict) -> set[str]:
    known = {p.lower() for p in (req.get("participants") or [])} | {req["from"].lower()}
    me = _principal()
    if me:
        known.add(me)
    return known


def disallowed_attendees(attendees: list[str], req: dict) -> list[str]:
    """Email attendees the model may not invite: not on the thread, not the principal, not an allowed domain.

    A prompt-injected email must not be able to get an invite sent to an outsider. The principal can still add anyone
    by editing the approval card. Plain names (no @) only go into the event description, so they pass.
    """
    known = _known_addresses(req)
    domains = {d.lower().lstrip("@") for d in store.get_settings().get("attendeeAllowDomains", [])}
    bad = []
    for a in attendees:
        e = a.strip().lower()
        if _EMAIL.fullmatch(e) and e not in known and e.split("@")[1] not in domains:
            bad.append(a)
    return bad


def leak_check(text: str, req: dict) -> str | None:
    """Reason a draft to a third party must not be offered for approval, or None if it is clean.

    Drafts may not carry sensitive/payment/travel content, other people's addresses, or titles of calendar entries.
    """
    if classify_sensitive({"subject": "", "body": text}):
        return "it mentions sensitive, payment or travel content"
    known = _known_addresses(req)
    for e in _EMAIL.findall(text):
        if e.lower() not in known:
            return f"it mentions {e}, who is not on this thread"
    try:
        meetings = google_api.list_meetings(0, 14)
    except Exception as e:  # the human approval still stands; record that this check did not run
        log("leak_check_skipped", error=str(e)[:200])
        meetings = []
    low = text.lower()
    for m in meetings:
        t = (m.get("title") or "").strip().lower()
        if len(t) >= 4 and t in low:
            return "it mentions a calendar entry"
    return None


def _alert_principal(category: str, req: dict) -> None:
    """Tell the principal straight away (own inbox, no mail body) that something needs their sign-off."""
    if not store.get_settings().get("escalationAlerts", True):
        return
    try:
        ui = os.getenv("UI_URL", "http://localhost:3000")
        google_api.send_to_self(
            f"Needs your sign-off: {category}",
            f"A {category} item from {req['from']} needs your sign-off.\nSubject: {req['subject']}\nReview it: {ui}/approvals",
        )
        log("escalation_alert_sent", requestId=req["id"], category=category)
    except Exception as e:
        log("escalation_alert_failed", requestId=req["id"], error=str(e)[:200])


# ---- tools exposed to the model ------------------------------------------


def get_calendar(from_day: int, to_day: int) -> dict:
    """List the busy time blocks between two day offsets (0 = today, 1 = tomorrow), inclusive. Titles and attendees are not shown.

    Args:
        from_day: First day offset.
        to_day: Last day offset.
    """
    meetings = google_api.list_meetings(from_day, to_day)
    busy = [{"day": m["day"], "start": m["start"], "end": m["end"], "allDay": m["allDay"]} for m in meetings]
    return {"busy": sorted(busy, key=lambda b: (b["day"], b["start"]))}


def find_free_slots(day: int, duration_min: int) -> dict:
    """Find free start times on a working day, inside working hours, that do not clash with any meeting or pending
    proposal and give the principal enough notice.

    Args:
        day: Day offset (0 = today, 1 = tomorrow).
        duration_min: Meeting length in minutes.
    """
    if not _is_working_day(day):
        return {"day": day, "freeSlots": [], "note": "not a working day; try another day"}
    wh = store.get_settings()["workingHours"]
    start, end = _mins(wh["start"]), _mins(wh["end"])
    busy = _busy(day)
    earliest = _earliest()
    slots = []
    t = start
    while t + duration_min <= end:
        if slot_start(day, _hhmm(t)) >= earliest and all(t + duration_min <= b0 or t >= b1 for b0, b1 in busy):
            slots.append({"start": _hhmm(t), "end": _hhmm(t + duration_min)})
        t += 30
    return {"day": day, "freeSlots": slots}


def set_triage(request_id: str, triage: str, reason: str) -> dict:
    """Record whether a request is routine or sensitive.

    Args:
        request_id: The request id.
        triage: Either "routine" or "sensitive".
        reason: One short sentence.
    """
    req = get_request(request_id)
    if not req:
        return {"error": f"unknown request {request_id}"}
    if triage not in ("routine", "sensitive"):
        return {"error": "triage must be 'routine' or 'sensitive'"}
    if triage == "routine" and classify_sensitive(req):
        triage = "sensitive"  # guardrail: the model may not downgrade a flagged request
        reason = "Forced sensitive by guardrail rules."
    store.update_request(request_id, triage=triage)
    log("triage", requestId=request_id, triage=triage, reason=reason)
    return {"ok": True, "triage": triage}


def propose_meeting(request_id: str, title: str, day: int, start: str, end: str, attendees: list[str]) -> dict:
    """Propose a meeting for the principal's approval. Fails if it clashes or is outside working hours.

    Args:
        request_id: The request that asked for the meeting.
        title: Meeting title.
        day: Day offset (0 = today, 1 = tomorrow).
        start: Start time "HH:MM" (24h).
        end: End time "HH:MM" (24h).
        attendees: Names or emails of attendees. Emails must be people on the email thread.
    """
    req = get_request(request_id)
    if not req:
        return {"error": f"unknown request {request_id}"}
    if req["triage"] == "sensitive" or classify_sensitive(req):
        return {"error": "sensitive requests cannot be scheduled; use escalate"}
    existing = _open_approval(request_id, "meeting")
    if existing:
        return {"ok": True, "note": "already proposed", "approvalId": existing["id"]}
    try:
        s, e = _mins(start), _mins(end)
    except ValueError:
        return {"error": "start and end must be HH:MM"}
    wh = store.get_settings()["workingHours"]
    if not (_mins(wh["start"]) <= s < e <= _mins(wh["end"])):
        return {"error": f"outside working hours {wh['start']}-{wh['end']}"}
    if day < 0:
        return {"error": "day must be today or later"}
    if day > MAX_DAYS_AHEAD:
        return {"error": f"day must be within {MAX_DAYS_AHEAD} days"}
    if not _is_working_day(day):
        return {"error": "that is not a working day; call find_free_slots for another day"}
    if slot_start(day, start) < now():
        return {"error": "that time has already passed; call find_free_slots"}
    if slot_start(day, start) < _earliest():
        return {"error": "too soon: the principal needs more notice; call find_free_slots"}
    bad = disallowed_attendees(attendees, req)
    if bad:
        return {"error": f"{', '.join(bad)} are not on the email thread; only invite people from the thread"}
    for b0, b1 in _busy(day):
        if s < b1 and e > b0:
            return {"error": f"clashes with another meeting at {_hhmm(b0)}-{_hhmm(b1)}; call find_free_slots"}
    d = today() + timedelta(days=day)
    a = add_approval(
        "meeting",
        f"Book {title} - {d.strftime('%a %d %b')} {start}-{end}",
        request_id=request_id,
        draft=f"Invite: {title}, {start}-{end}, with {', '.join(attendees)}.",
        title=title, day=day, start=start, end=end, attendees=attendees, meeting_date=d.isoformat(),
    )
    return {"ok": True, "approvalId": a["id"], **({"note": "already proposed"} if a.get("duplicate") else {})}


def draft_reply(request_id: str, body: str) -> dict:
    """Draft a reply to a routine email for the principal's approval. It is NOT sent.

    Args:
        request_id: The request being answered.
        body: The reply text. Use only template wording and the sender's own message; no calendar details.
    """
    req = get_request(request_id)
    if not req:
        return {"error": f"unknown request {request_id}"}
    if req["triage"] == "sensitive" or classify_sensitive(req):
        return {"error": "sensitive requests cannot be answered with a draft; use escalate"}
    existing = _open_approval(request_id, "reply")
    if existing:
        return {"ok": True, "note": "already drafted", "approvalId": existing["id"]}
    why = leak_check(body, req)
    if why:
        log("leak_blocked", requestId=request_id, reason=why)
        return {"error": f"draft blocked: {why}. Rewrite it using only the template wording."}
    a = add_approval("reply", f"Reply to: {req['subject']}", request_id=request_id, draft=body)
    return {"ok": True, "approvalId": a["id"], **({"note": "already drafted"} if a.get("duplicate") else {})}


def escalate(request_id: str, category: str, summary: str) -> dict:
    """Escalate to the principal: sensitive mail, a payment, or a travel booking. Nothing is done on their behalf.

    Args:
        request_id: The request being escalated.
        category: One of "sensitive", "payment", "travel".
        summary: One neutral line for the principal. Do not copy confidential details.
    """
    req = get_request(request_id)
    if not req:
        return {"error": f"unknown request {request_id}"}
    if category not in ("sensitive", "payment", "travel"):
        return {"error": "category must be sensitive, payment or travel"}
    if any(a["requestId"] == request_id and a["type"] == category for a in store.list_approvals()):
        return {"ok": True, "note": "already escalated"}
    store.update_request(request_id, triage="sensitive")
    a = add_approval(category, f"{summary[:200]} (from {req['from']})", request_id=request_id)
    if not a.get("duplicate"):
        _alert_principal(category, req)
    return {"ok": True, "approvalId": a["id"]}


def add_follow_up(task: str, owner: str, due: str) -> dict:
    """Add a follow-up to the tracker.

    Args:
        task: What needs doing.
        owner: "Assistant" or "Principal".
        due: When, e.g. "Today", "Tomorrow", "Friday".
    """
    task_id = google_api.add_task(task, owner, due)
    log("follow_up_added", followUpId=task_id, task=task)
    return {"ok": True, "id": task_id}


TOOLS = [get_calendar, find_free_slots, set_triage, propose_meeting, draft_reply, escalate, add_follow_up]
TOOL_MAP = {fn.__name__: fn for fn in TOOLS}
