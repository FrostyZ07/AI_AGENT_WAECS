"""Guardrail tests. No network, no database: store and google_api are replaced with in-memory fakes."""

import pytest
from fastapi.testclient import TestClient

from app import google_api, main, store, tools

SETTINGS = {
    "workingHours": {"start": "09:00", "end": "18:00"},
    "sensitiveKeywords": ["confidential", "contract", "salary"],
    "replyTemplates": [],
    "timezone": "Asia/Kolkata", "briefTime": "08:00", "pollMinutes": 10,
}


def req(id_, subject, body="hello", triage="routine"):
    return {"id": id_, "from": "x@y.com", "subject": subject, "body": body, "kind": "mail", "triage": triage,
            "processed": False, "threadId": "t1", "messageId": "<m@y>"}


@pytest.fixture
def fake(monkeypatch):
    db = {"requests": {}, "approvals": [], "meetings": [], "sent": [], "events": []}

    def add_approval(type_, summary, request_id=None, draft=None, **extra):
        a = {"id": str(len(db["approvals"]) + 1), "type": type_, "summary": summary, "draft": draft, "status": "pending",
             "requestId": request_id, "title": None, "day": None, "start": None, "end": None, "attendees": None, **extra}
        db["approvals"].append(a)
        return a

    def update_approval(aid, **f):
        a = next(x for x in db["approvals"] if x["id"] == aid)
        a.update(f)

    def update_request(rid, **f):
        db["requests"][rid].update(f)

    monkeypatch.setattr(main, "log", lambda *a, **k: None)
    for mod in (store, tools):
        monkeypatch.setattr(mod, "get_request", lambda rid: db["requests"].get(rid), raising=False)
        monkeypatch.setattr(mod, "add_approval", add_approval, raising=False)
        monkeypatch.setattr(mod, "log", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(store, "get_settings", lambda: SETTINGS)
    monkeypatch.setattr(store, "list_approvals", lambda: db["approvals"])
    monkeypatch.setattr(store, "get_approval", lambda aid: next((a for a in db["approvals"] if a["id"] == aid), None))
    monkeypatch.setattr(store, "update_approval", update_approval)
    monkeypatch.setattr(store, "update_request", update_request)
    monkeypatch.setattr(google_api, "list_meetings", lambda a, b: [m for m in db["meetings"] if a <= m["day"] <= b])
    monkeypatch.setattr(google_api, "send_reply", lambda r, body: db["sent"].append(body) or "msg1")
    monkeypatch.setattr(google_api, "create_event", lambda *a: db["events"].append(a) or "ev1")
    monkeypatch.setattr(main.store, "get_request", lambda rid: db["requests"].get(rid))
    return db


def test_classify_flags_payment_travel_and_keywords(fake):
    assert tools.classify_sensitive(req("a", "Invoice #1", "pay Rs 500")) == "payment"
    assert tools.classify_sensitive(req("b", "Flight options")) == "travel"
    assert tools.classify_sensitive(req("c", "Hi", "this is confidential")) == "sensitive"
    assert tools.classify_sensitive(req("d", "Lunch?", "free thursday")) is None


def test_model_cannot_downgrade_flagged_request(fake):
    fake["requests"]["r"] = req("r", "Invoice", "payment due", triage="sensitive")
    fake["requests"]["q"] = req("q", "Invoice", "payment due")
    assert tools.set_triage("q", "routine", "looks fine")["triage"] == "sensitive"


def test_sensitive_requests_cannot_be_drafted_or_scheduled(fake):
    fake["requests"]["s"] = req("s", "Contract", "confidential clause")
    assert "error" in tools.draft_reply("s", "Sure!")
    assert "error" in tools.propose_meeting("s", "Call", 1, "10:00", "10:30", ["x@y.com"])
    assert fake["approvals"] == []


def test_propose_meeting_rejects_clash_and_out_of_hours(fake):
    fake["requests"]["m"] = req("m", "Catch up", "free thursday?")
    fake["meetings"].append({"day": 1, "start": "10:00", "end": "11:00", "allDay": False})
    assert "clashes" in tools.propose_meeting("m", "Call", 1, "10:30", "11:30", [])["error"]
    assert "working hours" in tools.propose_meeting("m", "Call", 1, "07:00", "07:30", [])["error"]
    assert tools.propose_meeting("m", "Call", 1, "11:00", "11:30", ["x@y.com"])["ok"]


def test_pending_proposal_blocks_the_same_slot(fake):
    fake["requests"]["m"] = req("m", "Catch up", "hello")
    assert tools.propose_meeting("m", "A", 2, "10:00", "10:30", [])["ok"]
    assert "clashes" in tools.propose_meeting("m", "B", 2, "10:00", "10:30", [])["error"]


def test_reject_sends_nothing_and_approve_sends_once(fake):
    fake["requests"]["m"] = req("m", "Question", "how are you")
    tools.draft_reply("m", "Thanks for reaching out.")
    c = TestClient(main.app)
    assert c.post("/approvals/1", json={"status": "rejected"}).status_code == 200
    assert fake["sent"] == []
    assert c.post("/approvals/1", json={"status": "approved"}).status_code == 409  # already decided

    tools.draft_reply("m", "Second draft")
    assert c.post("/approvals/2", json={"status": "approved"}).status_code == 200
    assert fake["sent"] == ["Second draft"]


def test_approving_payment_never_calls_google(fake):
    fake["requests"]["p"] = req("p", "Invoice", "pay Rs 100")
    tools.escalate("p", "payment", "Invoice due")
    assert TestClient(main.app).post("/approvals/1", json={"status": "approved"}).status_code == 200
    assert fake["sent"] == [] and fake["events"] == []


def test_meeting_approval_rechecks_live_calendar(fake):
    fake["requests"]["m"] = req("m", "Catch up", "hello")
    tools.propose_meeting("m", "Call", 1, "10:00", "10:30", [])
    fake["meetings"].append({"day": 1, "title": "New thing", "start": "10:15", "end": "11:00", "allDay": False})
    c = TestClient(main.app)
    assert c.post("/approvals/1", json={"status": "approved"}).status_code == 409
    assert fake["events"] == [] and fake["approvals"][0]["status"] == "pending"
