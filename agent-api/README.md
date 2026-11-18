# agent-api

Python (FastAPI + Gemini) backend for the Executive Assistant Agent. Phase 3: real Gmail / Google Calendar / Google Tasks, state in Supabase Postgres, optional scheduler.

## One-time setup
1. **Google Cloud**: enable the Gmail, Google Calendar and Google Tasks APIs. Configure the OAuth consent screen (External, Testing) and add the principal as a test user. Create an OAuth client of type *Web application* with redirect URI `http://localhost:8000/oauth/google/callback`.
2. **Supabase**: create a project, run `schema.sql` in the SQL editor, copy the Session pooler connection string.
3. `cp .env.example .env` and fill `GEMINI_API_KEY`, `DATABASE_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`.

## Run
```
uv run uvicorn app.main:app --reload --port 8000
```
Then the UI in `../exec-assistant` (`npm run dev`), open Settings and click **Connect Google**.
Set `SCHEDULER_ENABLED=1` to poll the inbox every N minutes and email the daily brief (both set in Settings). Use `--reload` off when the scheduler is on, or jobs run twice.

## Test
`uv run pytest` runs the guardrail tests (no network or database needed).

## Files
`store.py` (Postgres), `google_api.py` (all Google calls), `prompt.py` (role prompt), `tools.py` (tools + guardrails), `agent.py` (Gemini loop, brief), `main.py` (routes, approvals, OAuth, scheduler).

## Guardrails
No tool sends, books or pays. Replies and invites happen only in `POST /approvals/{id}` after the principal approves (a failed send leaves the item pending). Payment, travel and sensitive items only record sign-off. Mail is read-only; the daily brief goes only to the principal's own inbox.
