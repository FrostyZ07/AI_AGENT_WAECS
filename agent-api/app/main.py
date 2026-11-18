import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app import agent, google_api, store
from app.store import log

load_dotenv()
UI_URL = os.getenv("UI_URL", "http://localhost:3000")
scheduler = BackgroundScheduler()


def _poll_inbox() -> None:
    agent.process_inbox()


def _daily_brief() -> None:
    agent.generate_brief(email=True)


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
    scheduler.add_job(_safe(_daily_brief), "cron", hour=int(hh), minute=int(mm), timezone=s["timezone"],
                      id="brief", replace_existing=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.getenv("SCHEDULER_ENABLED") == "1":
        reschedule()
        scheduler.start()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Executive Assistant Agent API", lifespan=lifespan)


class Decision(BaseModel):
    status: str  # "approved" | "rejected"


class WorkingHours(BaseModel):
    start: str
    end: str


class Settings(BaseModel):
    workingHours: WorkingHours
    sensitiveKeywords: list[str]
    replyTemplates: list[str]
    timezone: str = "Asia/Kolkata"
    briefTime: str = "08:00"
    pollMinutes: int = 10


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


@app.get("/state")
def state():
    g = google_api.status()
    meetings, follow_ups = [], []
    if g["connected"]:
        try:
            meetings = google_api.list_meetings(0, 7)
            follow_ups = google_api.list_follow_ups()
        except Exception as e:  # show the app with an empty calendar rather than a blank error page
            log("state_google_error", error=str(e)[:300])
    return {
        "requests": store.list_requests(), "meetings": meetings, "approvals": store.list_approvals(),
        "followUps": follow_ups, "settings": store.get_settings(), "brief": store.get_brief(), "google": g,
    }


@app.post("/process-inbox")
def process_inbox():
    return _run(agent.process_inbox)


@app.post("/brief")
def brief():
    return _run(agent.generate_brief)


def _apply_approved(a: dict) -> str | None:
    """Perform the real side effect for an approved item. Returns a Google ref, or None. Raises on failure."""
    if a["type"] == "meeting":
        # Re-check against the live calendar: it may have changed since the proposal was made.
        for m in google_api.list_meetings(a["day"], a["day"]):
            if not m["allDay"] and a["start"] < m["end"] and a["end"] > m["start"]:
                raise HTTPException(409, f"Clashes with '{m['title']}' ({m['start']}-{m['end']}). Reject this and re-run the inbox.")
        return google_api.create_event(a["title"], a["day"], a["start"], a["end"], a["attendees"] or [])
    if a["type"] == "reply":
        req = store.get_request(a["requestId"])
        if not req:
            raise HTTPException(404, "original request not found")
        return google_api.send_reply(req, a["draft"] or "")
    return None  # payment / travel / sensitive: sign-off is recorded only. Code never pays or books.


@app.post("/approvals/{approval_id}")
def decide(approval_id: str, body: Decision):
    if body.status not in ("approved", "rejected"):
        raise HTTPException(400, "status must be approved or rejected")
    a = store.get_approval(approval_id)
    if not a:
        raise HTTPException(404, "approval not found")
    if a["status"] != "pending":
        raise HTTPException(409, f"already {a['status']}")
    if body.status == "approved":
        # Side effect first: if Google fails the approval stays pending and can be retried.
        ref = _run(lambda: _apply_approved(a))
        store.update_approval(approval_id, status="approved", **({"googleRef": ref} if ref else {}))
        log("approval_decided", approvalId=approval_id, status="approved", googleRef=ref)
        if ref is None:
            log("signoff_recorded", approvalId=approval_id, type=a["type"])
    else:
        store.update_approval(approval_id, status="rejected")
        log("approval_decided", approvalId=approval_id, status="rejected")
    return store.get_approval(approval_id)


@app.put("/settings")
def save_settings(s: Settings):
    saved = store.save_settings(s.model_dump())
    log("settings_saved")
    if scheduler.running:
        reschedule()
    return saved


@app.get("/oauth/google/start")
def google_start():
    return RedirectResponse(_run(google_api.auth_url))


@app.get("/oauth/google/callback")
def google_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error or not code or not state:
        return RedirectResponse(f"{UI_URL}/settings?google_error={error or 'missing_code'}")
    try:
        google_api.finish_auth(code, state)
    except Exception as e:
        return RedirectResponse(f"{UI_URL}/settings?google_error={str(e)[:120]}")
    return RedirectResponse(f"{UI_URL}/settings?connected=1")
