# agent-api

Python (FastAPI + Gemini) backend for the Executive Assistant Agent. Real Gmail / Google Calendar / Google Tasks / Google Drive (read-only), state in Supabase Postgres, optional scheduler.

## One-time setup
1. **Google Cloud**: enable the Gmail, Google Calendar, Google Tasks and Google Drive APIs. Configure the OAuth consent screen (External, Testing) and add the principal as a test user. Create an OAuth client of type *Web application* with redirect URI `http://localhost:8000/oauth/google/callback`.
2. **Supabase**: create a project and run `schema.sql` in the SQL editor (fresh install). **Existing database:** run `migrations/002_hardening.sql` instead. Copy the Session pooler connection string.
3. `cp .env.example .env` and fill `GEMINI_API_KEY`, `DATABASE_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `AGENT_API_KEY` (a long random value; the API will not start without it).
4. In `../../project` copy `.env.example` to `.env.local` and set `AGENT_API_KEY` (same value), `UI_PASSWORD` and `SESSION_SECRET`.

If Google was connected before Drive access existed, open Settings and click **Reconnect** once (meeting prep needs the read-only Drive scope).

## Run
```
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Then the UI in `../../project` (`pnpm dev`), sign in, open Settings and click **Connect Google**.
Set `SCHEDULER_ENABLED=1` to poll the inbox every N minutes, prepare today's and tomorrow's meetings and email the daily brief (all set in Settings). Don't use `--reload` with the scheduler on, or jobs run twice.

## Test
`uv run pytest` runs the guardrail tests (no network or database needed).

## Files
`store.py` (Postgres, KPIs, audit), `google_api.py` (all Google calls), `prompt.py` (role prompt, untrusted-text fencing), `tools.py` (tools + guardrails), `agent.py` (Gemini loop, meeting prep, brief), `main.py` (routes, approvals, OAuth, scheduler).

## Guardrails
- **Access:** every route except `/health` and the Google OAuth callback needs the `X-API-Key` header. Starting a Google connection also needs it (`/oauth/google/start` returns JSON).
- **No tool sends, books or pays.** Replies and invites happen only in `POST /approvals/{id}` after the principal approves. Approval is claimed atomically (`pending` to `approving`), so a double click or retry can never send twice; a failed send goes back to pending. Proposals are unique per request and type.
- **The principal can edit** the reply or the invite list on the card; the edited version is what is sent, and the audit log keeps both. A rejection reason makes the agent re-draft.
- **Leak guards:** the model sees busy blocks only (no titles or attendees); it can only invite people on the email thread, the principal, or allowed domains; drafts containing sensitive/payment/travel content, other people's addresses or calendar titles are blocked; email text is fenced as untrusted data; escalations alert the principal at once (sender and subject only).
- Payment, travel and sensitive items only record sign-off. Mail is read-only; Drive is read-only; the daily brief and prep notes go only to the principal.
- Meeting proposals pin an absolute date, so approving a day later books the proposed date (or refuses if it has passed).
