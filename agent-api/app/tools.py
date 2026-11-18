"""Tools the Gemini agent can call, plus the code-level guardrails.

Every tool only *proposes* something. There is deliberately no send/book/pay tool:
those side effects happen in main.py when the principal approves.
All tools return plain dicts; errors come back as {"error": ...} so the model can correct itself.
"""

import re

from app import google_api, store
from app.store import add_approval, get_request, log


def _mins(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _hhmm(mins: int) -> str:
    return f"{mins // 60:02d}:{mins % 60:02d}"


def _busy(day: int) -> list[tuple[int, int]]:
    """Booked meetings plus still-pending meeting proposals on a day."""
    busy = [(_mins(m["start"]), _mins(m["end"])) for m in google_api.list_meetings(day, day) if not m["allDay"]]
    busy += [
        (_mins(a["start"]), _mins(a["end"]))
        for a in store.list_approvals()
        if a["type"] == "meeting" and a["status"] == "pending" and a["day"] == day
    ]
    return busy


# ---- code-level guardrail -------------------------------------------------

_PAYMENT = re.compile(r"invoice|payment|\bpay\b|wire transfer|\bRs\b|₹|\bINR\b", re.I)
_TRAVEL = re.compile(r"flight|hotel|airline|boarding|itinerary|train ticket", re.I)


def classify_sensitive(req: dict) -> str | None:
    """Return 'payment' | 'travel' | 'sensitive' if the request must be escalated, else None.

    Runs in code before the model sees the request, so the model cannot talk its way past it.
    """
    text = f"{req['subject']} {req['body']}"
    if _TRAVEL.search(text):
        return "travel"
    if _PAYMENT.search(text):
        return "payment"
    if any(k.lower() in text.lower() for k in store.get_settings()["sensitiveKeywords"]):
        return "sensitive"
    return None


# ---- tools exposed to the model ------------------------------------------


def get_calendar(from_day: int, to_day: int) -> dict:
    """List booked meetings between two day offsets (0 = today, 1 = tomorrow), inclusive.

    Args:
        from_day: First day offset.
        to_day: Last day offset.
    """
    meetings = google_api.list_meetings(from_day, to_day)
    return {"meetings": sorted(meetings, key=lambda m: (m["day"], m["start"]))}


def find_free_slots(day: int, duration_min: int) -> dict:
    """Find free start times on a day, inside working hours, that do not clash with any meeting or pending proposal.

    Args:
        day: Day offset (0 = today, 1 = tomorrow).
        duration_min: Meeting length in minutes.
    """
    wh = store.get_settings()["workingHours"]
    start, end = _mins(wh["start"]), _mins(wh["end"])
    busy = _busy(day)
    slots = []
    t = start
    while t + duration_min <= end:
        if all(t + duration_min <= b0 or t >= b1 for b0, b1 in busy):
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
        attendees: Names or emails of attendees.
    """
    req = get_request(request_id)
    if not req:
        return {"error": f"unknown request {request_id}"}
    if req["triage"] == "sensitive" or classify_sensitive(req):
        return {"error": "sensitive requests cannot be scheduled; use escalate"}
    try:
        s, e = _mins(start), _mins(end)
    except ValueError:
        return {"error": "start and end must be HH:MM"}
    wh = store.get_settings()["workingHours"]
    if not (_mins(wh["start"]) <= s < e <= _mins(wh["end"])):
        return {"error": f"outside working hours {wh['start']}-{wh['end']}"}
    if day < 0:
        return {"error": "day must be today or later"}
    for b0, b1 in _busy(day):
        if s < b1 and e > b0:
            return {"error": f"clashes with another meeting at {_hhmm(b0)}-{_hhmm(b1)}; call find_free_slots"}
    a = add_approval(
        "meeting",
        f"Book {title} - day {day} {start}-{end}",
        request_id=request_id,
        draft=f"Invite: {title}, {start}-{end}, with {', '.join(attendees)}.",
        title=title, day=day, start=start, end=end, attendees=attendees,
    )
    return {"ok": True, "approvalId": a["id"]}


def draft_reply(request_id: str, body: str) -> dict:
    """Draft a reply to a routine email for the principal's approval. It is NOT sent.

    Args:
        request_id: The request being answered.
        body: The reply text.
    """
    req = get_request(request_id)
    if not req:
        return {"error": f"unknown request {request_id}"}
    if req["triage"] == "sensitive" or classify_sensitive(req):
        return {"error": "sensitive requests cannot be answered with a draft; use escalate"}
    a = add_approval("reply", f"Reply to: {req['subject']}", request_id=request_id, draft=body)
    return {"ok": True, "approvalId": a["id"]}


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
