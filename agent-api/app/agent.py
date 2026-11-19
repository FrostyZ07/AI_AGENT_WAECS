"""Gemini agent loop. Function calling is run by hand so every call is guarded and logged."""

import json
import os
import threading
from datetime import timedelta

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app import google_api, store
from app.prompt import BRIEF_PROMPT, PREP_PROMPT, build_system_prompt, fence
from app.store import log
from app.tools import TOOL_MAP, TOOLS, _alert_principal, classify_sensitive, escalate, today

load_dotenv()

MAX_STEPS = 6
MAX_ATTEMPTS = 3  # a request that errors this many times goes to the principal for review

# A manual run and a scheduled run must not process the same mail twice.
_inbox_lock = threading.Lock()


class MissingKey(RuntimeError):
    pass


def _client() -> genai.Client:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise MissingKey("GEMINI_API_KEY is not set. Add it to agent-api/.env and restart the API.")
    # A hung call would hold the inbox lock forever; transient 429/5xx errors are retried with backoff.
    return genai.Client(api_key=key, http_options=types.HttpOptions(
        timeout=int(os.getenv("GEMINI_TIMEOUT_MS", "60000")),
        retry_options=types.HttpRetryOptions(attempts=3, http_status_codes=[408, 429, 500, 502, 503, 504]),
    ))


def _model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


def flag_for_review(req: dict, reason: str) -> None:
    """Hand a request the agent could not handle to the principal, so no mail is silently dropped."""
    a = store.add_approval("review", f"Needs your review: {req['subject'][:150]} (from {req['from']})", request_id=req["id"])
    log("needs_review", requestId=req["id"], reason=reason[:300])
    if not a.get("duplicate"):
        _alert_principal("review", req)


def _unhandled_reason(resp, handled: set[str], forced: str | None, hit_limit: bool) -> str | None:
    """Why the agent's run did not deal with the request, or None if it did."""
    if hit_limit:
        return f"step limit ({MAX_STEPS}) reached"
    if not resp.candidates:
        return "the model returned no answer"
    finish = resp.candidates[0].finish_reason
    if finish not in (None, types.FinishReason.STOP):
        return f"the model stopped early ({getattr(finish, 'name', finish)})"
    if not forced and not handled & {"set_triage", "escalate"}:  # forced requests are escalated by the backstop
        return "the model did not triage the request"
    return None


def process_request(client: genai.Client, req: dict) -> str | None:
    """Run the agent on one request. Returns why it was left unhandled, or None."""
    forced = classify_sensitive(req)  # guardrail runs in code, before the model
    # Everything the sender controls (From, Subject, body) goes inside the fence: it is data, never instructions.
    files = ", ".join(req.get("attachments") or []) or "none"
    email = fence("EMAIL", f"From: {req['from']}\nSubject: {req['subject']}\nAttachments: {files}\n\n{req['body']}")
    prompt = f"{email}\n\nType: {req['kind']}\nRequest id: {req['id']}"
    if req.get("rejectNote"):  # written by the principal, so it sits outside the fence
        prompt += f"\n\nThe principal REJECTED your earlier proposal for this request. Reason: {req['rejectNote']}\nMake a new proposal that follows this reason."
    if forced:
        prompt += f"\n\nGUARDRAIL: this is flagged '{forced}'. Triage it sensitive and call escalate with category '{forced}'. Do not draft or schedule."

    config = types.GenerateContentConfig(
        system_instruction=build_system_prompt(store.get_settings()),
        tools=TOOLS,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
    handled: set[str] = set()  # tools that ran without an error
    hit_limit = False

    for _ in range(MAX_STEPS):
        resp = client.models.generate_content(model=_model(), contents=contents, config=config)
        calls = resp.function_calls or []
        if not calls:
            log("agent_done", requestId=req["id"], note=(resp.text or "")[:200] if resp.candidates else "")
            break
        contents.append(resp.candidates[0].content)
        parts = []
        for call in calls:
            fn = TOOL_MAP.get(call.name)
            args = dict(call.args or {})
            try:
                result = fn(**args) if fn else {"error": f"unknown tool {call.name}"}
            except TypeError as e:
                result = {"error": f"bad arguments: {e}"}
            log("tool_call", requestId=req["id"], tool=call.name, args=args, result=result)
            if isinstance(result, dict) and "error" not in result:
                handled.add(call.name)
            parts.append(types.Part.from_function_response(name=call.name, response={"result": result}))
        contents.append(types.Content(role="user", parts=parts))
    else:
        hit_limit = True
        log("agent_step_limit", requestId=req["id"])

    # Guardrail backstop: flagged requests must end up escalated, whatever the model did.
    if forced and not any(a["requestId"] == req["id"] and a["type"] == forced for a in store.list_approvals()):
        escalate(req["id"], forced, f"{forced.title()} item: {req['subject']}")
        log("guardrail_escalation", requestId=req["id"], category=forced)

    return _unhandled_reason(resp, handled, forced, hit_limit)


def process_inbox() -> dict:
    """Fetch new Gmail, then run the agent on every unprocessed request. Returns {"busy": True} if a run is in progress."""
    client = _client()
    if not _inbox_lock.acquire(blocking=False):  # never queue behind a running (or stuck) run
        return {"busy": True}
    try:
        fetched = google_api.fetch_new_mail()
        done, failed, review, skipped = [], [], [], []
        for req in store.list_requests():
            if req["processed"]:
                continue
            # Newsletters and no-reply mail need no answer. An automated invoice or itinerary still goes through,
            # so the payment/travel sign-off rule keeps applying.
            if req.get("automated") and not classify_sensitive(req):
                store.update_request(req["id"], processed=True, kind="bulk")
                skipped.append(req["id"])
                continue
            try:
                unhandled = process_request(client, req)
                if unhandled:
                    flag_for_review(req, unhandled)
                    review.append(req["id"])
                store.update_request(req["id"], processed=True, reject_note=None)
                done.append(req["id"])
            except Exception as e:  # keep going; one bad request must not block the rest
                err = str(e)[:300]
                log("agent_error", requestId=req["id"], error=err)
                failed.append({"id": req["id"], "error": err})
                try:  # stop retrying (and paying for) a request that keeps failing: the principal takes it
                    if store.bump_attempts(req["id"]) >= MAX_ATTEMPTS:
                        flag_for_review(req, f"failed {MAX_ATTEMPTS} times: {err}")
                        store.update_request(req["id"], processed=True, reject_note=None)
                        review.append(req["id"])
                except Exception as e2:
                    log("review_flag_error", requestId=req["id"], error=str(e2)[:300])
        if skipped:
            log("mail_skipped", count=len(skipped))
        return {"fetched": fetched, "processed": done, "failed": failed, "review": review, "skipped": skipped}
    finally:
        _inbox_lock.release()


def prepare_meeting(client: genai.Client, event: dict) -> dict:
    """Find related Drive docs for a meeting and write a short prep note. Both go only to the principal (UI + brief)."""
    try:
        docs = google_api.search_docs(event["title"], event.get("attendeeEmails", []))
    except Exception as e:  # e.g. Drive scope not granted yet: still write a note from the event itself
        log("prep_docs_unavailable", eventId=event["id"], error=str(e)[:200])
        docs = []
    excerpts = []
    for d in docs[:3]:
        try:
            text = google_api.doc_text(d)
        except Exception:
            text = ""
        if text:
            excerpts.append(fence(f"DOC {d['name']}", text))
    day = today() + timedelta(days=event["day"])
    prompt = PREP_PROMPT.format(
        title=" ".join(event["title"].split())[:120], when=f"{day.isoformat()} {event['start']}-{event['end']}",
        attendees=", ".join(event["attendees"]),
        description=fence("EVENT DESCRIPTION", event.get("description") or "(none)"),
        docs="\n\n".join(excerpts) or "No linked documents found.",
    )
    resp = client.models.generate_content(model=_model(), contents=prompt)
    note = (resp.text or "").strip()
    links = [{k: d[k] for k in ("id", "name", "url", "modified")} for d in docs]
    store.save_prep(event["id"], day.isoformat(), note, links)
    log("meeting_prepared", eventId=event["id"], docs=len(links))
    return {"note": note, "docs": links}


def prepare_upcoming(force: bool = False) -> dict:
    """Prep today's and tomorrow's meetings that have guests. Skips ones prepared in the last 12 hours."""
    client = _client()
    done = skipped = failed = 0
    for event in google_api.list_meetings(0, 1):
        if event["allDay"] or not event.get("attendeeEmails"):
            continue
        if not force and store.prep_is_fresh(event["id"]):
            skipped += 1
            continue
        try:
            prepare_meeting(client, event)
            done += 1
        except Exception as e:  # one bad meeting must not stop the rest
            log("prep_error", eventId=event["id"], error=str(e)[:300])
            failed += 1
    return {"prepared": done, "skipped": skipped, "failed": failed}


def generate_brief(email: bool = False) -> dict:
    client = _client()
    meetings = store.attach_prep(google_api.list_meetings(0, 0))
    open_items = [f for f in google_api.list_follow_ups() if not f["done"]]
    data = {
        "todayMeetings": [
            {"title": m["title"], "start": m["start"], "end": m["end"], "attendees": m["attendees"],
             "prepNote": m.get("prepNote"), "linkedDocs": [d["name"] for d in m.get("docs", [])]}
            for m in meetings
        ],
        "overdueFollowUps": [{"task": f["task"], "owner": f["owner"], "due": f["due"]} for f in open_items if f["overdue"]],
        "openFollowUps": [{"task": f["task"], "owner": f["owner"], "due": f["due"]} for f in open_items if not f["overdue"]],
        "pendingApprovals": [{"type": a["type"], "summary": a["summary"]} for a in store.list_approvals() if a["status"] == "pending"],
    }
    resp = client.models.generate_content(
        model=_model(), contents=BRIEF_PROMPT.format(data=fence("DATA", json.dumps(data, indent=1))))
    brief = store.save_brief(resp.text or "")
    log("brief_generated", emailed=email)
    if email:
        google_api.send_to_self("Your daily brief", brief["text"])  # the principal's own inbox: no approval needed
    return brief
