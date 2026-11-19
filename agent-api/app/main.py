import hmac
import os
import re
from contextlib import asynccontextmanager
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, field_validator, model_validator

from app import agent, google_api, store, tools
from app.store import log

load_dotenv()
UI_URL = os.getenv("UI_URL", "http://localhost:3000")
scheduler = BackgroundScheduler()


def _poll_inbox() -> None:
    agent.process_inbox()


def _brief_failed_alert(error: str) -> None:
    """Tell the principal (own inbox) that today's brief did not go out. Gmail may be the thing that failed: log it."""
    try:
        google_api.send_to_self(
            "Your daily brief failed",
            f"Your daily brief could not be prepared.\nReason: {error[:300]}\nOpen {UI_URL}/brief to generate it by hand.",
        )
        log("brief_failure_alert_sent")
    except Exception as e:
        log("brief_alert_failed", error=str(e)[:300])


def _daily_brief() -> None:
    try:
        agent.prepare_upcoming()  # meeting prep notes first, so the brief can include them
    except Exception as e:
        log("prep_error", error=str(e)[:300])
    try:
        agent.generate_brief(email=True)
    except Exception as e:
        log("brief_failed", error=str(e)[:300])
        _brief_failed_alert(str(e))
        raise  # _safe logs it as a scheduler error too


BRIEF_CHECK_DELAY = 30  # minutes after briefTime


def _brief_watchdog() -> None:
    """Runs BRIEF_CHECK_DELAY minutes after the brief time: if no brief was emailed, try once more (which alerts on failure)."""
    if store.brief_emailed_since(tools.now() - timedelta(minutes=BRIEF_CHECK_DELAY + 30)):
        return
    log("brief_missed")
    _daily_brief()


def _safe(fn):
    def job():
        try:
            fn()
        except Exception as e:  # a failed tick must never kill the scheduler
            log("scheduler_error", job=fn.__name__, error=str(e)[:300])
    return job


def reschedule() -> None:
    """(Re)create the two jobs from current settings. Only used when SCHEDULER_ENABLED=1."""
    s = store.get_settings()
    hh, mm = s["briefTime"].split(":")
    scheduler.add_job(_safe(_poll_inbox), "interval", minutes=int(s["pollMinutes"]), id="poll", replace_existing=True)
    # A busy or briefly paused process would otherwise skip the brief silently (the default grace is 1 second).
    scheduler.add_job(_safe(_daily_brief), "cron", hour=int(hh), minute=int(mm), timezone=s["timezone"],
                      id="brief", replace_existing=True, misfire_grace_time=1800, coalesce=True)
    check = (int(hh) * 60 + int(mm) + BRIEF_CHECK_DELAY) % (24 * 60)
    scheduler.add_job(_safe(_brief_watchdog), "cron", hour=check // 60, minute=check % 60, timezone=s["timezone"],
                      id="brief_check", replace_existing=True, misfire_grace_time=1800, coalesce=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    key = os.getenv("AGENT_API_KEY", "")
    if len(key) < 16:  # nothing here is safe to expose without it: refuse to start
        raise RuntimeError("AGENT_API_KEY is not set (or shorter than 16 characters). Add a long random value to agent-api/.env.")
    if os.getenv("SCHEDULER_ENABLED") == "1":
        reschedule()
        scheduler.start()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


def require_key(x_api_key: str | None = Header(default=None)) -> None:
    """Every route except /health and the OAuth callback needs the shared secret the Next server sends."""
    expected = os.getenv("AGENT_API_KEY", "")
    if not expected:
        raise HTTPException(503, "AGENT_API_KEY is not set on the server")
    if not x_api_key or not hmac.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(401, "Invalid or missing API key")


app = FastAPI(title="Executive Assistant Agent API", lifespan=lifespan)
api = APIRouter(dependencies=[Depends(require_key)])


class Decision(BaseModel):
    status: str  # "approved" | "rejected"
    draft: str | None = None            # edited reply text (approve only)
    attendees: list[str] | None = None  # edited invite list (approve only)
    note: str | None = None             # reason, when rejecting: the agent re-drafts with it
    start: str | None = None            # edited meeting start "HH:MM" (approve only)
    end: str | None = None              # edited meeting end "HH:MM" (approve only)


_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _hhmm(v: str) -> str:
    if not _HHMM.match(v):
        raise ValueError("must be a 24h time like 09:30")
    return v


class WorkingHours(BaseModel):
    start: str
    end: str

    @field_validator("start", "end")
    @classmethod
    def _check(cls, v: str) -> str:
        return _hhmm(v)

    @model_validator(mode="after")
    def _ordered(self):
        if self.start >= self.end:
            raise ValueError("working hours must start before they end")
        return self


class Settings(BaseModel):
    workingHours: WorkingHours
    sensitiveKeywords: list[str]
    replyTemplates: list[str]
    timezone: str = "Asia/Kolkata"
    briefTime: str = "08:00"
    pollMinutes: int = Field(10, ge=5, le=240)
    attendeeAllowDomains: list[str] = []
    reminderMinutes: int = Field(15, ge=0, le=1440)
    escalationAlerts: bool = True
    workingDays: list[int] = [0, 1, 2, 3, 4]  # 0 = Monday ... 6 = Sunday
    minNoticeMinutes: int = Field(120, ge=0, le=1440)

    @field_validator("workingDays")
    @classmethod
    def _days(cls, v: list[int]) -> list[int]:
        if not v or any(d < 0 or d > 6 for d in v):
            raise ValueError("pick at least one working day (0 = Monday ... 6 = Sunday)")
        return sorted(set(v))

    @field_validator("briefTime")
    @classmethod
    def _brief(cls, v: str) -> str:
        return _hhmm(v)

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except Exception:
            raise ValueError("unknown timezone, use a name like Asia/Kolkata")
        return v

    @field_validator("sensitiveKeywords", "replyTemplates", "attendeeAllowDomains")
    @classmethod
    def _clean(cls, v: list[str]) -> list[str]:
        return [x.strip() for x in v if x.strip()]

    @field_validator("attendeeAllowDomains")
    @classmethod
    def _domains(cls, v: list[str]) -> list[str]:
        return [d.lower().lstrip("@") for d in v]


def _run(fn):
    try:
        return fn()
    except HTTPException:
        raise
    except google_api.NotConnected as e:
        raise HTTPException(409, str(e))
    except agent.MissingKey as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        raise HTTPException(502, f"Call failed: {str(e)[:300]}")


@app.get("/health")
def health():
    return {"ok": True}


@api.get("/state")
def state():
    g = google_api.status()
    meetings, follow_ups = [], []
    if g["connected"]:
        try:
            meetings = store.attach_prep(google_api.list_meetings(0, 7))
            follow_ups = google_api.list_follow_ups()
        except Exception as e:  # show the app with an empty calendar rather than a blank error page
            log("state_google_error", error=str(e)[:300])
    return {
        "requests": store.list_requests(), "meetings": meetings, "approvals": store.list_approvals(),
        "followUps": follow_ups, "settings": store.get_settings(), "brief": store.get_brief(), "google": g,
    }


@api.post("/process-inbox")
def process_inbox():
    result = _run(agent.process_inbox)
    if result.get("busy"):
        raise HTTPException(409, "Inbox processing is already running. Try again in a minute.")
    return result


@api.post("/brief")
def brief():
    return _run(agent.generate_brief)


@api.post("/meetings/{event_id}/prep")
def prep_meeting(event_id: str):
    def go():
        client = agent._client()
        event = next((m for m in google_api.list_meetings(0, 14) if m["id"] == event_id), None)
        if not event:
            raise HTTPException(404, "Meeting not found in the next 14 days")
        return agent.prepare_meeting(client, event)
    return _run(go)


@api.post("/follow-ups/{task_id}/done")
def follow_up_done(task_id: str):
    _run(lambda: google_api.complete_task(task_id))  # the principal's own task list: no approval needed
    log("follow_up_done", followUpId=task_id)
    return {"ok": True}


@api.get("/kpis")
def kpis(days: int = 30):
    k = store.kpis(days)
    try:
        items = google_api.list_follow_ups()
        k["followUps"] = {"closed": sum(1 for f in items if f["done"]), "total": len(items)}
    except Exception:  # Google not connected or unreachable: the other KPIs still show
        k["followUps"] = None
    return k


@api.get("/audit")
def audit(limit: int = 100, event: str | None = None):
    return {"entries": store.list_audit(limit, event), "events": store.audit_events()}


def _apply_approved(a: dict, draft: str | None, attendees: list[str]) -> str | None:
    """Perform the real side effect for an approved item. Returns a Google ref, or None. Raises on failure."""
    if a["type"] == "meeting":
        # The proposal pins an absolute date; day offsets go stale if approval happens on a later day.
        day = (date.fromisoformat(a["meetingDate"]) - tools.today()).days if a.get("meetingDate") else a["day"]
        if day < 0:
            raise HTTPException(409, "This meeting's date has passed. Reject it and re-run the inbox.")
        if tools.slot_start(day, a["start"]) < tools.now():  # a["start"] already holds the principal's edit, if any
            raise HTTPException(409, "This time has already passed. Edit the time or reject it.")
        # Re-check against the live calendar: it may have changed since the proposal was made.
        for m in google_api.list_meetings(day, day):
            if not m["allDay"] and a["start"] < m["end"] and a["end"] > m["start"]:
                log("approval_clash", approvalId=a["id"], clashesWith=m.get("title"))
                raise HTTPException(409, f"Clashes with '{m.get('title')}' ({m['start']}-{m['end']}). Reject this and re-run the inbox.")
        return google_api.create_event(a["title"], day, a["start"], a["end"], attendees)
    if a["type"] == "reply":
        req = store.get_request(a["requestId"])
        if not req:
            raise HTTPException(404, "original request not found")
        return google_api.send_reply(req, draft or "")
    return None  # payment / travel / sensitive: sign-off is recorded only. Code never pays or books.


def _resolve_edits(a: dict, body: Decision) -> tuple[str | None, list[str], bool]:
    """What will actually be sent or booked: the principal's edits if any, else the proposal. Returns (draft, attendees, edited)."""
    draft, attendees, edited = a["draft"], list(a["attendees"] or []), False
    if a["type"] == "reply" and body.draft is not None:
        new = body.draft.strip()
        if not new:
            raise HTTPException(422, "The reply is empty.")
        if new != (a["draft"] or "").strip():
            draft, edited = new, True
    elif a["type"] == "meeting":
        if body.start is not None or body.end is not None:
            s, e = body.start or a["start"], body.end or a["end"]
            if not (_HHMM.match(s) and _HHMM.match(e)):
                raise HTTPException(422, "Times must look like 09:30.")
            if s >= e:
                raise HTTPException(422, "The meeting must start before it ends.")
            if (s, e) != (a["start"], a["end"]):
                a["start"], a["end"], edited = s, e, True  # the principal chose this time, so working hours do not apply
        if body.attendees is not None:
            new = [x.strip() for x in body.attendees if x.strip()][:20]
            for x in new:
                if "@" in x and not tools._EMAIL.fullmatch(x):
                    raise HTTPException(422, f"'{x}' is not a valid email address.")
            if new != attendees:  # the principal chose these, so the thread/domain guard does not apply
                attendees, edited = new, True
        else:
            req = store.get_request(a["requestId"]) if a["requestId"] else None
            bad = tools.disallowed_attendees(attendees, req) if req else []
            if bad:
                raise HTTPException(409, f"{', '.join(bad)} are not on the email thread. Edit the attendees to confirm them.")
    return draft, attendees, edited


@api.post("/approvals/{approval_id}")
def decide(approval_id: str, body: Decision):
    if body.status not in ("approved", "rejected"):
        raise HTTPException(400, "status must be approved or rejected")
    a = store.get_approval(approval_id)
    if not a:
        raise HTTPException(404, "approval not found")
    note = (body.note or "").strip()[:500] or None

    def already() -> HTTPException:
        cur = store.get_approval(approval_id)
        return HTTPException(409, f"already {cur['status'] if cur else 'handled'}")

    if body.status == "rejected":
        if not store.reject_approval(approval_id, note):
            raise already()
        if note and a["type"] in ("reply", "meeting") and a["requestId"]:
            store.update_request(a["requestId"], processed=False, reject_note=note)  # the agent re-drafts with the reason
        log("approval_decided", approvalId=approval_id, status="rejected", note=note)
        return store.get_approval(approval_id)

    # Claim first: only one caller can move pending -> approving, so a double click or retry can never send twice.
    if not store.claim_approval(approval_id):
        raise already()
    try:
        draft, attendees, edited = _resolve_edits(a, body)
        ref = _run(lambda: _apply_approved(a, draft, attendees))
    except Exception:
        store.release_approval(approval_id)  # nothing happened: back to pending so it can be retried
        raise
    # From here the side effect has happened. Never release: a row stuck in 'approving' is safer than a second send.
    store.finish_approval(
        approval_id, ref,
        draft=draft if edited and a["type"] == "reply" else None,
        attendees=attendees if edited and a["type"] == "meeting" else None,
        start=a["start"] if a["type"] == "meeting" else None,
        end=a["end"] if a["type"] == "meeting" else None,
        edited=edited,
    )
    log("approval_decided", approvalId=approval_id, status="approved", googleRef=ref, edited=edited,
        **({"original": {"draft": a["draft"], "attendees": a["attendees"]}, "final": {"draft": draft, "attendees": attendees}} if edited else {}))
    if ref is None:
        log("signoff_recorded", approvalId=approval_id, type=a["type"])
    return store.get_approval(approval_id)


@api.put("/settings")
def save_settings(s: Settings):
    saved = store.save_settings(s.model_dump())
    log("settings_saved")
    if scheduler.running:
        reschedule()
    return saved


@api.get("/oauth/google/start")
def google_start():
    # JSON, not a redirect: only a caller holding the API key can start (or replace) the Google connection.
    return {"url": _run(google_api.auth_url)}


@app.get("/oauth/google/callback")  # reached by Google's redirect, so no key; the PKCE state ties it to a start call
def google_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error or not code or not state:
        return RedirectResponse(f"{UI_URL}/settings?google_error={error or 'missing_code'}")
    try:
        google_api.finish_auth(code, state)
    except Exception as e:
        return RedirectResponse(f"{UI_URL}/settings?google_error={str(e)[:120]}")
    return RedirectResponse(f"{UI_URL}/settings?connected=1")


app.include_router(api)
