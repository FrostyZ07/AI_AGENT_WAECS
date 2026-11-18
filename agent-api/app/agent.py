"""Gemini agent loop. Function calling is run by hand so every call is guarded and logged."""

import json
import os
import threading

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app import google_api, store
from app.prompt import BRIEF_PROMPT, build_system_prompt
from app.store import log
from app.tools import TOOL_MAP, TOOLS, classify_sensitive, escalate

load_dotenv()

MAX_STEPS = 6

# A manual run and a scheduled run must not process the same mail twice.
_inbox_lock = threading.Lock()


class MissingKey(RuntimeError):
    pass


def _client() -> genai.Client:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise MissingKey("GEMINI_API_KEY is not set. Add it to agent-api/.env and restart the API.")
    return genai.Client(api_key=key)


def _model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


def process_request(client: genai.Client, req: dict) -> None:
    forced = classify_sensitive(req)  # guardrail runs in code, before the model
    prompt = f"From: {req['from']}\nSubject: {req['subject']}\nType: {req['kind']}\n\n{req['body']}\n\nRequest id: {req['id']}"
    if forced:
        prompt += f"\n\nGUARDRAIL: this is flagged '{forced}'. Triage it sensitive and call escalate with category '{forced}'. Do not draft or schedule."

    config = types.GenerateContentConfig(
        system_instruction=build_system_prompt(store.get_settings()),
        tools=TOOLS,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]

    for _ in range(MAX_STEPS):
        resp = client.models.generate_content(model=_model(), contents=contents, config=config)
        calls = resp.function_calls or []
        if not calls:
            log("agent_done", requestId=req["id"], note=(resp.text or "")[:200])
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
            parts.append(types.Part.from_function_response(name=call.name, response={"result": result}))
        contents.append(types.Content(role="user", parts=parts))
    else:
        log("agent_step_limit", requestId=req["id"])

    # Guardrail backstop: flagged requests must end up escalated, whatever the model did.
    if forced and not any(a["requestId"] == req["id"] and a["type"] == forced for a in store.list_approvals()):
        escalate(req["id"], forced, f"{forced.title()} item: {req['subject']}")
        log("guardrail_escalation", requestId=req["id"], category=forced)


def process_inbox() -> dict:
    """Fetch new Gmail, then run the agent on every unprocessed request."""
    client = _client()
    with _inbox_lock:
        fetched = google_api.fetch_new_mail()
        done, failed = [], []
        for req in store.list_requests():
            if req["processed"]:
                continue
            try:
                process_request(client, req)
                store.update_request(req["id"], processed=True)
                done.append(req["id"])
            except Exception as e:  # keep going; one bad request must not block the rest
                log("agent_error", requestId=req["id"], error=str(e)[:300])
                failed.append({"id": req["id"], "error": str(e)[:300]})
        return {"fetched": fetched, "processed": done, "failed": failed}


def generate_brief(email: bool = False) -> dict:
    client = _client()
    data = {
        "todayMeetings": google_api.list_meetings(0, 0),
        "openFollowUps": [f for f in google_api.list_follow_ups() if not f["done"]],
        "pendingApprovals": [{"type": a["type"], "summary": a["summary"]} for a in store.list_approvals() if a["status"] == "pending"],
    }
    resp = client.models.generate_content(model=_model(), contents=BRIEF_PROMPT.format(data=json.dumps(data, indent=1)))
    brief = store.save_brief(resp.text or "")
    log("brief_generated", emailed=email)
    if email:
        google_api.send_to_self("Your daily brief", brief["text"])  # the principal's own inbox: no approval needed
    return brief
